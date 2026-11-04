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
from django.shortcuts import redirect,render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET,require_http_methods
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
            data['phone']=normalize_phone(entry.get('phone'))
            problems=[]
            if not data['name']:problems.append('shop name is required')
            if not data['phone']:problems.append('enter a valid 10-digit mobile number')
            if data['pincode'] and not re.fullmatch(r'[1-9][0-9]{5}',data['pincode']):problems.append('pincode must have 6 digits')
            for key,limit in LIMITS.items():
                if len(data[key])>limit:problems.append(f'{key} must have at most {limit} characters')
            if problems:
                if len(errors)<20:errors.append(f'Row {number}: '+', '.join(problems)+'.')
                continue
            data['normalized_name']=data['name'].casefold()
            identity=(data['phone'],data['normalized_name'])
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
    file=forms.FileField(label='Shop list',widget=forms.ClearableFileInput(attrs={'accept':'.xlsx,.csv'}),help_text='Excel .xlsx or CSV, up to 5 MB and 5,000 shops.')

    def clean_file(self):
        upload=self.cleaned_data['file']
        self.entries=read_sheet(upload)
        return upload


@private
@require_http_methods(['GET','POST'])
def directory(request):
    form=ShopUploadForm(request.POST if request.method=='POST' else None,request.FILES if request.method=='POST' else None)
    if request.method=='POST' and form.is_valid():
        created=updated=skipped=0
        with transaction.atomic():
            for data in form.entries:
                identity={key:data[key] for key in ('phone','normalized_name')}
                current=ShopDirectoryEntry.objects.select_for_update().filter(**identity).first()
                if current and current.registered_shop_id:
                    skipped+=1;continue
                if current:
                    # A two-column re-upload must not erase optional details.
                    for key,value in data.items():
                        if value:setattr(current,key,value)
                    current.uploaded_by=request.user;current.save();updated+=1
                else:
                    ShopDirectoryEntry.objects.create(**data,uploaded_by=request.user);created+=1
        messages.success(request,f'Shop list imported: {created} added, {updated} updated, {skipped} already registered and left unchanged.')
        return redirect('shop_directory')
    query=request.GET.get('q','').strip()[:150]
    entries=ShopDirectoryEntry.objects.select_related('registered_shop')
    if query:entries=entries.filter(Q(name__icontains=query)|Q(phone__icontains=query))
    return render(request,'pilot_admin/shop_directory.html',{'tab':'directory','form':form,'q':query,'page':Paginator(entries,20).get_page(request.GET.get('page')),'entry_count':ShopDirectoryEntry.objects.count(),'registered_count':ShopDirectoryEntry.objects.filter(registered_shop__isnull=False).count()})


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
    if len(query)<2 or not phone:return JsonResponse({'results':[]})
    entries=ShopDirectoryEntry.objects.filter(phone=phone,registered_shop__isnull=True)
    if normalize_phone(query)!=phone:entries=entries.filter(name__icontains=query)
    results=[{key:getattr(entry,key) for key in ('id','name','phone','pincode','city','address','category')} for entry in entries[:10]]
    return JsonResponse({'results':results})
