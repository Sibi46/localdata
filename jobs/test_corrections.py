from unittest import skip
from datetime import date, time, timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from jobs.models import User, CompanyProfile, LocalOffer
from community.models import FamilySetup, FamilyMember, CommunityEvent, EventRSVP, CommunityEventUserRating
from portal.models import (Community, CommunityMember, Event, EventParticipant, AttendeeRating,
                           MemberPoints, PointAuditLog, Participation)


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False,
                   CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}},
                   PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class CorrectionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', user_type='shop', pincode='600073')
        self.other = User.objects.create_user('other')
        self.profile = CompanyProfile.objects.create(user=self.owner, company_name='Example Business')
        self.community = Community.objects.create(name='Test Community', created_by=self.owner,
                                                   purpose='Testing', pincode='600073')
        for user in (self.owner, self.other):
            CommunityMember.objects.create(community=self.community, user=user, status='approved')
        # Retired points signals no longer create records during test setup.

    def login(self, user):
        self.client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')

    @skip('Family profiles retired; boundary covered by jobs.test_feature_scope')
    def test_family_public_private_icon_and_direct_access(self):
        setup = FamilySetup.objects.create(user=self.owner, setup_done=True, house_name='Family House')
        member = FamilyMember.objects.create(creator=self.owner, name='Family Member', member_type='son')
        url = reverse('family_profile', args=[self.owner.pk])
        business_url = reverse('business_profile', args=[self.profile.company_id])
        self.login(self.other)
        self.assertNotContains(self.client.get(business_url), url)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(reverse('family_member_detail', args=[member.pk])).status_code, 404)
        self.login(self.owner)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.post(reverse('family_visibility'), {'visibility': 'public'})
        self.login(self.other)
        self.assertContains(self.client.get(business_url), url)
        self.assertContains(self.client.get(url), 'Family Member')
        self.client.post(reverse('family_visibility'), {'visibility': 'private', 'user_id': self.owner.pk})
        setup.refresh_from_db()
        self.assertTrue(setup.is_public)
        self.login(self.owner)
        self.client.post(reverse('family_visibility'), {'visibility': 'private'})
        self.login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)

    @skip('Retired feature; absence and data preservation covered by jobs.test_feature_scope')
    def test_linked_family_member_can_view_private_profile(self):
        FamilySetup.objects.create(user=self.owner, setup_done=True)
        FamilyMember.objects.create(creator=self.owner, name='Child', member_type='son', child_linked_user=self.other)
        self.login(self.other)
        self.assertEqual(self.client.get(reverse('family_profile', args=[self.owner.pk])).status_code, 200)

    @skip('Retired feature; absence and data preservation covered by jobs.test_feature_scope')
    def test_community_rating_saves_once_and_awards_points(self):
        event = CommunityEvent.objects.create(posted_by=self.owner, title='Long event ' * 15,
            event_date=date.today(), event_time=time(12), venue='Chennai')
        for user in (self.owner, self.other):
            EventRSVP.objects.create(user=user, event=event, status='going')
        self.login(self.owner)
        url = reverse('event_rate_user', args=[event.pk])
        for _ in range(2):
            self.assertEqual(self.client.post(url, {f'rating_{self.other.pk}': '5'}).status_code, 302)
        self.assertEqual(CommunityEventUserRating.objects.count(), 1)
        self.assertEqual(MemberPoints.objects.get(user=self.other, community=self.community).total_points, self.initial_points + 5)
        self.assertLessEqual(len(PointAuditLog.objects.filter(action__startswith='Peer rating').get().action), 100)

    @skip('Retired feature; absence and data preservation covered by jobs.test_feature_scope')
    def test_portal_rating_valid_invalid_and_outsider(self):
        event = Event.objects.create(community=self.community, created_by=self.owner,
            name='Event', date=date.today(), time=time(12), location='Chennai')
        for user in (self.owner, self.other):
            EventParticipant.objects.create(event=event, user=user, status='approved')
        url = reverse('portal_event_attendee_ratings', args=[event.pk])
        self.login(User.objects.create_user('outsider'))
        self.client.post(url, {'ratee_id': self.other.pk, 'rating': '5'})
        self.assertFalse(AttendeeRating.objects.exists())
        self.login(self.owner)
        self.assertEqual(self.client.post(url, {'ratee_id': self.other.pk, 'rating': 'bad'}).status_code, 302)
        self.assertFalse(AttendeeRating.objects.exists())
        self.client.post(url, {'ratee_id': self.other.pk, 'rating': '4'})
        self.assertEqual(AttendeeRating.objects.get().rating, 4)
        self.assertEqual(MemberPoints.objects.get(user=self.other).total_points, self.initial_points + 4)

    @skip('Retired feature; absence and data preservation covered by jobs.test_feature_scope')
    def test_participation_records_grouped_under_person(self):
        self.login(self.owner)
        url = reverse('record_participation', args=[self.community.slug])
        self.assertEqual(self.client.post(url, {'user_id': self.other.pk, 'role': 'volunteer'}).status_code, 302)
        response = self.client.get(url)
        self.assertContains(response, 'Participation records')
        self.assertContains(response, 'other')
        self.assertEqual(len(response.context['records']), 1)
        self.assertEqual(Participation.objects.get().status, 'confirmed')
        response = self.client.get(reverse('portal_member_profile', args=[self.other.pk]))
        self.assertContains(response, 'Participation records')
        self.assertEqual(len(response.context['participation_records']), 1)

    def test_business_listing_profile_registration_and_share(self):
        self.login(self.owner)
        response = self.client.get('/businesses/', {'pincode': '600073'})
        self.assertContains(response, self.profile.company_name)
        self.assertNotContains(self.client.get('/businesses/', {'pincode': '999999'}), self.profile.company_name)
        self.login(self.owner)
        self.assertRedirects(self.client.get('/register/'), '/account/', fetch_redirect_response=False)
        response = self.client.get(reverse('business_profile', args=[self.profile.company_id]))
        self.assertContains(response, self.profile.company_name)
        self.assertNotContains(response, '/portal/')

    def test_my_offers_owned_pending_and_withdrawal(self):
        self.login(self.owner)
        self.client.post(reverse('offer_post'), {'business_name': self.profile.company_name,
            'title': 'My pending offer', 'discount_text': '10% OFF'})
        offer = LocalOffer.objects.get()
        self.assertEqual(offer.owner, self.owner)
        self.assertContains(self.client.get(reverse('my_offers')), 'My pending offer')
        self.login(self.other)
        self.assertNotContains(self.client.get(reverse('my_offers')), 'My pending offer')
        self.assertEqual(self.client.post(reverse('my_offers'), {'offer_id': offer.pk}).status_code, 404)
        self.login(self.owner)
        offer.is_active = True
        offer.save()
        self.client.post(reverse('my_offers'), {'offer_id': offer.pk})
        offer.refresh_from_db()
        self.assertFalse(offer.is_active)

    @skip('Retired feature; absence and data preservation covered by jobs.test_feature_scope')
    def test_event_history_scopes_both_event_types_and_excludes_upcoming(self):
        past = date.today() - timedelta(days=5)
        future = date.today() + timedelta(days=5)
        own = Event.objects.create(created_by=self.owner, name='My past event', date=past,
                                    time=time(12), location='Chennai')
        joined = Event.objects.create(created_by=self.other, name='Joined past event', date=past,
                                       time=time(12), location='Chennai')
        EventParticipant.objects.create(event=joined, user=self.owner, status='approved')
        Event.objects.create(created_by=self.other, name='Unrelated past event', date=past,
                             time=time(12), location='Chennai')
        Event.objects.create(created_by=self.owner, name='Upcoming event', date=future,
                             time=time(12), location='Chennai')
        Event.objects.create(created_by=self.owner, name='Still ongoing event', date=past,
                             end_date=future, time=time(12), location='Chennai')
        local = CommunityEvent.objects.create(posted_by=self.other, title='Local past event',
                                               event_date=past, venue='Chennai')
        EventRSVP.objects.create(event=local, user=self.owner, status='going')
        self.login(self.owner)
        response = self.client.get(reverse('portal_event_history'))
        for name in ('My past event', 'Joined past event', 'Local past event'):
            self.assertContains(response, name)
        for name in ('Unrelated past event', 'Upcoming event', 'Still ongoing event'):
            self.assertNotContains(response, name)
        self.assertEqual(response.context['history'].paginator.count, 3)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('portal_event_history')).status_code, 302)

    def test_dashboard_business_logos_link_to_full_profiles(self):
        self.login(self.owner)
        response = self.client.get(reverse('employer_dashboard'))
        self.assertContains(response, 'View public shop')
        self.assertContains(response, reverse('business_profile', args=[self.profile.company_id]))
        self.assertNotContains(response, '/portal/history/')
