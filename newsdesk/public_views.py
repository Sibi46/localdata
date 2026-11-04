import json
import re
import secrets
import time
import uuid
from datetime import datetime, timezone as datetime_timezone
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.crypto import salted_hmac
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .models import NewsContributor, NewsSubmission
from .permissions import is_admin, agent_for, published_items
from .public_forms import ReviewSubmissionForm, ShareNewsForm
from .public_services import editor_submissions, review_submission, submit_news


def verified_phone(request):
    proof = request.session.get('news_phone_proof', {})
    if not isinstance(proof, dict):
        return None
    try:
        if 0 <= time.time() - float(proof['at']) <= 1800 and re.fullmatch(r'[6-9][0-9]{9}', proof['phone']):
            return proof['phone']
    except (KeyError, ValueError, TypeError):
        pass
    return None


def limited(key, maximum, seconds):
    key = 'news-share:' + salted_hmac('news-share-rate', key).hexdigest()
    try:
        cache.add(key, 0, timeout=seconds)
        return cache.incr(key) > maximum
    except Exception:
        return True


def read_payload(request):
    if len(request.body) > 2048:
        raise ValueError
    data = json.loads(request.body)
    if not isinstance(data, dict):
        raise ValueError
    return data


def make_otp():
    return str(secrets.randbelow(900000) + 100000)


def deliver_otp(phone, otp):
    from jobs.otp_security import deliver_code
    return deliver_code(phone, otp)


@never_cache
@require_POST
def send_otp(request):
    try:
        phone = read_payload(request).get('phone')
        if not isinstance(phone, str) or not re.fullmatch(r'[6-9][0-9]{9}', phone):
            raise ValueError
    except (ValueError, TypeError, UnicodeError):
        return JsonResponse({'error': 'Enter a valid 10-digit mobile number.'}, status=400)
    request.session.pop('news_phone_proof', None)
    request.session.pop('news_otp', None)
    request.session.pop('news_form_tokens', None)
    ip = request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR', '')
    if limited('send-phone:' + phone, 3, 600) or limited('send-ip:' + ip, 30, 600):
        return JsonResponse({'error': 'Too many OTP requests. Please try again after 10 minutes.'}, status=429)
    otp = make_otp()
    if not deliver_otp(phone, otp):
        return JsonResponse({'error': 'SMS could not be sent. Please try again later.'}, status=503)
    request.session['news_otp'] = {'phone': phone, 'hash': make_password(otp), 'at': time.time()}
    return JsonResponse({'success': True, 'message': 'OTP sent. It is valid for 10 minutes.'})


@never_cache
@require_POST
def verify_otp(request):
    try:
        otp = read_payload(request).get('otp')
        if not isinstance(otp, str) or not re.fullmatch(r'[0-9]{6}', otp):
            raise ValueError
    except (ValueError, TypeError, UnicodeError):
        return JsonResponse({'error': 'Enter the six-digit OTP.'}, status=400)
    challenge = request.session.get('news_otp', {})
    if not challenge or time.time() - challenge.get('at', 0) > 600:
        request.session.pop('news_otp', None)
        return JsonResponse({'error': 'OTP expired. Request a new code.'}, status=400)
    if limited('verify-phone:' + challenge['phone'], 5, 600):
        request.session.pop('news_otp', None)
        return JsonResponse({'error': 'Too many attempts. Request a new OTP later.'}, status=429)
    if not check_password(otp, challenge['hash']):
        return JsonResponse({'error': 'Incorrect OTP. Please try again.'}, status=400)
    request.session['news_phone_proof'] = {'phone': challenge['phone'], 'at': time.time()}
    request.session.pop('news_otp', None)
    request.session.cycle_key()
    return JsonResponse({'success': True, 'redirect': '/news/share/'})


@never_cache
@require_http_methods(['GET', 'POST'])
def share(request):
    if request.user.is_authenticated:
        from .account_submissions import share as account_share
        return account_share(request)
    phone = verified_phone(request)
    if not phone:
        if request.method == 'POST':
            messages.error(request, 'Verify your mobile number before sending news.')
        return render(request, 'newsdesk/share_verify.html', {'can_manage': is_admin(request.user) or bool(agent_for(request.user))})
    contributor = NewsContributor.objects.filter(phone=phone).select_related('pincode').first()
    tokens = request.session.get('news_form_tokens', [])
    if request.method == 'GET':
        token = str(uuid.uuid4())
        tokens = (tokens + [token])[-5:]
        request.session['news_form_tokens'] = tokens
    else:
        token = request.POST.get('token', '')
    form = ShareNewsForm(request.POST if request.method == 'POST' else None, request.FILES or None,
        contributor=contributor, initial={'token': token})
    if request.method == 'POST' and form.is_valid():
        if str(form.cleaned_data['token']) not in tokens:
            form.add_error(None, 'This form has expired. Reload the page and try again.')
        elif limited('submissions:' + phone, 10, 3600):
            form.add_error(None, 'You have reached the hourly submission limit. Please try again later.')
        else:
            proof_at = datetime.fromtimestamp(request.session['news_phone_proof']['at'], tz=datetime_timezone.utc)
            try:
                submission = submit_news(phone, proof_at, form.cleaned_data, request.user)
            except ValidationError as error:
                form.add_error(None, error)
            except OSError:
                form.add_error(None, 'Private documents could not be saved. Please try again later.')
            except IntegrityError:
                submission = NewsSubmission.objects.filter(submission_token=form.cleaned_data['token'], contributor__phone=phone).first()
                if submission:
                    return redirect('newsdesk:submission_status', pk=submission.pk)
                form.add_error(None, 'Your details changed in another tab. Reload this page and try again.')
            else:
                return redirect('newsdesk:submission_status', pk=submission.pk)
    submissions = contributor.submissions.select_related('published_story')[:20] if contributor else []
    return render(request, 'newsdesk/share_form.html', {'form': form, 'phone': phone, 'contributor': contributor,
        'submissions': submissions}, status=400 if request.method == 'POST' else 200)


@never_cache
@require_GET
def submission_status(request, pk):
    phone = verified_phone(request)
    if not phone:
        return redirect('newsdesk:share')
    submission = get_object_or_404(NewsSubmission.objects.select_related('contributor', 'published_story'), pk=pk, contributor__phone=phone)
    public_story = published_items().filter(pk=submission.published_story_id).first() if submission.published_story_id else None
    return render(request, 'newsdesk/submission_status.html', {'submission': submission, 'public_story': public_story})


@never_cache
@require_POST
def finish(request):
    for key in ('news_phone_proof', 'news_otp', 'news_form_tokens'):
        request.session.pop(key, None)
    return redirect('newsdesk:share')


@never_cache
@login_required
@require_GET
def submission_queue(request):
    scope = editor_submissions(request.user).select_related('contributor__pincode')
    status = request.GET.get('status', 'pending')
    if status not in NewsSubmission.Status.values:
        status = 'pending'
    page = Paginator(scope.filter(status=status), 20).get_page(request.GET.get('page'))
    return render(request, 'newsdesk/submission_queue.html', {'page': page, 'selected_status': status,
        'statuses': NewsSubmission.Status.choices, 'can_manage': True})


@never_cache
@login_required
@require_http_methods(['GET', 'POST'])
def review(request, pk):
    submission = get_object_or_404(editor_submissions(request.user).select_related('contributor__pincode', 'published_story'), pk=pk)
    form = ReviewSubmissionForm(request.POST if request.method == 'POST' else None,
        initial={'topic': submission.topic, 'body': submission.body, 'category': 'news'})
    if request.method == 'POST' and form.is_valid():
        try:
            submission = review_submission(request.user, pk, form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, 'News published.' if submission.status == 'published' else 'Submission reviewed.')
            return redirect('newsdesk:review_submission', pk=submission.pk)
    return render(request, 'newsdesk/review_submission.html', {'submission': submission, 'form': form, 'can_manage': True},
        status=400 if request.method == 'POST' and form.errors else 200)


@never_cache
@require_GET
def identity_file(request, pk, kind):
    if kind not in {'aadhaar', 'profile_photo'}:
        raise Http404
    contributor = get_object_or_404(NewsContributor, pk=pk)
    if verified_phone(request) != contributor.phone:
        if not request.user.is_authenticated or not editor_submissions(request.user).filter(contributor=contributor).exists():
            raise PermissionDenied
    file = getattr(contributor, kind)
    if not file or not file.storage.exists(file.name):
        raise Http404
    extension = Path(file.name).suffix.lower()
    content_type = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp'}.get(extension, 'application/octet-stream')
    response = FileResponse(file.open('rb'), as_attachment=kind == 'aadhaar', filename=kind + extension,
        content_type='application/octet-stream' if kind == 'aadhaar' else content_type)
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "default-src 'none'"
    response['Cache-Control'] = 'private, no-store'
    return response
