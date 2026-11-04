import json
import re
from types import SimpleNamespace
import mimetypes
from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Avg, Count
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from . import services
from .forms import AgentForm, CommentForm, FeedForm, NewsItemForm, RatingForm, ReportForm
from .models import Comment, CommentReport, NewsAgent
from .permissions import active_pincodes, agent_for, is_admin, managed_items, published_items


def api(request):
    return request.path.startswith('/news/api/')


def endpoint(methods=('GET',), auth=False):
    def decorator(view):
        @require_http_methods(methods)
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if auth and (not request.user.is_authenticated or not request.user.is_active):
                if api(request):
                    return JsonResponse({'error': 'Sign in to continue.'}, status=401)
                return redirect_to_login(request.get_full_path())
            try:
                return view(request, *args, **kwargs)
            except (ValidationError, PermissionDenied, Http404) as error:
                status = 400 if isinstance(error, ValidationError) else 403 if isinstance(error, PermissionDenied) else 404
                errors = error.messages if isinstance(error, ValidationError) else [str(error) or 'Not found.']
                if api(request):
                    return JsonResponse({'errors': errors}, status=status)
                return render(request, 'newsdesk/error.html', {'errors': errors}, status=status)
        return wrapped
    return decorator


def payload(request):
    if request.content_type == 'application/json':
        try:
            values = json.loads(request.body)
        except (ValueError, UnicodeDecodeError):
            raise ValidationError('Send a valid JSON object.')
        if not isinstance(values, dict) or any(isinstance(value, (dict, list)) for value in values.values()):
            raise ValidationError('Send a JSON object with simple field values.')
        return values
    return request.POST


def display_name(user):
    # Usernames in this project can be phone numbers.
    return user.get_full_name().strip() or f'Resident {user.pk}'


def serialize_item(item):
    return {
        'id': item.pk, 'title': item.title, 'category': item.category, 'kind': item.kind,
        'pincode': item.pincode.code, 'status': item.status,
        'published_at': item.published_at.isoformat() if item.published_at else None,
        'comment_deadline': item.comment_deadline.isoformat() if item.comment_deadline else None,
        'comments_open': item.comments_open,
        'event_start': item.event_start.isoformat() if item.event_start else None,
        'event_end': item.event_end.isoformat() if item.event_end else None, 'venue': item.venue,
        'photo': reverse('newsdesk:media', args=[item.pk, 'photo']) if item.photo else None,
        'video': reverse('newsdesk:media', args=[item.pk, 'video']) if item.video else None,
        'url': reverse('newsdesk:detail', args=[item.pk]),
    }


def page_data(page, serializer):
    return {'results': [serializer(obj) for obj in page], 'page': page.number, 'pages': page.paginator.num_pages, 'total': page.paginator.count}


def desk_context(request):
    admin = is_admin(request.user)
    return {'desk_admin': admin, 'can_manage': admin or bool(agent_for(request.user))}


@endpoint()
def feed(request):
    values = request.GET.copy()
    if 'pincode' not in values:
        from jobs.account import selected_area
        values['pincode'] = selected_area(request) or request.session.get('news_pincode', '')
        # A resident profile may contain a pincode not yet configured in the hierarchy.
        if not re.fullmatch(r'[1-9][0-9]{5}', values['pincode'] or ''):
            values['pincode'] = ''
    form = FeedForm(values)
    selected = services.valid(form)
    code = selected['pincode']
    pin = SimpleNamespace(code=code) if code else None
    if pin:
        request.session['news_pincode'] = pin.code
    elif 'pincode' in request.GET:
        request.session.pop('news_pincode', None)
    items = published_items().select_related('pincode')
    if pin:
        items = items.filter(pincode__code=code)
    for field in ('category', 'kind'):
        if selected[field]:
            items = items.filter(**{field: selected[field]})
    page = Paginator(items, 12).get_page(request.GET.get('page'))
    if api(request):
        return JsonResponse(page_data(page, serialize_item))
    edition = list(page)
    return render(request, 'newsdesk/feed.html', {
        'form': form, 'page': page, 'selected_pin': pin,
        'top_stories': edition[:6], 'latest_stories': edition[6:],
        'community_stories': [story for story in edition if story.category in ('community', 'achievements')][:3],
        **desk_context(request),
    })


@endpoint()
def detail(request, pk):
    item = get_object_or_404(published_items().select_related('pincode', 'author'), pk=pk)
    comments = item.comments.filter(is_hidden=False).select_related('user')
    page = Paginator(comments, 30).get_page(request.GET.get('page'))
    ratings = item.ratings.aggregate(average=Avg('stars'), total=Count('pk'))
    my_rating = item.ratings.filter(user=request.user).first() if request.user.is_authenticated else None
    for comment in page:
        comment.resident_name = display_name(comment.user)
    if api(request):
        return JsonResponse({**serialize_item(item), 'body': item.body, 'author': display_name(item.author),
                             'ratings': ratings, 'my_rating': my_rating.stars if my_rating else None,
                             'comments': page_data(page, lambda c: {'id': c.pk, 'name': c.resident_name, 'text': c.text, 'created_at': c.created_at.isoformat()})})
    return render(request, 'newsdesk/detail.html', {
        'item': item, 'page': page, 'ratings': ratings, 'author_name': display_name(item.author),
        'comment_form': CommentForm(), 'rating_form': RatingForm(instance=my_rating), **desk_context(request),
    })


@endpoint(('POST',), auth=True)
def comment(request, pk):
    obj = services.add_comment(request.user, pk, payload(request))
    if api(request):
        return JsonResponse({'id': obj.pk, 'text': obj.text}, status=201)
    messages.success(request, 'Your comment was added.')
    return redirect(reverse('newsdesk:detail', args=[pk]) + '#conversation')


@endpoint(('POST',), auth=True)
def rate(request, pk):
    obj = services.rate_item(request.user, pk, payload(request))
    if api(request):
        return JsonResponse({'stars': obj.stars})
    messages.success(request, 'Your rating was saved.')
    return redirect('newsdesk:detail', pk=pk)


@endpoint(('GET', 'POST'), auth=True)
def report(request, pk):
    obj = get_object_or_404(Comment, pk=pk, is_hidden=False, item__in=published_items())
    form = ReportForm(payload(request) if request.method == 'POST' else None)
    if request.method == 'POST':
        result, created = services.report_comment(request.user, pk, payload(request))
        if api(request):
            return JsonResponse({'id': result.pk, 'created': created}, status=201 if created else 200)
        messages.success(request, 'Your report has been sent to the local news desk.')
        return redirect('newsdesk:detail', pk=obj.item_id)
    return render(request, 'newsdesk/form.html', {'form': form, 'heading': 'Report a comment', 'intro': 'Tell the local news desk what needs attention.', 'submit': 'Send report', **desk_context(request)})


@endpoint(auth=True)
def manage(request):
    scope = managed_items(request.user)
    tab = request.GET.get('tab', 'stories')
    if tab not in {'stories', 'comments', 'reports'}:
        raise ValidationError('Choose stories, comments or reports.')
    if tab == 'stories':
        query = scope.select_related('pincode').annotate(average=Avg('ratings__stars'), rating_count=Count('ratings')).order_by('-updated_at', '-pk')
    elif tab == 'comments':
        query = Comment.objects.filter(item__in=scope).select_related('item', 'user').order_by('-created_at', '-pk')
    else:
        query = CommentReport.objects.filter(comment__item__in=scope, resolved=False).select_related('comment__item').order_by('-created_at', '-pk')
    page = Paginator(query, 20).get_page(request.GET.get('page'))
    if api(request):
        if tab == 'stories':
            serializer = lambda obj: {**serialize_item(obj), 'average': obj.average, 'rating_count': obj.rating_count}
        elif tab == 'comments':
            serializer = lambda obj: {'id': obj.pk, 'item': obj.item_id, 'text': obj.text, 'is_hidden': obj.is_hidden}
        else:
            serializer = lambda obj: {'id': obj.pk, 'comment': obj.comment_id, 'reason': obj.reason}
        return JsonResponse(page_data(page, serializer))
    return render(request, 'newsdesk/manage.html', {'page': page, 'tab': tab, **desk_context(request)})


@endpoint(('GET', 'POST'), auth=True)
def edit(request, pk=None):
    scope = managed_items(request.user)
    item = get_object_or_404(scope, pk=pk) if pk else None
    form = NewsItemForm(payload(request) if request.method == 'POST' else None, request.FILES or None, instance=item, user=request.user, pincode_as_code=not api(request))
    if request.method == 'POST':
        try:
            item = services.save_item(request.user, payload(request), request.FILES, pk, pincode_as_code=not api(request))
        except ValidationError as error:
            if api(request):
                raise
            form.is_valid()
            if not form.errors:
                form.add_error(None, error.messages)
        else:
            if api(request):
                return JsonResponse(serialize_item(item), status=200 if pk else 201)
            messages.success(request, 'Story published.' if item.status == 'published' else 'Draft saved.')
            return redirect('newsdesk:manage')
    if api(request):
        if not item:
            raise Http404()
        return JsonResponse({**serialize_item(item), 'body': item.body})
    return render(request, 'newsdesk/form.html', {
        'form': form, 'item': item, 'heading': 'Edit your story' if item else 'Create a local story',
        'intro': 'Keep your neighbourhood informed. Choose Draft to finish later, or Published to make it visible.',
        'submit': 'Save story', **desk_context(request),
    }, status=400 if request.method == 'POST' else 200)


@endpoint(('POST',), auth=True)
def moderate(request, pk):
    obj = services.moderate_comment(request.user, pk, payload(request).get('action'))
    if api(request):
        return JsonResponse({'id': obj.pk, 'is_hidden': obj.is_hidden})
    messages.success(request, 'Moderation saved.')
    return redirect(reverse('newsdesk:manage') + '?tab=comments')


@endpoint(('GET', 'POST'), auth=True)
def agents(request, pk=None):
    if not is_admin(request.user):
        raise PermissionDenied('News Desk admin access is required.')
    agent = get_object_or_404(NewsAgent, pk=pk) if pk else None
    form = AgentForm(payload(request) if request.method == 'POST' else None, instance=agent)
    if request.method == 'POST' and form.is_valid():
        agent = form.save()
        if api(request):
            return JsonResponse({'id': agent.pk, 'user': agent.user_id, 'pincode': agent.pincode.code, 'is_active': agent.is_active}, status=200 if pk else 201)
        messages.success(request, 'News Agent assignment saved.')
        return redirect('newsdesk:agents')
    page = Paginator(NewsAgent.objects.select_related('user', 'pincode').order_by('pk'), 30).get_page(request.GET.get('page'))
    if api(request):
        if request.method == 'POST':
            services.valid(form)
        serialize = lambda obj: {'id': obj.pk, 'user': obj.user_id, 'pincode': obj.pincode.code, 'is_active': obj.is_active}
        return JsonResponse(serialize(agent) if pk else page_data(page, serialize))
    return render(request, 'newsdesk/agents.html', {'form': form, 'page': page, **desk_context(request)}, status=400 if request.method == 'POST' else 200)


@endpoint()
def media(request, pk, kind):
    if kind not in {'photo', 'video'}:
        raise Http404()
    item = published_items().filter(pk=pk).first()
    if not item:
        item = get_object_or_404(managed_items(request.user), pk=pk)
    field = getattr(item, kind)
    if not field:
        raise Http404()
    try:
        stream = field.open('rb')
    except FileNotFoundError:
        raise Http404()
    response = FileResponse(stream, content_type=mimetypes.guess_type(field.name)[0] or 'application/octet-stream')
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response








@endpoint()
def pincodes(request):
    query = active_pincodes()
    prefix = request.GET.get('q', '').strip()
    if prefix and (not prefix.isascii() or not prefix.isdigit() or len(prefix) > 6):
        raise ValidationError('Search with up to six pincode digits.')
    if prefix:
        query = query.filter(code__startswith=prefix)
    page = Paginator(query, 50).get_page(request.GET.get('page'))
    return JsonResponse(page_data(page, lambda pin: {'id': pin.pk, 'code': pin.code, 'area': pin.area_name}))
