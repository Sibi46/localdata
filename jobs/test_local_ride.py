from datetime import timedelta
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .local_ride import trips
from .models import Conversation, Message, RideRequest, RideTrip, User, UserNotification


class LocalRideTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user('ride-owner', first_name='Sibi', phone='9876501122', city='Vandavasi')
        cls.rider = User.objects.create_user('ride-rider', first_name='Priya', phone='9876501133')
        cls.other = User.objects.create_user('ride-other', first_name='Other', phone='9876501144')
        cls.admin = User.objects.create_user('ride-admin', admin_role='super_admin')

    def setUp(self):
        self.client.force_login(self.owner)

    def trip(self, **values):
        data = dict(owner=self.owner, origin='Vandavasi', destination='Chennai', departure_at=timezone.now()+timedelta(days=1), vehicle='bike', seats=1, meeting_area='Bus stand')
        data.update(values)
        return RideTrip.objects.create(**data)

    def payload(self, **values):
        data = dict(origin='Vandavasi', destination='Chennai', departure_at=timezone.localtime(timezone.now()+timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'), vehicle='bike', seats=1, meeting_area='Bus stand', notes='Leaving in the morning')
        data.update(values)
        return data

    def join(self, trip, user=None, **data):
        self.client.force_login(user or self.rider)
        return self.client.post(reverse('ride_join', args=[trip.pk]), data)

    def accept(self, application, user=None, decision='accept'):
        self.client.force_login(user or self.owner)
        return self.client.post(reverse('ride_review', args=[application.trip_id, application.pk]), {'decision': decision})

    def test_hospital_placeholder_is_available_on_home_without_booking(self):
        self.client.logout()
        response=self.client.get('/')
        self.assertContains(response,'data-hospital-launch')
        self.assertContains(response,'datetime="2027-01-01"')
        self.assertContains(response,'January 1, 2027')
        self.assertContains(response,reverse('ride_feed'))
        self.assertFalse(RideTrip.objects.exists())

    def test_guest_and_inactive_accounts_cannot_use_rides(self):
        trip=self.trip()
        self.client.logout()
        for url in [reverse('ride_feed'), reverse('ride_create'), reverse('ride_mine'), trip.get_absolute_url()]:
            self.assertEqual(self.client.get(url).status_code,302)
        self.assertEqual(self.client.post(reverse('ride_create'),self.payload()).status_code,302)
        self.owner.is_active=False;self.owner.save(update_fields=['is_active'])
        self.client.force_login(self.owner)
        self.assertIn(self.client.post(reverse('ride_create'),self.payload()).status_code,(302,403))
        self.assertEqual(RideTrip.objects.count(),1)

    def test_post_uses_account_identity_and_starts_open(self):
        response=self.client.post(reverse('ride_create'),self.payload(owner=self.other.pk,status='completed'))
        self.assertEqual(response.status_code,302)
        trip=RideTrip.objects.get()
        self.assertEqual((trip.owner_id,trip.status,trip.vehicle,trip.seats),(self.owner.pk,'open','bike',1))
        self.assertEqual(response['Location'],trip.get_absolute_url())
        self.assertEqual(timezone.localtime(trip.departure_at).hour,timezone.localtime(timezone.now()+timedelta(days=1)).hour)

    def test_invalid_routes_times_and_capacity_are_rejected(self):
        for values in [{'destination':'  VANDAVASI  '},{'departure_at':timezone.localtime(timezone.now()-timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')},
                       {'departure_at':timezone.localtime(timezone.now()+timedelta(days=91)).strftime('%Y-%m-%dT%H:%M')},
                       {'seats':0},{'seats':2},{'vehicle':'car','seats':8},{'vehicle':'bus'},{'meeting_area':''},{'notes':'x'*501}]:
            with self.subTest(values=values):
                response=self.client.post(reverse('ride_create'),self.payload(**values))
                self.assertEqual(response.status_code,200)
                self.assertTrue(response.context['form'].errors)
                self.assertFalse(RideTrip.objects.exists())

    def test_car_can_offer_seven_places(self):
        self.client.post(reverse('ride_create'),self.payload(vehicle='car',seats=7))
        self.assertEqual(RideTrip.objects.get().seats,7)

    def test_posting_is_limited_to_five_journeys_per_24_hours(self):
        for index in range(5):self.trip(destination=f'Place {index}')
        response=self.client.post(reverse('ride_create'),self.payload())
        self.assertContains(response,'up to 5 journeys in 24 hours')
        self.assertEqual(RideTrip.objects.count(),5)

    def test_feed_filters_expired_closed_and_inactive_owners(self):
        visible=self.trip()
        self.trip(status='full')
        self.trip(status='cancelled');self.trip(status='completed')
        self.trip(departure_at=timezone.now()-timedelta(minutes=1))
        self.other.is_active=False;self.other.save(update_fields=['is_active'])
        self.trip(owner=self.other)
        response=self.client.get(reverse('ride_feed'),{'from':'vanda','to':'chen'})
        self.assertEqual({item.pk for item in response.context['page']},{visible.pk,visible.pk+1})
        self.assertContains(response,'noindex,follow')
        self.assertIn('no-store',response['Cache-Control'])

    def test_feed_capacity_and_owner_labels_do_not_make_per_card_queries(self):
        for index in range(4):self.trip(destination=f'Town {index}')
        with self.assertNumQueries(1):
            self.assertEqual([(trip.owner.first_name,trip.available_seats) for trip in trips()],[('Sibi',1)]*4)

    def test_detail_hides_other_request_notes_and_account_contacts(self):
        trip=self.trip()
        RideRequest.objects.create(trip=trip,requester=self.rider,note='Private meeting request')
        self.client.force_login(self.other)
        response=self.client.get(trip.get_absolute_url())
        for private in ('Private meeting request',self.owner.phone,self.rider.phone):self.assertNotContains(response,private)
        self.owner.first_name='';self.owner.username=self.owner.phone;self.owner.save()
        response=self.client.get(trip.get_absolute_url())
        self.assertContains(response,'Local member');self.assertNotContains(response,self.owner.phone)

    def test_join_is_single_use_and_does_not_create_chat_before_acceptance(self):
        trip=self.trip()
        self.join(trip,note='Please consider my request')
        self.join(trip,note='Duplicate')
        self.assertEqual(RideRequest.objects.count(),1)
        self.assertEqual(UserNotification.objects.filter(user=self.owner).count(),1)
        self.assertFalse(Conversation.objects.exists());self.assertFalse(Message.objects.exists())
        application=RideRequest.objects.get()
        self.assertEqual((application.requester_id,application.status,application.note),(self.rider.pk,'pending','Please consider my request'))

    def test_owner_cannot_join_own_trip_or_submit_a_long_note(self):
        trip=self.trip()
        self.assertEqual(self.join(trip,self.owner).status_code,403)
        self.join(trip,note='x'*301)
        self.assertFalse(RideRequest.objects.exists())

    def test_full_cancelled_completed_and_past_trips_reject_join(self):
        for values in [{'status':'full'},{'status':'cancelled'},{'status':'completed'},{'departure_at':timezone.now()-timedelta(minutes=1)}]:
            self.join(self.trip(**values))
        self.assertFalse(RideRequest.objects.exists())

    def test_request_daily_cap(self):
        for index in range(30):RideRequest.objects.create(trip=self.trip(destination=f'Town {index}'),requester=self.rider)
        trip=self.trip()
        self.join(trip)
        self.assertFalse(trip.requests.exists())

    def test_only_trip_owner_can_review_request(self):
        application=RideRequest.objects.create(trip=self.trip(),requester=self.rider)
        for user in (self.rider,self.other,self.admin):
            self.assertEqual(self.accept(application,user).status_code,403)
        application.refresh_from_db();self.assertEqual(application.status,'pending')

    def test_acceptance_reserves_one_place_and_opens_participant_chat(self):
        trip=self.trip()
        application=RideRequest.objects.create(trip=trip,requester=self.rider)
        self.accept(application)
        application.refresh_from_db();trip.refresh_from_db()
        self.assertEqual((application.status,trip.status,trip.available_seats),('accepted','full',0))
        conversation=application.conversation
        self.assertEqual({conversation.user_a_id,conversation.user_b_id},{self.owner.pk,self.rider.pk})
        self.assertEqual(Message.objects.count(),1)
        self.assertTrue(UserNotification.objects.filter(user=self.rider,title='Local Ride request accepted').exists())
        self.accept(application)
        self.assertEqual(Message.objects.count(),1)
        self.assertEqual(Conversation.objects.count(),1)

    def test_existing_conversation_is_reused(self):
        first,second=sorted([self.owner.pk,self.rider.pk])
        conversation=Conversation.objects.create(user_a_id=first,user_b_id=second)
        previous=timezone.now()-timedelta(days=1)
        Conversation.objects.filter(pk=conversation.pk).update(updated_at=previous)
        application=RideRequest.objects.create(trip=self.trip(),requester=self.rider)
        self.accept(application)
        application.refresh_from_db();self.assertEqual(application.conversation_id,conversation.pk)
        conversation.refresh_from_db();self.assertGreater(conversation.updated_at,previous)
        self.assertEqual(Conversation.objects.count(),1)

    def test_last_place_cannot_be_assigned_twice(self):
        trip=self.trip()
        first=RideRequest.objects.create(trip=trip,requester=self.rider)
        second=RideRequest.objects.create(trip=trip,requester=self.other)
        self.accept(first);self.accept(second)
        second.refresh_from_db();self.assertEqual(second.status,'pending')
        self.assertEqual(trip.requests.filter(status='accepted').count(),1)
        self.assertEqual(Message.objects.count(),1)

    def test_invalid_review_and_inactive_requester_do_not_reserve_places(self):
        application=RideRequest.objects.create(trip=self.trip(),requester=self.rider)
        self.accept(application,decision='unknown')
        self.rider.is_active=False;self.rider.save(update_fields=['is_active'])
        self.accept(application)
        application.refresh_from_db();self.assertEqual(application.status,'pending')
        self.assertFalse(Conversation.objects.exists())

    def test_decline_does_not_reserve_place_or_expose_chat(self):
        application=RideRequest.objects.create(trip=self.trip(),requester=self.rider)
        self.accept(application,decision='reject')
        application.refresh_from_db();self.assertEqual(application.status,'rejected')
        self.assertEqual(application.trip.available_seats,1)
        self.assertFalse(Conversation.objects.exists())

    def test_review_request_must_belong_to_url_trip(self):
        application=RideRequest.objects.create(trip=self.trip(),requester=self.rider)
        other_trip=self.trip()
        self.assertEqual(self.client.post(reverse('ride_review',args=[other_trip.pk,application.pk]),{'decision':'accept'}).status_code,404)

    def test_withdrawal_reopens_full_trip_and_keeps_history(self):
        trip=self.trip();application=RideRequest.objects.create(trip=trip,requester=self.rider)
        self.accept(application)
        self.client.force_login(self.rider)
        self.client.post(reverse('ride_withdraw',args=[trip.pk]))
        trip.refresh_from_db();application.refresh_from_db()
        self.assertEqual((trip.status,trip.available_seats,application.status),('open',1,'withdrawn'))
        count=UserNotification.objects.count()
        self.client.post(reverse('ride_withdraw',args=[trip.pk]))
        self.assertEqual(UserNotification.objects.count(),count)
        self.join(trip)
        self.assertEqual(trip.requests.count(),1)
        self.assertEqual(RideRequest.objects.get().status,'withdrawn')

    def test_other_user_cannot_withdraw_someone_elses_request(self):
        trip=self.trip();RideRequest.objects.create(trip=trip,requester=self.rider)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(reverse('ride_withdraw',args=[trip.pk])).status_code,404)

    def test_cancel_notifies_participants_once_without_deleting_history(self):
        trip=self.trip(vehicle='car',seats=2)
        accepted=RideRequest.objects.create(trip=trip,requester=self.rider)
        pending=RideRequest.objects.create(trip=trip,requester=self.other)
        self.accept(accepted)
        self.client.post(reverse('ride_status',args=[trip.pk]),{'status':'cancelled'})
        trip.refresh_from_db();self.assertEqual(trip.status,'cancelled')
        self.assertEqual(trip.requests.filter(status='cancelled').count(),2)
        count=UserNotification.objects.count()
        self.client.post(reverse('ride_status',args=[trip.pk]),{'status':'cancelled'})
        self.assertEqual(UserNotification.objects.count(),count)
        self.assertEqual(Conversation.objects.count(),1)

    def test_superadmin_can_cancel_but_unrelated_users_and_state_admin_cannot(self):
        trip=self.trip()
        for user in [self.other,User.objects.create_user('ride-state-admin',admin_role='state_admin')]:
            self.client.force_login(user)
            self.assertEqual(self.client.post(reverse('ride_status',args=[trip.pk]),{'status':'cancelled'}).status_code,403)
            self.assertEqual(self.client.get(reverse('ride_admin')).status_code,403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('ride_admin')).status_code,200)
        self.client.post(reverse('ride_status',args=[trip.pk]),{'status':'cancelled'})
        trip.refresh_from_db();self.assertEqual(trip.status,'cancelled')

    def test_completion_only_after_departure_and_no_reopening(self):
        trip=self.trip()
        self.client.post(reverse('ride_status',args=[trip.pk]),{'status':'completed'})
        trip.refresh_from_db();self.assertEqual(trip.status,'open')
        RideTrip.objects.filter(pk=trip.pk).update(departure_at=timezone.now()-timedelta(hours=1))
        self.client.post(reverse('ride_status',args=[trip.pk]),{'status':'completed'})
        trip.refresh_from_db();self.assertEqual(trip.status,'completed')
        self.client.post(reverse('ride_status',args=[trip.pk]),{'status':'open'})
        trip.refresh_from_db();self.assertEqual(trip.status,'completed')

    def test_private_chat_requires_acceptance_and_participation(self):
        trip=self.trip();application=RideRequest.objects.create(trip=trip,requester=self.rider)
        url=reverse('ride_chat',args=[trip.pk,application.pk])
        self.client.force_login(self.rider)
        self.assertEqual(self.client.post(url).status_code,403)

        self.accept(application)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(url).status_code,403)
        self.client.force_login(self.rider)
        application.refresh_from_db()
        self.assertRedirects(self.client.post(url),reverse('chat_room',args=[application.conversation_id]))
        self.client.force_login(self.owner)
        self.client.post(reverse('ride_status',args=[trip.pk]),{'status':'cancelled'})
        self.client.force_login(self.rider)
        self.assertEqual(self.client.post(url).status_code,403)

    def test_wrong_participant_conversation_cannot_be_reused(self):
        trip=self.trip()
        first,second=sorted([self.rider.pk,self.other.pk])
        conversation=Conversation.objects.create(user_a_id=first,user_b_id=second)
        application=RideRequest.objects.create(trip=trip,requester=self.rider,status='accepted',conversation=conversation)
        self.client.force_login(self.rider)
        self.assertEqual(self.client.post(reverse('ride_chat',args=[trip.pk,application.pk])).status_code,403)

    def test_all_mutations_are_post_only_and_csrf_protected(self):
        trip=self.trip();application=RideRequest.objects.create(trip=trip,requester=self.rider)
        urls=[reverse('ride_join',args=[trip.pk]),reverse('ride_withdraw',args=[trip.pk]),reverse('ride_status',args=[trip.pk]),
              reverse('ride_review',args=[trip.pk,application.pk]),reverse('ride_chat',args=[trip.pk,application.pk])]
        client=Client(enforce_csrf_checks=True);client.force_login(self.owner)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code,405)
            self.assertEqual(client.post(url).status_code,403)
        self.assertEqual(client.post(reverse('ride_create'),self.payload()).status_code,403)

    def test_acceptance_rolls_back_if_notification_fails(self):
        application=RideRequest.objects.create(trip=self.trip(),requester=self.rider)
        with patch('jobs.local_ride.notify',side_effect=RuntimeError('test notification failure')):
            with self.assertRaises(RuntimeError):self.accept(application)
        application.refresh_from_db();self.assertEqual(application.status,'pending')
        self.assertEqual(application.trip.status,'open')
        self.assertFalse(Conversation.objects.exists());self.assertFalse(Message.objects.exists())

    def test_mine_contains_only_own_posts_and_requests(self):
        own=self.trip();another=self.trip(owner=self.other)
        RideRequest.objects.create(trip=another,requester=self.rider)
        self.client.force_login(self.rider)
        response=self.client.get(reverse('ride_mine'))
        self.assertEqual(response.context['page'].paginator.count,0)
        self.assertEqual([item.trip_id for item in response.context['applications']],[another.pk])
        self.client.force_login(self.owner)
        response=self.client.get(reverse('ride_mine'))
        self.assertEqual([item.pk for item in response.context['page']],[own.pk])
        self.assertEqual(response.context['applications'].paginator.count,0)

    def test_notes_are_escaped(self):
        trip=self.trip(notes='<script>alert(1)</script>')
        response=self.client.get(trip.get_absolute_url())
        self.assertContains(response,'&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response,'<script>alert(1)</script>')

    def test_database_enforces_unique_requests_and_bike_capacity(self):
        trip=self.trip();RideRequest.objects.create(trip=trip,requester=self.rider)
        with self.assertRaises(IntegrityError),transaction.atomic():RideRequest.objects.create(trip=trip,requester=self.rider)
        with self.assertRaises(IntegrityError),transaction.atomic():self.trip(seats=2)
