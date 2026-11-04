"""Ad creative applications and private owner status tracking."""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from .models import AdPost, User, UserNotification
from .shop_forms import check_image


class AdApplicationForm(forms.ModelForm):
    contact_phone = forms.RegexField(r'^[6-9][0-9]{9}$', label='Contact phone', widget=forms.TextInput(attrs={'type': 'tel', 'inputmode': 'numeric', 'maxlength': '10'}))
    contact_name = forms.CharField(max_length=100, label='Contact person')
    title = forms.CharField(max_length=160, label='Ad headline', widget=forms.TextInput(attrs={'placeholder': 'What would you like Vandavasi to discover?'}))
    pincode = forms.RegexField(r'^[1-9][0-9]{5}$', label='Business pincode', widget=forms.TextInput(attrs={'inputmode':'numeric','maxlength':'6'}))

    class Meta:
        model = AdPost
        fields = ['ad_type', 'company_name', 'title', 'description', 'image', 'contact_name', 'contact_phone', 'pincode', 'website', 'requested_days']
        labels = {'ad_type': 'Promotion type', 'company_name':'Shop / business name', 'description':'Ad description', 'image':'Ad image', 'website':'Website (optional)', 'requested_days':'Requested duration'}
        widgets = {'ad_type': forms.RadioSelect(), 'description': forms.Textarea(attrs={'rows':4,'maxlength':'2000'}), 'image':forms.ClearableFileInput(attrs={'accept':'image/jpeg,image/png,image/webp','data-image-preview':'ad-image-preview','data-image-crop':'product'})}
        help_texts = {'image':'JPG, PNG, or WebP, up to 5 MB. You can crop or adjust it before submitting.', 'requested_days':'The approved run starts when the Superadmin approves your ad.'}

    def clean_image(self):
        return check_image(self.cleaned_data.get('image'))

    def clean_description(self):
        value = self.cleaned_data['description']
        if len(value) > 2000:
            raise forms.ValidationError('Keep the description within 2,000 characters.')
        return value


@require_http_methods(['GET','POST'])
def apply(request, pk=None):
    if not request.user.is_authenticated:
        if request.method == 'POST':
            return redirect('/login/?next=/advertise/register/')
        return render(request,'ads/apply.html',{'guest':True})
    ad = get_object_or_404(AdPost,pk=pk,user=request.user,status='rejected') if pk else AdPost(user=request.user)
    company = getattr(request.user,'company',None)
    form = AdApplicationForm(request.POST if request.method=='POST' else None, request.FILES if request.method=='POST' else None, instance=ad,
        initial={} if pk else {'ad_type':'shop','company_name':company.company_name if company else '', 'contact_name':request.user.get_full_name() or request.user.username,'contact_phone':request.user.business_phone or request.user.phone,'pincode':request.user.pincode,'requested_days':7})
    if request.method=='POST' and form.is_valid():
        ad=form.save(commit=False)
        ad.user=request.user
        ad.status='pending'
        ad.reject_note=''
        ad.approved_at=None
        ad.expires_at=None
        ad.save()
        UserNotification.objects.bulk_create([
            UserNotification(user=admin,title='Ad application ready for review',message=f'{ad.company_name}: {ad.title}'[:200],link=f'/super-admin/ads/{ad.pk}/')
            for admin in User.objects.filter(admin_role='super_admin',is_active=True)
        ])
        messages.success(request,'Ad application submitted. The Superadmin will review it before it appears publicly.')
        return redirect('ad_applications')
    return render(request,'ads/apply.html',{'form':form,'editing':bool(pk),'ad':ad})


@login_required
def applications(request):
    page=Paginator(AdPost.objects.filter(user=request.user).order_by('-created_at','-pk'),12).get_page(request.GET.get('page'))
    return render(request,'ads/mine.html',{'page':page})
