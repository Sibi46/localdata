"""Import shop spreadsheets and look up entries using the current account phone."""
import csv
import io
import re
from pathlib import Path
from zipfile import ZipFile,BadZipFile
from xml.etree.ElementTree import ParseError

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse,JsonResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET,require_POST,require_http_methods
from openpyxl import Workbook,load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from .models import ShopDirectoryEntry
from .pilot_admin import private


def normalize_phone(value):
    if isinstance(value,float):
        if not value.is_integer():return ''
        value=int(value)
    phone=re.sub(r'[\s()+-]','',str(value or ''))
    if phone.startswith('0091') and len(phone)==14:phone=phone[4:]
    elif phone.startswith('91') and len(phone)==12:phone=phone[2:]
    return phone if re.fullmatch(r'[6-9][0-9]{9}',phone) else ''


MAX_PHONES = 10


def parse_phone_cell(value):
    """Keep source text for review; never trim digits or invent missing numbers."""
    source = str(value if value is not None else '').strip()
    if len(source) > 1000:
        raise forms.ValidationError('A phone cell must have at most 1,000 characters.')
    if not source:
        return [], source, 'Phone number missing. Add a valid mobile before owner registration.'
    if source.startswith('-'):
        return [], source, 'A negative value is not a mobile number. Correct the original value.'
    direct = normalize_phone(value)
    if direct:
        return [direct], source, ''
    parts = [part.strip() for part in re.split(r'[,;/\n|]+', source) if part.strip()]
    # The supplied sheet also has "98765 01122 98765 01133" and
    # "9876501122 9876501133". Require a visible boundary between two numbers.
    if len(parts) == 1:
        pair = re.fullmatch(r'([6-9][0-9]{4}\s*[0-9]{5})\s+([6-9][0-9]{4}\s*[0-9]{5})', source)
        if pair:
            parts = list(pair.groups())
    phones = []
    invalid = 0
    for part in parts:
        phone = '' if part.startswith('-') else normalize_phone(part)
        if phone:
            if phone not in phones:
                phones.append(phone)
        else:
            invalid += 1
    if len(phones) > MAX_PHONES:
        raise forms.ValidationError('Use up to 10 mobile numbers per shop.')
    note = ('Some phone values need correction; only valid numbers can match an account.' if phones else
            'No valid mobile found. Correct the original number before owner registration.') if invalid else ''
    return phones, source, note


def phone_query(phones):
    query = Q(phone__in=phones)
    for index in range(MAX_PHONES - 1):
        query |= Q(**{f'alternate_phones__{index}__in': phones})
    return query


def entry_accepts_phone(entry, value):
    phone = normalize_phone(value)
    return bool(phone and phone in [entry.phone, *entry.alternate_phones])


HEADERS={
    'shopname':'name','businessname':'name','storename':'name','name':'name',
    'phone':'phone','phno':'phone','phonenumber':'phone','mobilenumber':'phone','mobile':'phone','contactnumber':'phone',
    'pincode':'pincode','pin':'pincode','postalcode':'pincode',
    'city':'city','town':'city','citytown':'city','address':'address','shopaddress':'address',
    'category':'category','shoptype':'category',
}
LIMITS={'name':150,'city':100,'address':500,'category':100}


def read_sheet(upload):
    extension=Path(upload.name).suffix.lower()
    if upload.size>5*1024*1024:raise forms.ValidationError('Upload a file smaller than 5 MB.')
    book=None
    try:
        if extension=='.xlsx':
            with ZipFile(upload) as archive:
                if len(archive.infolist())>1000 or sum(item.file_size for item in archive.infolist())>50*1024*1024:
                    raise forms.ValidationError('This workbook is too large. Use the template with up to 5,000 shops.')
            upload.seek(0)
            book=load_workbook(upload,read_only=True,data_only=True,keep_links=False)
            sheet=book.active
            sheet.reset_dimensions()
            rows=sheet.iter_rows(values_only=True,max_row=5002,max_col=20)
        elif extension=='.csv':
            rows=csv.reader(io.StringIO(upload.read().decode('utf-8-sig')))
        else:
            raise forms.ValidationError('Choose an Excel .xlsx file or a UTF-8 .csv file. Save older .xls files as .xlsx first.')
        header=next(rows,None)
        if not header:raise forms.ValidationError('The sheet is empty. Add column headings and shop details.')
        columns={}
        for index,value in enumerate(header):
            key=HEADERS.get(re.sub(r'[^a-z0-9]','',str(value or '').lower()))
            if key:
                if key in columns.values():raise forms.ValidationError(f'The {key} column is repeated.')
                columns[index]=key
        if not {'name','phone'}<=set(columns.values()):
            raise forms.ValidationError('The first row must contain Shop Name and Phone columns. Download the example template below.')
        parsed=[];errors=[];seen=set()
        for number,row in enumerate(rows,start=2):
            if number>5001 and any(value not in (None,'') for value in row):
                raise forms.ValidationError('Upload up to 5,000 shops at a time.')
            if not any(value not in (None,'') for value in row):continue
            entry={key:(row[index] if index<len(row) else None) for index,key in columns.items()}
            data={key:str(entry.get(key) or '').strip() for key in ('name','pincode','city','address','category')}
            data['name']=' '.join(data['name'].split())
            phones, source, note = parse_phone_cell(entry.get('phone'))
            data.update(phone=phones[0] if phones else '', alternate_phones=phones[1:], source_phone=source, phone_note=note)
            problems=[]
            if not data['name']:problems.append('shop name is required')
            if data['pincode'] and not re.fullmatch(r'[1-9][0-9]{5}',data['pincode']):problems.append('pincode must have 6 digits')
            for key,limit in LIMITS.items():
                if len(data[key])>limit:problems.append(f'{key} must have at most {limit} characters')
            if problems:
                if len(errors)<20:errors.append(f'Row {number}: '+', '.join(problems)+'.')
                continue
            data['normalized_name']=data['name'].casefold()
            identity=(tuple(sorted(phones)),data['normalized_name'],source if not phones else '')
            if identity not in seen:parsed.append(data);seen.add(identity)
        if errors:raise forms.ValidationError(errors)
        if not parsed:raise forms.ValidationError('Add at least one shop below the column headings.')
        return parsed
    except forms.ValidationError:raise
    except (BadZipFile,UnicodeError,csv.Error,ValueError,KeyError,TypeError,IndexError,OSError,EOFError,ParseError,InvalidFileException):
        raise forms.ValidationError('The file could not be read. Download the template and save your shops as .xlsx or UTF-8 CSV.')
    finally:
        if book is not None:book.close()


class ShopUploadForm(forms.Form):
    file=forms.FileField(label='Shop list',widget=forms.ClearableFileInput(attrs={'accept':'.xlsx,.csv'}),help_text='Excel .xlsx or CSV, up to 5 MB and 5,000 rows. Multiple numbers and missing phones are accepted for admin review.')

    def clean_file(self):
        upload=self.cleaned_data['file']
        self.entries=read_sheet(upload)
        return upload


@private
@require_http_methods(['GET','POST'])
def directory(request):
    form=ShopUploadForm(request.POST if request.method=='POST' else None,request.FILES if request.method=='POST' else None)
    if request.method=='POST' and form.is_valid():
        created=updated=skipped=needs_review=0
        with transaction.atomic():
            for data in form.entries:
                phones = [data['phone'], *data['alternate_phones']] if data['phone'] else []
                candidates = ShopDirectoryEntry.objects.select_for_update().filter(normalized_name=data['normalized_name'])
                source_match = Q(source_phone=data['source_phone']) & (Q(phone='') | Q(contacts_reviewed=True))
                matches = candidates.filter(phone_query(phones) | source_match) if phones else candidates.filter(Q(phone='') | source_match)
                # Never alter any already-claimed matching listing.
                current = matches.order_by('-registered_shop_id', 'pk').first()
                if current and current.registered_shop_id:
                    skipped+=1;continue
                if current:
                    # A repeated upload cannot undo an explicit admin correction.
                    if current.contacts_reviewed:
                        phones = []
                        data['source_phone'] = current.source_phone
                        data['phone_note'] = current.phone_note
                    combined = list(dict.fromkeys([current.phone, *current.alternate_phones, *phones]))
                    combined = [phone for phone in combined if normalize_phone(phone)]
                    if len(combined) > MAX_PHONES:
                        skipped += 1
                        continue
                    data['phone'] = combined[0] if combined else ''
                    data['alternate_phones'] = combined[1:]
                    # A two-column re-upload must not erase optional details.
                    for key,value in data.items():
                        if value or key in ('alternate_phones','source_phone','phone_note'):setattr(current,key,value)
                    current.uploaded_by=request.user;current.save();updated+=1
                else:
                    ShopDirectoryEntry.objects.create(**data,uploaded_by=request.user);created+=1
                if data['phone_note'] or not data['phone']:
                    needs_review += 1
        messages.success(request,f'Shop list imported: {created} added, {updated} updated, {skipped} protected or unchanged. {needs_review} rows need phone review. No user accounts were created.')
        return redirect('shop_directory')
    query=request.GET.get('q','').strip()[:150]
    entries=ShopDirectoryEntry.objects.select_related('registered_shop')
    needs_review = Q(phone='') | ~Q(phone_note='')
    review_only = request.GET.get('review') == '1'
    if review_only:entries=entries.filter(needs_review, registered_shop__isnull=True)
    if query:
        criteria = Q(name__icontains=query) | Q(phone__icontains=query) | Q(source_phone__icontains=query)
        normalized = normalize_phone(query)
        if normalized:criteria |= phone_query([normalized])
        entries = entries.filter(criteria)
    return render(request,'pilot_admin/shop_directory.html',{'tab':'directory','form':form,'q':query,'review_only':review_only,'review_count':ShopDirectoryEntry.objects.filter(needs_review,registered_shop__isnull=True).count(),'page':Paginator(entries,20).get_page(request.GET.get('page')),'entry_count':ShopDirectoryEntry.objects.count(),'registered_count':ShopDirectoryEntry.objects.filter(registered_shop__isnull=False).count()})


@private
@require_POST
def update_phones(request, pk):
    entry = get_object_or_404(ShopDirectoryEntry, pk=pk)
    try:
        phones, source, note = parse_phone_cell(request.POST.get('phones', ''))
        if note or not phones:
            raise forms.ValidationError('Enter valid mobile numbers only, separated by commas. Existing details were not changed.')
    except forms.ValidationError as error:
        messages.error(request, ' '.join(error.messages))
        return redirect('shop_directory')
    with transaction.atomic():
        entry = ShopDirectoryEntry.objects.select_for_update().get(pk=pk)
        if entry.registered_shop_id:
            messages.error(request, 'Registered shop contacts cannot be changed by the importer.')
            return redirect('shop_directory')
        if ShopDirectoryEntry.objects.filter(normalized_name=entry.normalized_name).exclude(pk=entry.pk).filter(phone_query(phones)).exists():
            messages.error(request, 'This shop already has a listing with one of these numbers. Nothing changed.')
            return redirect('shop_directory')
        entry.phone = phones[0]
        entry.alternate_phones = phones[1:]
        # Keep source_phone as the original imported evidence.
        entry.phone_note = ''
        entry.contacts_reviewed = True
        entry.uploaded_by = request.user
        entry.save(update_fields=['phone', 'alternate_phones', 'phone_note', 'contacts_reviewed', 'uploaded_by', 'updated_at'])
    messages.success(request, 'Shop contacts corrected. Matching account holders can now select this listing.')
    return redirect('shop_directory')


@private
@require_GET
def template(request):
    book=Workbook();sheet=book.active;sheet.title='Shops'
    sheet.append(['Shop Name','Phone','Pincode','City','Address','Category'])
    sheet.append(['Example Shop','9876543210','604408','Vandavasi','','Groceries'])
    for column in sheet.columns:sheet.column_dimensions[column[0].column_letter].width=24
    stream=io.BytesIO();book.save(stream);book.close()
    response=HttpResponse(stream.getvalue(),content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition']='attachment; filename="shop-list-template.xlsx"'
    return response


@never_cache
@login_required
@require_GET
def search(request):
    query=request.GET.get('q','').strip()[:150]
    phone=normalize_phone(request.user.phone)
    if len(query)<2:return JsonResponse({'results':[]})
    entries=ShopDirectoryEntry.objects.filter(registered_shop__isnull=True)
    query_phone=normalize_phone(query)
    if query_phone:
        # Phone lookup must never reveal another account's imported contacts.
        if not phone or query_phone!=phone:return JsonResponse({'results':[]})
        entries=entries.filter(phone_query([phone]))
    else:
        entries=entries.filter(name__icontains=query)
    # Show matching names to help owners discover their listing, but expose
    # contact/detail data and selection only for the account's own phone.
    entries=entries.annotate(account_match=phone_query([phone]) if phone else Q(pk__isnull=True)).order_by('-account_match','name','pk')
    results=[]
    for entry in entries[:10]:
        can_select=entry_accepts_phone(entry,phone)
        result={'name':entry.name,'can_select':can_select}
        if can_select:
            result.update({key:getattr(entry,key) for key in ('id','pincode','city','address','category')})
            result['phone']=phone
        results.append(result)
    return JsonResponse({'results':results})
