"""Five free products per shop, with additional slots assigned by Superadmin."""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from .models import CompanyProfile, User
from .pilot_admin import private


def send_access_message(sender, receiver, content, title, link):
    from .admin_messages import send_review_message
    return send_review_message(sender,receiver,title,content,link,notif_type='info')


class ProductAccessRequestForm(forms.Form):
    requested_limit=forms.IntegerField(label='Total products you need',min_value=6,max_value=10000,help_text='This includes your 5 free products.')
    message=forms.CharField(label='Message to Superadmin',max_length=1000,widget=forms.Textarea(attrs={'rows':5}))

    def __init__(self,*args,company,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['requested_limit'].min_value=company.product_limit+1
        self.fields['requested_limit'].widget.attrs['min']=company.product_limit+1
        self.company=company

    def clean_requested_limit(self):
        value=self.cleaned_data['requested_limit']
        if value<=self.company.product_limit:
            raise forms.ValidationError('Request a total above your current product limit.')
        return value


def request_context(company,form=None):
    count=company.products.count()
    if form is None:
        form=ProductAccessRequestForm(company=company,initial={
            'requested_limit':company.product_limit+5,
            'message':f'Hello Superadmin, I would like to add more products to {company.company_name}. My shop currently has {count} of {company.product_limit} product slots in use. Please enable additional product slots for my shop. Thank you.',
        })
    return {'company':company,'product_count':count,'form':form,'at_limit':count>=company.product_limit}


def limit_page(request,company,status=200):
    return render(request,'shop/product_access.html',request_context(company),status=status)


@login_required
@require_http_methods(['GET','POST'])
def request_access(request):
    company=get_object_or_404(CompanyProfile,user=request.user,user__is_active=True)
    if request.method=='POST':
        form=ProductAccessRequestForm(request.POST,company=company)
        if form.is_valid():
            with transaction.atomic():
                company=CompanyProfile.objects.select_for_update().get(pk=company.pk)
                if company.product_access_status=='pending':
                    messages.info(request,'Your request is already waiting for Superadmin review.')
                    return redirect('product_access_request')
                if form.cleaned_data['requested_limit']<=company.product_limit:
                    messages.info(request,'Your product limit has changed. Please check your current allowance.')
                    return redirect('product_access_request')
                admins=list(User.objects.filter(admin_role='super_admin',is_active=True).exclude(pk=request.user.pk).order_by('pk'))
                if not admins:
                    form.add_error(None,'No Superadmin is available right now. Please try again later.')
                else:
                    company.requested_product_limit=form.cleaned_data['requested_limit']
                    company.product_access_status='pending'
                    company.product_access_requested_at=timezone.now()
                    company.product_access_note=''
                    company.save(update_fields=['requested_product_limit','product_access_status','product_access_requested_at','product_access_note'])
                    body=(f'Product access request for {company.company_name} ({company.company_id}). '
                          f'Current allowance: {company.product_limit} products. Requested total: {company.requested_product_limit} products.\n\n'
                          f'{form.cleaned_data["message"]}\n\nReview: /super-admin/shops/{company.pk}/#product-access')
                    conversation=None
                    for admin in admins:
                        sent=send_access_message(request.user,admin,body,'Shop requests more product slots',f'/super-admin/shops/{company.pk}/#product-access')
                        if conversation is None:conversation=sent
                    messages.success(request,'Your request was sent to Superadmin in Messages. Your current product limit stays in place until approval.')
                    return redirect('chat_room',conv_id=conversation.pk)
        return render(request,'shop/product_access.html',request_context(company,form))
    return limit_page(request,company)


class ProductAccessReviewForm(forms.Form):
    decision=forms.ChoiceField(choices=[('approve','Assign more product slots'),('decline','Request changes')])
    product_limit=forms.IntegerField(label='New total product limit',min_value=6,max_value=10000,required=False,help_text='For example, 20 means this shop can have 20 products in total.')
    note=forms.CharField(label='Message to shop owner (optional)',required=False,max_length=1000,widget=forms.Textarea(attrs={'rows':3}))

    def clean(self):
        data=super().clean()
        if data.get('decision')=='approve' and not data.get('product_limit'):
            self.add_error('product_limit','Enter the total number of products this shop can add.')
        if data.get('decision')=='decline' and not data.get('note'):
            self.add_error('note','Tell the shop owner what needs to change.')
        return data


@private
@require_POST
def assign_access(request,pk):
    company=get_object_or_404(CompanyProfile,pk=pk)
    form=ProductAccessReviewForm(request.POST)
    if form.is_valid():
        with transaction.atomic():
            company=CompanyProfile.objects.select_for_update().select_related('user').get(pk=pk)
            approve=form.cleaned_data['decision']=='approve'
            if approve and form.cleaned_data['product_limit']<=company.product_limit:
                form.add_error('product_limit',f'Choose a total greater than the current limit of {company.product_limit}.')
            elif not approve and company.product_access_status!='pending':
                form.add_error(None,'There is no pending request to return.')
            else:
                if approve:company.product_limit=form.cleaned_data['product_limit']
                company.product_access_status='approved' if approve else 'declined'
                company.product_access_note=form.cleaned_data['note']
                company.save(update_fields=['product_limit','product_access_status','product_access_note'])
                title='More product slots approved' if approve else 'Your product request needs changes'
                body=(f'Your shop {company.company_name} can now add up to {company.product_limit} products.' if approve else f'Your product access request for {company.company_name} needs changes.')
                if company.product_access_note:body+='\n\n'+company.product_access_note
                if request.user.pk!=company.user_id:
                    send_access_message(request.user,company.user,body,title,'/shop/products/access/')
                messages.success(request,f'{company.company_name} now has {company.product_limit} product slots.' if approve else 'Feedback sent to the shop owner.')
                return redirect('pilot_admin_shop',pk=pk)
    from .pilot_admin import shop_detail_context
    return render(request,'pilot_admin/shop_detail.html',shop_detail_context(company,form),status=400)


@private
@require_GET
def requests(request):
    status=request.GET.get('status','pending')
    if status not in ('pending','approved','declined','all'):status='pending'
    records=CompanyProfile.objects.exclude(product_access_status='').select_related('user').order_by('-product_access_requested_at','-pk')
    if status!='all':records=records.filter(product_access_status=status)
    query=request.GET.get('q','').strip()[:150]
    if query:records=records.filter(Q(company_name__icontains=query)|Q(user__phone__icontains=query)|Q(company_id__icontains=query))
    return render(request,'pilot_admin/product_requests.html',{'tab':'product_requests','page':Paginator(records,20).get_page(request.GET.get('page')),'status':status,'q':query})
