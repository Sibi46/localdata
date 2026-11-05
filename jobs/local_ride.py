"""Account-only travel posts, capacity-checked requests and private connections."""
from datetime import timedelta
from functools import wraps

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .models import Conversation, Message, RideRequest, RideTrip, User, UserNotification
from .pilot_admin import is_superadmin, private


def member(view):
    @never_cache
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_active:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped


class TripForm(forms.ModelForm):
    departure_at = forms.DateTimeField(label='Departure date and time',
        input_formats=['%Y-%m-%dT%H:%M'],
        widget=forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
        help_text='India time (IST). Choose a time at least 5 minutes ahead, within 90 days.')

    class Meta:
        model = RideTrip
        fields = ['origin', 'destination', 'departure_at', 'vehicle', 'seats', 'meeting_area', 'notes']
        labels = {'origin': 'From', 'destination': 'To', 'seats': 'Passenger places (excluding you)',
                  'meeting_area': 'Meeting area / landmark', 'notes': 'Journey details (optional)'}
        widgets = {'origin': forms.TextInput(attrs={'placeholder': 'Vandavasi'}),
                   'destination': forms.TextInput(attrs={'placeholder': 'Chennai'}),
                   'notes': forms.Textarea(attrs={'rows': 3, 'maxlength': 500})}
        help_texts = {'seats': 'Bike: 1 passenger. Car: up to 7 passengers.',
                      'notes': 'Keep phone numbers and private addresses out of public notes. Use chat after acceptance.'}

    def clean(self):
        data = super().clean()
        for key in ('origin', 'destination', 'meeting_area'):
            if data.get(key): data[key] = ' '.join(data[key].split())
        if data.get('origin') and data.get('destination') and data['origin'].casefold() == data['destination'].casefold():
            self.add_error('destination', 'Choose a destination different from your starting place.')
        departure = data.get('departure_at')
        if departure and not timezone.now() + timedelta(minutes=5) <= departure <= timezone.now() + timedelta(days=90):
            self.add_error('departure_at', 'Choose a departure at least 5 minutes ahead and within 90 days.')
        if data.get('vehicle') == 'bike' and data.get('seats') != 1:
            self.add_error('seats', 'A bike can offer only 1 passenger place.')
        return data


class JoinForm(forms.Form):
    note = forms.CharField(label='Message to the traveller (optional)', max_length=300, required=False,
                           widget=forms.Textarea(attrs={'rows': 3, 'maxlength': 300}))


def trips():
    return RideTrip.objects.select_related('owner').annotate(
        accepted_count=Count('requests', filter=Q(requests__status='accepted'))).order_by('departure_at', 'pk')


def notify(user, trip, title):
    UserNotification.objects.create(user=user, title=title, message=str(trip),
        link=trip.get_absolute_url(), notif_type='info')


def chat_for(trip, application):
    first, second = sorted([trip.owner_id, application.requester_id])
    if application.conversation_id:
        if not Conversation.objects.filter(pk=application.conversation_id, user_a_id=first, user_b_id=second).exists():
            raise PermissionDenied('This chat does not belong to the journey participants.')
        return application.conversation_id
    conversation = Conversation.objects.filter(user_a_id=first, user_b_id=second).order_by('pk').first()
    if conversation is None:
        conversation = Conversation.objects.create(user_a_id=first, user_b_id=second)
    application.conversation = conversation
    application.save(update_fields=['conversation', 'updated_at'])
    return conversation.pk


@member
@require_GET
def feed(request):
    query = trips().filter(owner__is_active=True, status__in=['open', 'full'], departure_at__gt=timezone.now())
    origin = request.GET.get('from', '').strip()[:80]
    destination = request.GET.get('to', '').strip()[:80]
    if origin: query = query.filter(origin__icontains=origin)
    if destination: query = query.filter(destination__icontains=destination)
    return render(request, 'rides/feed.html', {'page': Paginator(query, 12).get_page(request.GET.get('page')),
        'origin': origin, 'destination': destination})


@member
@require_http_methods(['GET', 'POST'])
def create(request):
    form = TripForm(request.POST if request.method == 'POST' else None,
                    initial={'origin': request.user.city or 'Vandavasi', 'seats': 1})
    if request.method == 'POST' and form.is_valid():
        # Lock a stable per-account row: repeated tabs cannot bypass the daily cap.
        with transaction.atomic():
            User.objects.select_for_update().get(pk=request.user.pk)
            if RideTrip.objects.filter(owner=request.user, created_at__gte=timezone.now()-timedelta(days=1)).count() >= 5:
                form.add_error(None, 'You can post up to 5 journeys in 24 hours. Manage your existing rides below.')
            else:
                trip = form.save(commit=False); trip.owner = request.user; trip.save()
                messages.success(request, 'Your journey is posted. You can review requests here.')
                return redirect(trip)
    return render(request, 'rides/form.html', {'form': form})


@member
@require_GET
def mine(request):
    return render(request, 'rides/mine.html', {
        'page': Paginator(trips().filter(owner=request.user).order_by('-created_at'), 12).get_page(request.GET.get('page')),
        'applications': Paginator(RideRequest.objects.filter(requester=request.user).select_related('trip', 'trip__owner').order_by('-created_at'), 12).get_page(request.GET.get('requests_page'))})


@member
@require_GET
def detail(request, pk):
    query = trips()
    if not is_superadmin(request.user): query = query.filter(owner__is_active=True)
    trip = get_object_or_404(query, pk=pk)
    manager = trip.owner_id == request.user.pk or is_superadmin(request.user)
    application = trip.requests.filter(requester=request.user).first()
    return render(request, 'rides/detail.html', {'trip': trip, 'manager': manager,
        'is_owner': trip.owner_id == request.user.pk, 'application': application, 'join_form': JoinForm(),
        'can_join': trip.owner_id != request.user.pk and application is None and trip.status == 'open' and trip.departure_at > timezone.now(),
        'can_withdraw': application and application.status in ('pending', 'accepted') and trip.status in ('open', 'full') and trip.departure_at > timezone.now(),
        'can_complete': trip.owner_id == request.user.pk and trip.status in ('open', 'full') and trip.departure_at <= timezone.now(),
        'departed': trip.departure_at <= timezone.now(),
        'requests_page': Paginator(trip.requests.select_related('requester'), 20).get_page(request.GET.get('page')) if manager else None})


@member
@require_POST
def join(request, pk):
    form = JoinForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Keep your request message within 300 characters.')
        return redirect('ride_detail', pk=pk)
    with transaction.atomic():
        trip = get_object_or_404(RideTrip.objects.select_for_update().select_related('owner'), pk=pk, owner__is_active=True)
        if trip.owner_id == request.user.pk: raise PermissionDenied('You cannot join your own journey.')
        if trip.status != 'open' or trip.departure_at <= timezone.now():
            messages.error(request, 'This journey is no longer accepting requests.')
        elif trip.requests.filter(requester=request.user).exists():
            messages.info(request, 'You already sent a request for this journey. Check its status below.')
        else:
            User.objects.select_for_update().get(pk=request.user.pk)
            if RideRequest.objects.filter(requester=request.user, created_at__gte=timezone.now()-timedelta(days=1)).count() >= 30:
                messages.error(request, 'You can request up to 30 journeys in 24 hours.')
            else:
                RideRequest.objects.create(trip=trip, requester=request.user, note=form.cleaned_data['note'])
                notify(trip.owner, trip, 'New Local Ride request')
                messages.success(request, 'Request sent. Your place is confirmed only after the traveller accepts.')
    return redirect('ride_detail', pk=pk)


@member
@require_POST
def review(request, pk, request_id):
    with transaction.atomic():
        trip = get_object_or_404(RideTrip.objects.select_for_update(), pk=pk)
        if trip.owner_id != request.user.pk: raise PermissionDenied
        application = get_object_or_404(RideRequest.objects.select_for_update().select_related('requester'), pk=request_id, trip=trip)
        decision = request.POST.get('decision')
        if decision not in ('accept', 'reject'):
            messages.error(request, 'Choose Accept or Decline.')
        elif application.status != 'pending':
            messages.info(request, 'This request has already been handled.')
        elif trip.status not in ('open', 'full') or trip.departure_at <= timezone.now():
            messages.error(request, 'This journey is closed or has already departed.')
        elif decision == 'reject':
            application.status = 'rejected'; application.save(update_fields=['status', 'updated_at'])
            notify(application.requester, trip, 'Local Ride request declined')
        elif not application.requester.is_active:
            messages.error(request, 'This account is no longer active.')
        elif trip.requests.filter(status='accepted').count() >= trip.seats:
            messages.error(request, 'All passenger places are already filled.')
        else:
            application.status = 'accepted'; application.save(update_fields=['status', 'updated_at'])
            conversation_id = chat_for(trip, application)
            Message.objects.create(conversation_id=conversation_id, sender=request.user, receiver=application.requester,
                content=f'Your Local Ride request for {trip} has been accepted. Confirm your meeting details here.', msg_type='text')
            Conversation.objects.filter(pk=conversation_id).update(updated_at=timezone.now())
            notify(application.requester, trip, 'Local Ride request accepted')
            if trip.requests.filter(status='accepted').count() >= trip.seats:
                trip.status = 'full'; trip.save(update_fields=['status', 'updated_at'])
            messages.success(request, 'Request accepted. You can now open private chat.')
    return redirect('ride_detail', pk=pk)


@member
@require_POST
def withdraw(request, pk):
    with transaction.atomic():
        trip = get_object_or_404(RideTrip.objects.select_for_update(), pk=pk)
        application = get_object_or_404(RideRequest.objects.select_for_update(), trip=trip, requester=request.user)
        if application.status in ('pending', 'accepted') and trip.status in ('open', 'full') and trip.departure_at > timezone.now():
            application.status = 'withdrawn'; application.save(update_fields=['status', 'updated_at'])
            if trip.status == 'full' and trip.requests.filter(status='accepted').count() < trip.seats:
                trip.status = 'open'; trip.save(update_fields=['status', 'updated_at'])
            notify(trip.owner, trip, 'Local Ride request withdrawn')
            messages.success(request, 'Your request was withdrawn.')
        else: messages.info(request, 'This request can no longer be withdrawn.')
    return redirect('ride_detail', pk=pk)


@member
@require_POST
def change_status(request, pk):
    with transaction.atomic():
        trip = get_object_or_404(RideTrip.objects.select_for_update().select_related('owner'), pk=pk)
        if trip.owner_id != request.user.pk and not is_superadmin(request.user): raise PermissionDenied
        status = request.POST.get('status')
        if status not in ('cancelled', 'completed'):
            messages.error(request, 'Choose Cancel or Complete.')
        elif trip.status in ('cancelled', 'completed'):
            messages.info(request, 'This journey is already closed.')
        elif status == 'completed' and (trip.owner_id != request.user.pk or trip.departure_at > timezone.now()):
            messages.error(request, 'Only the traveller can complete a journey after departure.')
        else:
            trip.status = status; trip.save(update_fields=['status', 'updated_at'])
            participants = list(trip.requests.filter(status__in=['pending', 'accepted']).select_related('requester'))
            if status == 'cancelled':
                trip.requests.filter(status__in=['pending', 'accepted']).update(status='cancelled', updated_at=timezone.now())
                for application in participants: notify(application.requester, trip, 'Local Ride journey cancelled')
                if request.user.pk != trip.owner_id: notify(trip.owner, trip, 'Your Local Ride journey was cancelled by admin')
            messages.success(request, 'Journey '+trip.get_status_display().lower()+'.')
    return redirect('ride_detail', pk=pk)


@member
@require_POST
def chat(request, pk, request_id):
    with transaction.atomic():
        trip = get_object_or_404(RideTrip.objects.select_for_update(), pk=pk)
        application = get_object_or_404(RideRequest.objects.select_for_update(), pk=request_id, trip=trip)
        if request.user.pk not in (trip.owner_id, application.requester_id): raise PermissionDenied
        if application.status != 'accepted' or trip.status == 'cancelled': raise PermissionDenied
        conversation_id = chat_for(trip, application)
    return redirect('chat_room', conv_id=conversation_id)


@private
@require_GET
def admin_rides(request):
    return render(request, 'rides/feed.html', {'admin_mode': True,
        'page': Paginator(trips().order_by('-created_at'), 20).get_page(request.GET.get('page'))})
