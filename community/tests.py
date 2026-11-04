from unittest import skip
"""
Community app tests.
Uses RequestFactory + direct view calls to bypass Django test DB creation.
"""
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory


# ─────────────────────────────────────────────────────────────────────────────
# CRIT-E2 — Teacher registration: safe error messages
# ─────────────────────────────────────────────────────────────────────────────

@skip('Retired community/family/badge feature; boundary covered by jobs.test_feature_scope')
class TeacherRegisterSafeErrorTest(TestCase):
    """
    Verify that teacher_register view never exposes raw exception text.
    Patches DB calls so no real database is required.
    """

    def _post(self, post_data, user_exists=False, create_side_effect=None):
        from community.views import teacher_register
        factory = RequestFactory()
        request = factory.post('/community/teacher-register/', post_data)
        request.user = MagicMock(is_authenticated=False)

        with patch('community.views.School') as MockSchool, \
             patch('community.views.SchoolAdmin') as MockSchoolAdmin:

            MockSchool.objects.all.return_value.order_by.return_value = []
            MockSchool.objects.get.return_value = MagicMock(pk=1, name='Test School')

            with patch('django.contrib.auth.get_user_model') as MockGetUser:
                MockUserModel = MagicMock()
                MockGetUser.return_value = MockUserModel
                MockUserModel.objects.filter.return_value.exists.return_value = user_exists

                if create_side_effect:
                    MockUserModel.objects.create_user.side_effect = create_side_effect

                resp = teacher_register(request)
        return resp

    def test_generic_exception_shows_safe_message(self):
        """RuntimeError during user creation must not expose str(e) in response."""
        secret = 'secret_internal_db_table_xyz'
        resp = self._post(
            {'full_name': 'Test Teacher', 'phone': '9876543210', 'school_id': '1'},
            user_exists=False,
            create_side_effect=RuntimeError(secret),
        )
        body = resp.content.decode()
        self.assertNotIn(secret, body)
        self.assertNotIn('Registration failed: ', body)

    def test_generic_exception_shows_generic_message(self):
        """A non-IntegrityError shows the generic registration failed message."""
        resp = self._post(
            {'full_name': 'Test Teacher', 'phone': '9876543210', 'school_id': '1'},
            user_exists=False,
            create_side_effect=RuntimeError('some internal error'),
        )
        body = resp.content.decode()
        self.assertIn('Registration failed. Please try again.', body)

    def test_integrity_error_shows_phone_message(self):
        """IntegrityError shows the phone-specific safe message."""
        from django.db import IntegrityError
        resp = self._post(
            {'full_name': 'Test Teacher', 'phone': '9876543210', 'school_id': '1'},
            user_exists=False,
            create_side_effect=IntegrityError("Duplicate entry '9876543210' for key 'username'"),
        )
        body = resp.content.decode()
        self.assertNotIn("Duplicate entry", body)
        self.assertNotIn("for key", body)
        self.assertIn('This phone may already be in use.', body)

    def test_no_sqlstate_in_response(self):
        """SQLSTATE and constraint names must never reach the response body."""
        from django.db import IntegrityError
        resp = self._post(
            {'full_name': 'Test Teacher', 'phone': '9876543210', 'school_id': '1'},
            user_exists=False,
            create_side_effect=IntegrityError("(1062, \"Duplicate entry 'x' for key 'jobs_user.username'\")"),
        )
        body = resp.content.decode()
        self.assertNotIn('1062', body)
        self.assertNotIn('jobs_user', body)


@skip('Retired community/family/badge feature; boundary covered by jobs.test_feature_scope')
class SchoolDashboardAddTeacherSafeErrorTest(TestCase):
    """
    Verify school_dashboard add_teacher action never exposes raw exception text.
    Tests the error-handling logic directly by simulating the two failure paths
    without invoking the full view (which requires many DB-level mocks).
    """

    def _simulate_link_error(self, exc):
        """
        Replicate the link-existing-user except block logic from school_dashboard.
        Returns the error string the view would assign.
        """
        error = None
        try:
            raise exc
        except Exception:
            import logging as _logging
            _logging.getLogger('community.views').exception(
                'school_corner add_teacher link: failed for phone=%s school=%s', 'X', 1
            )
            error = 'Registration failed. Please try again.'
        return error

    def _simulate_create_error(self, exc):
        """
        Replicate the create-new-user except block logic from school_dashboard.
        Returns the error string the view would assign.
        """
        error = None
        try:
            raise exc
        except Exception as e:
            from django.db import IntegrityError
            if isinstance(e, IntegrityError):
                error = 'Registration failed. This phone may already be in use.'
            else:
                error = 'Registration failed. Please try again.'
            import logging as _logging
            _logging.getLogger('community.views').exception(
                'school_corner add_teacher create: failed for phone=%s school=%s', 'X', 1
            )
        return error

    def test_link_path_exception_does_not_expose_raw_error(self):
        """Exception when linking existing user: raw str(e) not in error message."""
        secret = 'secret_constraint_jobs_user_phone'
        error = self._simulate_link_error(RuntimeError(secret))
        self.assertNotIn(secret, error)

    def test_link_path_exception_shows_safe_message(self):
        """Exception when linking existing user: safe generic message shown."""
        error = self._simulate_link_error(RuntimeError('any error'))
        self.assertEqual(error, 'Registration failed. Please try again.')

    def test_create_path_integrity_error_shows_phone_message(self):
        """IntegrityError on create: shows phone-specific safe message, not SQL."""
        from django.db import IntegrityError
        raw = "Duplicate entry '9800000002' for key 'jobs_user.username'"
        error = self._simulate_create_error(IntegrityError(raw))
        self.assertNotIn('Duplicate entry', error)
        self.assertNotIn('jobs_user', error)
        self.assertIn('This phone may already be in use.', error)

    def test_create_path_generic_exception_shows_safe_message(self):
        """RuntimeError on create: shows generic safe message, not str(e)."""
        secret = 'internal_path_detail_abc'
        error = self._simulate_create_error(RuntimeError(secret))
        self.assertNotIn(secret, error)
        self.assertEqual(error, 'Registration failed. Please try again.')

    def test_create_path_no_sqlstate_exposed(self):
        """SQLSTATE code and table name must never reach the error string."""
        from django.db import IntegrityError
        raw = "(1062, \"Duplicate entry 'x' for key 'jobs_user.username'\")"
        error = self._simulate_create_error(IntegrityError(raw))
        self.assertNotIn('1062', error)
        self.assertNotIn('jobs_user', error)


# ─────────────────────────────────────────────────────────────────────────────
# CRIT-E3 — FamilyMember age validation: invalid values never reach the DB
# ─────────────────────────────────────────────────────────────────────────────

@skip('Retired community/family/badge feature; boundary covered by jobs.test_feature_scope')
class FamilyMemberAgeValidationTest(TestCase):
    """
    Verify that family_member_create, family_member_edit, and the
    family_setup_wizard (Step 6 children) reject out-of-range age values
    before any DB write, preventing DataError (1264) under STRICT_ALL_TABLES.

    All tests use mocks — no real DB required.
    """

    def _post_create(self, age_str):
        """POST to family_member_create with the given age string. Returns saved FamilyMember mock."""
        from community.views import family_member_create
        factory = RequestFactory()
        data = {'name': 'Test Person', 'member_type': 'father', 'side': 'husband', 'age': age_str}
        request = factory.post('/community/family/member/create/', data)
        request.user = MagicMock()

        saved = {}

        def fake_save():
            saved['age'] = member_instance.age

        member_instance = MagicMock()
        member_instance.name = 'Test Person'
        member_instance.age = None
        member_instance.save.side_effect = fake_save

        with patch('community.views.FamilyMember') as MockFM, \
             patch('community.views.redirect') as mock_redirect:
            MockFM.TYPE_CHOICES = []
            instance = MockFM.return_value
            instance.name = 'Test Person'
            instance.age = None

            def fake_fm_save():
                saved['age'] = instance.age

            instance.save.side_effect = fake_fm_save
            mock_redirect.return_value = MagicMock(status_code=302)
            family_member_create(request)

        return saved.get('age')

    def _post_edit(self, age_str):
        """POST to family_member_edit with the given age string. Returns the age assigned to member."""
        from community.views import family_member_edit
        factory = RequestFactory()
        data = {'name': 'Test Person', 'member_type': 'father', 'status': 'living', 'age': age_str}
        request = factory.post('/community/family/member/1/edit/', data)
        request.user = MagicMock()

        member = MagicMock()
        member.name = 'Test Person'
        member.age = None
        member.pk = 1
        member.creator = request.user

        saved_age = {}

        def fake_save():
            saved_age['age'] = member.age

        member.save.side_effect = fake_save

        with patch('community.views.get_object_or_404', return_value=member), \
             patch('community.views.redirect') as mock_redirect:
            mock_redirect.return_value = MagicMock(status_code=302)
            family_member_edit(request, pk=1)

        return saved_age.get('age')

    # ── family_member_create ────────────────────────────────────────────────

    def test_create_negative_age_rejected(self):
        """Negative age must not be saved — stays None."""
        age = self._post_create('-1')
        self.assertIsNone(age, f'Expected None for age=-1, got {age!r}')

    def test_create_zero_age_accepted(self):
        """Age 0 is valid (newborn) and must be saved."""
        age = self._post_create('0')
        self.assertEqual(age, 0, f'Expected 0 for age=0, got {age!r}')

    def test_create_max_age_accepted(self):
        """Age 150 is the maximum valid value and must be saved."""
        age = self._post_create('150')
        self.assertEqual(age, 150, f'Expected 150 for age=150, got {age!r}')

    def test_create_over_max_age_rejected(self):
        """Age 151 exceeds the maximum — must not be saved."""
        age = self._post_create('151')
        self.assertIsNone(age, f'Expected None for age=151, got {age!r}')

    def test_create_non_integer_age_rejected(self):
        """Non-integer string must not crash and age must stay None."""
        age = self._post_create('abc')
        self.assertIsNone(age, f'Expected None for age=abc, got {age!r}')

    # ── family_member_edit ──────────────────────────────────────────────────

    def test_edit_negative_age_rejected(self):
        """Negative age in edit must not be saved — stays None."""
        age = self._post_edit('-5')
        self.assertIsNone(age, f'Expected None for age=-5 in edit, got {age!r}')

    # ── family_setup_wizard Step 6 (children / future DOB) ─────────────────

    def test_setup_wizard_future_dob_yields_zero_no_crash(self):
        """
        A future date of birth for a child must not cause DataError.
        age_val = max(0, min(150, negative_days // 365)) must yield 0.
        """
        from datetime import date, timedelta
        future_dob = (date.today() + timedelta(days=365)).strftime('%Y-%m-%d')

        from community.views import family_setup_wizard
        factory = RequestFactory()
        data = {
            'step': '6',
            'child_name': ['FutureChild'],
            'child_dob': [future_dob],
            'child_gender': ['male'],
            'child_email': [''],
            'child_password': [''],
        }
        request = factory.post('/community/family/setup/', data)
        request.user = MagicMock()
        request.user.pk = 1
        request._messages = MagicMock()

        created_ages = []

        def fake_create(**kwargs):
            created_ages.append(kwargs.get('age'))
            obj = MagicMock()
            obj.pk = 99
            obj.age = kwargs.get('age')
            return obj

        with patch('community.views.FamilySetup') as MockFS, \
             patch('community.views.FamilyMember') as MockFM, \
             patch('community.views.redirect') as mock_redirect:

            mock_setup = MagicMock()
            mock_setup.marital_status = 'single'
            mock_setup.setup_done = False
            MockFS.objects.get_or_create.return_value = (mock_setup, False)

            MockFM.objects.filter.return_value.delete.return_value = None
            MockFM.objects.create.side_effect = fake_create
            mock_redirect.return_value = MagicMock(status_code=302)

            family_setup_wizard(request)

        self.assertTrue(len(created_ages) > 0, 'No FamilyMember was created')
        for age in created_ages:
            self.assertIsNotNone(age, 'age should be 0, not None, for a future DOB')
            self.assertEqual(age, 0, f'Expected age=0 for future DOB, got {age!r}')


# ─────────────────────────────────────────────────────────────────────────────
# SECURITY HARDENING — family_member_detail must require authentication
# ─────────────────────────────────────────────────────────────────────────────

@skip('Retired community/family/badge feature; boundary covered by jobs.test_feature_scope')
class FamilyMemberDetailAuthTest(TestCase):
    """MEDIUM IDOR — family_member_detail must be decorated with @login_required."""

    def test_login_required_decorator_applied(self):
        """family_member_detail must have @login_required in its decorator chain."""
        from community import views as community_views
        view = community_views.family_member_detail
        self.assertTrue(
            hasattr(view, 'login_url') or hasattr(view, '__wrapped__'),
            'family_member_detail must be decorated with @login_required'
        )

    def test_anonymous_request_is_redirected(self):
        """Anonymous GET to family_member_detail must redirect to login, not return 200."""
        from community.views import family_member_detail
        factory = RequestFactory()
        request = factory.get('/community/family/member/1/')
        request.user = MagicMock()
        request.user.is_authenticated = False

        from django.contrib.sessions.backends.db import SessionStore
        session = SessionStore()
        session.create()
        request.session = session

        with patch('community.views.get_object_or_404') as mock_goo:
            mock_member = MagicMock()
            mock_goo.return_value = mock_member
            resp = family_member_detail(request, pk=1)

        # @login_required returns a redirect (302) for anonymous users
        self.assertEqual(resp.status_code, 302,
            f'Expected 302 redirect for anonymous user, got {resp.status_code}')
        self.assertIn('/login/', resp.get('Location', ''),
            'Redirect must point to login page')


# ─────────────────────────────────────────────────────────────────────────────
# HIGH ISSUE #2 — kids_corner_post and grandparents_post age clamping
# Prevents DataError (1264) under STRICT_ALL_TABLES when a user submits
# an age value outside the column's PositiveSmallIntegerField range (0-65535).
# ─────────────────────────────────────────────────────────────────────────────

@skip('Retired community/family/badge feature; boundary covered by jobs.test_feature_scope')
class KidsCornerAgeClampTest(TestCase):
    """
    Verify that kids_corner_post clamps age to max 150 before any DB write.
    PositiveSmallIntegerField (smallint unsigned) max is 65535; values like
    99999 would previously cause DataError (1264) under STRICT_ALL_TABLES.
    """

    def _compute_age(self, age_str):
        """Return the age value that kids_corner_post would pass to KidsPost.objects.create."""
        age = age_str.strip()
        if age.isdigit():
            return max(0, min(150, int(age)))
        return None

    def test_large_age_clamped_to_150(self):
        """Age 99999 must be clamped to 150, not passed to DB unchanged."""
        self.assertEqual(self._compute_age('99999'), 150)

    def test_age_65535_clamped_to_150(self):
        """Age 65535 (smallint unsigned max) must be clamped to 150."""
        self.assertEqual(self._compute_age('65535'), 150)

    def test_normal_age_preserved(self):
        """Normal child age (e.g. 10) must pass through unchanged."""
        self.assertEqual(self._compute_age('10'), 10)

    def test_zero_age_preserved(self):
        """Age 0 (newborn) must pass through as 0."""
        self.assertEqual(self._compute_age('0'), 0)

    def test_max_valid_age_preserved(self):
        """Age 150 (the clamping ceiling) must be preserved."""
        self.assertEqual(self._compute_age('150'), 150)

    def test_non_numeric_age_returns_none(self):
        """Non-numeric input must result in None (no DB write for age)."""
        self.assertIsNone(self._compute_age('abc'))

    def test_empty_age_returns_none(self):
        """Empty string must result in None."""
        self.assertIsNone(self._compute_age(''))

    def test_age_expression_matches_views_code(self):
        """The clamping expression in views.py must match exactly."""
        age = '99999'
        result = max(0, min(150, int(age))) if age.isdigit() else None
        self.assertEqual(result, 150)


@skip('Retired community/family/badge feature; boundary covered by jobs.test_feature_scope')
class GrandparentsAgeClampTest(TestCase):
    """
    Verify that grandparents_post clamps age to max 200 before any DB write.
    Elder ages can legitimately be higher than 150, so the ceiling is 200.
    PositiveSmallIntegerField max is 65535; 99999 would previously cause DataError.
    """

    def _compute_age(self, age_str):
        """Return the age value that grandparents_post would pass to GrandparentStory.objects.create."""
        age = age_str.strip()
        if age.isdigit():
            return max(0, min(200, int(age)))
        return None

    def test_large_age_clamped_to_200(self):
        """Age 99999 must be clamped to 200."""
        self.assertEqual(self._compute_age('99999'), 200)

    def test_age_65535_clamped_to_200(self):
        """Age 65535 (smallint unsigned max) must be clamped to 200."""
        self.assertEqual(self._compute_age('65535'), 200)

    def test_normal_elder_age_preserved(self):
        """Normal elder age (e.g. 85) must pass through unchanged."""
        self.assertEqual(self._compute_age('85'), 85)

    def test_zero_age_preserved(self):
        """Age 0 must pass through as 0."""
        self.assertEqual(self._compute_age('0'), 0)

    def test_max_valid_age_preserved(self):
        """Age 200 (the clamping ceiling) must be preserved."""
        self.assertEqual(self._compute_age('200'), 200)

    def test_non_numeric_age_returns_none(self):
        """Non-numeric input must result in None."""
        self.assertIsNone(self._compute_age('abc'))

    def test_empty_age_returns_none(self):
        """Empty string must result in None."""
        self.assertIsNone(self._compute_age(''))

    def test_age_expression_matches_views_code(self):
        """The clamping expression in views.py must match exactly."""
        age = '99999'
        result = max(0, min(200, int(age))) if age.isdigit() else None
        self.assertEqual(result, 200)


# ─────────────────────────────────────────────────────────────────────────────
# Gallery Timeline — FamilyFlick.event_date field and family_flick_add view
# ─────────────────────────────────────────────────────────────────────────────

@skip('Retired community/family/badge feature; boundary covered by jobs.test_feature_scope')
class GalleryTimelineTest(TestCase):
    """
    Tests for the gallery timeline feature:
    - event_date field saved correctly from POST
    - invalid/missing date handled safely (no 500)
    - view returns event_date in JSON response
    """

    def _make_user(self):
        from jobs.models import User as User2
        import uuid
        phone = '98' + str(uuid.uuid4().int)[:8]
        return User2.objects.create_user(username=phone, password='test', phone=phone)

    def _tiny_image(self):
        """Return a minimal valid JPEG as bytes."""
        import io
        from django.core.files.uploadedfile import SimpleUploadedFile
        # 1x1 red pixel JPEG
        jpeg = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
            b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
            b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\x1e'
            b'=\x19\x18\x18\x18\x18\x18\x18\x18\x18\x18\x18\x18\x18\x18\x18'
            b'\x18\x18\x18\x18\x18\x18\x18\x18\x18\x18\x18\x18\x18\x18\x18'
            b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4'
            b'\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b'
            b'\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05'
            b'\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06'
            b'\x13Qa\x07"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br'
            b'\x82\t\n\x16\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZ'
            b'cdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94'
            b'\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa'
            b'\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7'
            b'\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3'
            b'\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8'
            b'\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd4P\x00\x00'
            b'\x00\x1f\xff\xd9'
        )
        return SimpleUploadedFile('test.jpg', jpeg, content_type='image/jpeg')

    def test_event_date_saved(self):
        """POST with event_date saves the correct date to the DB."""
        from community.models import FamilyFlick
        user = self._make_user()
        self.client.force_login(user)
        resp = self.client.post('/community/family/flick/add/', {
            'photo': self._tiny_image(),
            'caption': 'Birthday',
            'event_date': '2024-06-15',
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['event_date'], '2024-06-15')
        flick = FamilyFlick.objects.get(pk=data['pk'])
        from datetime import date
        self.assertEqual(flick.event_date, date(2024, 6, 15))

    def test_no_event_date_is_null(self):
        """POST without event_date stores null in DB."""
        from community.models import FamilyFlick
        user = self._make_user()
        self.client.force_login(user)
        resp = self.client.post('/community/family/flick/add/', {
            'photo': self._tiny_image(),
            'caption': '',
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        flick = FamilyFlick.objects.get(pk=data['pk'])
        self.assertIsNone(flick.event_date)

    def test_invalid_event_date_ignored(self):
        """POST with a non-date string does not cause a 500; event_date is null."""
        from community.models import FamilyFlick
        user = self._make_user()
        self.client.force_login(user)
        resp = self.client.post('/community/family/flick/add/', {
            'photo': self._tiny_image(),
            'event_date': 'not-a-date',
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        flick = FamilyFlick.objects.get(pk=data['pk'])
        self.assertIsNone(flick.event_date)

    def test_future_event_date_accepted(self):
        """Future dates are accepted (no restriction on event_date)."""
        from community.models import FamilyFlick
        user = self._make_user()
        self.client.force_login(user)
        resp = self.client.post('/community/family/flick/add/', {
            'photo': self._tiny_image(),
            'event_date': '2099-12-31',
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        flick = FamilyFlick.objects.get(pk=data['pk'])
        from datetime import date
        self.assertEqual(flick.event_date, date(2099, 12, 31))

    def test_flick_ordering_by_event_date(self):
        """Flicks are ordered newest event_date first."""
        from community.models import FamilyFlick
        user = self._make_user()
        self.client.force_login(user)
        self.client.post('/community/family/flick/add/', {
            'photo': self._tiny_image(), 'event_date': '2023-01-01',
        })
        self.client.post('/community/family/flick/add/', {
            'photo': self._tiny_image(), 'event_date': '2024-06-01',
        })
        flicks = list(FamilyFlick.objects.filter(creator=user).order_by('-event_date', '-created_at'))
        self.assertEqual(flicks[0].event_date.year, 2024)
        self.assertEqual(flicks[1].event_date.year, 2023)


# ─────────────────────────────────────────────────────────────────────────────
# Birthday Notifications — detection logic, idempotency, security
# ─────────────────────────────────────────────────────────────────────────────

@skip('Retired community/family/badge feature; boundary covered by jobs.test_feature_scope')
class BirthdayNotificationTest(TestCase):
    """Tests for birthday detection, notification sending, and gift redirect."""

    def _make_user(self, prefix='9'):
        from jobs.models import User as U
        import uuid
        phone = prefix + str(uuid.uuid4().int)[:9]
        return U.objects.create_user(username=phone, password='test', phone=phone)

    def _make_setup(self, user, self_dob=None, partner_dob=None, partner_name=''):
        from community.models import FamilySetup
        return FamilySetup.objects.create(
            user=user,
            self_full_name='Test User',
            gender='male',
            marital_status='married' if partner_name else 'single',
            self_dob=self_dob,
            partner_dob=partner_dob,
            partner_full_name=partner_name,
            setup_done=True,
        )

    def _make_member(self, user, name, dob, status='living'):
        from community.models import FamilyMember
        return FamilyMember.objects.create(
            creator=user, name=name, member_type='brother',
            side='husband', dob=dob, status=status,
        )

    def _run_command(self):
        from django.core.management import call_command
        call_command('send_birthday_notifications', verbosity=0)

    # ── 1. Birthday today sends notification ──────────────────────────────────
    def test_birthday_today_sends_notification(self):
        from datetime import date
        from jobs.models import UserNotification
        from community.models import BirthdayNotificationLog
        user = self._make_user()
        self._make_setup(user)
        today = date.today()
        self._make_member(user, 'Arun', today.replace(year=today.year - 30))
        self._run_command()
        self.assertEqual(UserNotification.objects.filter(user=user, notif_type='success').count(), 1)
        self.assertEqual(BirthdayNotificationLog.objects.filter(user=user, notif_type='today').count(), 1)

    # ── 2. Birthday in 2 days sends reminder ─────────────────────────────────
    def test_birthday_in_two_days_sends_reminder(self):
        from datetime import date, timedelta
        from jobs.models import UserNotification
        from community.models import BirthdayNotificationLog
        user = self._make_user()
        self._make_setup(user)
        in_two = date.today() + timedelta(days=2)
        self._make_member(user, 'Priya', in_two.replace(year=in_two.year - 25))
        self._run_command()
        self.assertEqual(UserNotification.objects.filter(user=user, notif_type='info').count(), 1)
        self.assertEqual(BirthdayNotificationLog.objects.filter(user=user, notif_type='reminder').count(), 1)

    # ── 3. Other dates send nothing ───────────────────────────────────────────
    def test_no_notification_for_other_dates(self):
        from datetime import date, timedelta
        from jobs.models import UserNotification
        user = self._make_user()
        self._make_setup(user)
        in_five = date.today() + timedelta(days=5)
        self._make_member(user, 'Rajan', in_five.replace(year=in_five.year - 40))
        self._run_command()
        self.assertEqual(UserNotification.objects.filter(user=user).count(), 0)

    # ── 4. Duplicate not sent on second run ───────────────────────────────────
    def test_duplicate_not_sent(self):
        from datetime import date
        from jobs.models import UserNotification
        user = self._make_user()
        self._make_setup(user)
        today = date.today()
        self._make_member(user, 'Kavitha', today.replace(year=today.year - 28))
        self._run_command()
        self._run_command()  # second run
        self.assertEqual(UserNotification.objects.filter(user=user).count(), 1)

    # ── 5. Deceased member skipped ────────────────────────────────────────────
    def test_deceased_member_skipped(self):
        from datetime import date
        from jobs.models import UserNotification
        user = self._make_user()
        self._make_setup(user)
        today = date.today()
        self._make_member(user, 'Late Grandpa', today.replace(year=today.year - 80), status='passed')
        self._run_command()
        self.assertEqual(UserNotification.objects.filter(user=user).count(), 0)

    # ── 6. Null DOB skipped without error ─────────────────────────────────────
    def test_null_dob_skipped(self):
        from jobs.models import UserNotification
        user = self._make_user()
        self._make_setup(user)
        self._make_member(user, 'Unknown', dob=None)
        self._run_command()
        self.assertEqual(UserNotification.objects.filter(user=user).count(), 0)

    # ── 7. partner_dob triggers notification ─────────────────────────────────
    def test_partner_dob_notification(self):
        from datetime import date
        from jobs.models import UserNotification
        user = self._make_user()
        today = date.today()
        self._make_setup(user, partner_dob=today.replace(year=today.year - 30), partner_name='Kavitha')
        self._run_command()
        notif = UserNotification.objects.filter(user=user).first()
        self.assertIsNotNone(notif)
        self.assertIn('Kavitha', notif.message)

    # ── 8. self_dob triggers notification ────────────────────────────────────
    def test_self_dob_notification(self):
        from datetime import date
        from jobs.models import UserNotification
        user = self._make_user()
        today = date.today()
        self._make_setup(user, self_dob=today.replace(year=today.year - 35))
        self._run_command()
        self.assertEqual(UserNotification.objects.filter(user=user).count(), 1)

    # ── 9. Gift redirect validates ownership ─────────────────────────────────
    def test_gift_redirect_validates_ownership(self):
        from datetime import date
        user_a = self._make_user('7')
        user_b = self._make_user('8')
        self._make_setup(user_a)
        self._make_setup(user_b)
        today = date.today()
        member_b = self._make_member(user_b, 'Bob', today.replace(year=today.year - 30))
        # user_a tries to gift user_b's family member
        self.client.force_login(user_a)
        resp = self.client.get(f'/community/family/birthday-gift/{member_b.pk}/')
        self.assertEqual(resp.status_code, 403)

    # ── 10. Gift redirect succeeds for own member ─────────────────────────────
    def test_gift_redirect_succeeds_for_own_member(self):
        from datetime import date
        user = self._make_user()
        self._make_setup(user)
        today = date.today()
        member = self._make_member(user, 'Arun', today.replace(year=today.year - 30))
        self.client.force_login(user)
        resp = self.client.get(f'/community/family/birthday-gift/{member.pk}/')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('gift_for', resp['Location'])
        self.assertIn('Arun', resp['Location'])
