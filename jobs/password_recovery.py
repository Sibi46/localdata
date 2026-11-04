"""Session-bound pilot OTP recovery for personal and shop accounts."""
import time
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect,render
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods
from .models import User
from .simple_accounts import OTPForm,PasswordForm,valid_pending
from .otp_security import issue, verify, consume, demo_enabled, OTPError


class RecoveryPhoneForm(forms.Form):
    phone=forms.RegexField(r'^[6-9][0-9]{9}$',label='Registered mobile number',error_messages={'invalid':'Enter a valid 10-digit mobile number.'},widget=forms.TextInput(attrs={'type':'tel','inputmode':'numeric','maxlength':'10','autocomplete':'tel-national','placeholder':'10-digit mobile number'}))


def recoverable(user):
    return user and user.is_active and not user.is_staff and not user.is_superuser and not user.admin_role


def issue_code(request,user,phone):
    try:
        challenge = issue(request, phone, 'reset')
    except OTPError:
        return False
    request.session['password_recovery']={**challenge,'user_id':user.pk,'attempts':0}
    return True


@never_cache
@sensitive_post_parameters('password','confirm_password','otp')
@require_http_methods(['GET','POST'])
def recover(request):
    if getattr(settings, 'PUBLIC_DEMO_SIGNUP', False):
        request.session.pop('password_recovery', None)
        request.session.pop('account_otp_reset', None)
        return render(request, 'accounts/recovery_unavailable.html', status=503)
    pending=request.session.get('password_recovery')
    if pending and not demo_enabled('reset'):
        pending.pop('code', None)
        request.session['password_recovery'] = pending
    if pending and not valid_pending(pending):
        request.session.pop('password_recovery',None);pending=None
        messages.info(request,'Your OTP expired. Enter your mobile number to get a new one.')
    user=User.objects.filter(pk=pending['user_id']).first() if pending else None
    if pending and not recoverable(user):
        request.session.pop('password_recovery',None);pending=None;user=None
    if request.method=='POST' and request.POST.get('action')=='restart':
        request.session.pop('password_recovery',None)
        return redirect('forgot_password')
    step='password' if pending and pending.get('verified') else 'otp' if pending else 'phone'
    form_class={'phone':RecoveryPhoneForm,'otp':OTPForm,'password':PasswordForm}[step]
    form=form_class(request.POST if request.method=='POST' else None,**({'user':user} if step=='password' else {'initial':{'phone':request.GET.get('phone','')}} if step=='phone' else {}))
    if request.method=='POST' and request.POST.get('action')=='resend' and pending and step=='otp':
        if issue_code(request,user,pending['phone']):messages.success(request,'A new OTP is ready. Use the latest code shown below.')
        else:messages.error(request,'Too many OTP requests. Please try again in 10 minutes.')
        return redirect('forgot_password')
    if request.method=='POST' and form.is_valid():
        if step=='phone':
            phone=form.cleaned_data['phone']
            matches=list(User.objects.filter(Q(phone=phone)|Q(username=phone))[:2])
            candidate=matches[0] if len(matches)==1 else None
            if not recoverable(candidate):
                form.add_error('phone','Enter a registered personal or shop mobile number. Admin accounts require administrator help.')
            elif not issue_code(request,candidate,phone):
                form.add_error(None,'Password recovery is unavailable or too many OTP requests. Please try again later.')
            else:return redirect('forgot_password')
        elif step=='otp':
            try:
                verify(request, pending['phone'], 'reset', form.cleaned_data['otp'])
            except OTPError:
                pass
            else:
                pending['verified']=True;pending.pop('code',None)
                request.session['password_recovery']=pending
                return redirect('forgot_password')
            pending['attempts']+=1
            if pending['attempts']>=5:
                request.session.pop('password_recovery',None)
                messages.error(request,'Too many incorrect attempts. Start again to get a new OTP.')
                return redirect('forgot_password')
            request.session['password_recovery']=pending
            form.add_error('otp','That OTP is incorrect. Enter the code shown above.')
        else:
            with transaction.atomic():
                current=User.objects.select_for_update().filter(pk=pending['user_id']).first()
                if not recoverable(current):
                    request.session.pop('password_recovery',None)
                    messages.error(request,'This account cannot be reset here. Please contact support.')
                    return redirect('forgot_password')
                if (current.phone or current.username) != pending['phone']:
                    request.session.pop('password_recovery', None)
                    return redirect('forgot_password')
                try:
                    consume(request, pending['phone'], 'reset')
                except OTPError as error:
                    request.session.pop('password_recovery', None)
                    messages.error(request, str(error))
                    return redirect('forgot_password')
                current.set_password(form.cleaned_data['password'])
                current.save(update_fields=['password'])
            logout(request)
            messages.success(request,'Password updated. Sign in with your mobile number and new password.')
            return redirect('login')
    return render(request,'accounts/password_recovery.html',{'form':form,'step':step,'pending':pending})
