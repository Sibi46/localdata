from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from jobs.models import UserNotification
from .models import NewsAgent, NewsContributor, NewsItem, NewsSubmission
from .permissions import active_pincodes, agent_for, is_admin


def editor_submissions(user):
    if is_admin(user):
        return NewsSubmission.objects.all()
    agent = agent_for(user)
    if not agent:
        raise PermissionDenied('An active News Editor assignment is required.')
    return NewsSubmission.objects.filter(contributor__pincode_id=agent.pincode_id)


def notify_editors(submission):
    user_model = get_user_model()
    ids = set(NewsAgent.objects.filter(is_active=True, pincode_id=submission.contributor.pincode_id,
                                     user__is_active=True).values_list('user_id', flat=True))
    for user in user_model.objects.filter(is_active=True).filter(Q(is_superuser=True) | Q(admin_role='super_admin') | Q(is_staff=True)):
        if is_admin(user):
            ids.add(user.pk)
    for user_id in ids:
        UserNotification.objects.create(user_id=user_id, title='News awaiting editorial review',
            message=f'Submission {submission.reference} is ready to review.',
            link=reverse('newsdesk:review_submission', args=[submission.pk]))


def submit_news(phone, verified_at, data, user):
    saved_files = []
    try:
        with transaction.atomic():
            existing = NewsSubmission.objects.filter(submission_token=data['token'], contributor__phone=phone).first()
            if existing:
                return existing
            contributor = NewsContributor.objects.select_for_update().filter(phone=phone).first()
            if not contributor:
                contributor = NewsContributor(phone=phone, name=data['name'], pincode=data['pincode'],
                    address=data['address'], aadhaar=data['aadhaar'], profile_photo=data['profile_photo'],
                    phone_verified_at=verified_at)
                if user.is_authenticated and phone in {user.phone, user.business_phone}:
                    contributor.user = user
                # Save files explicitly so rollback can remove private uploads as well.
                for field in ('aadhaar', 'profile_photo'):
                    file = getattr(contributor, field)
                    file.save(file.name, file.file, save=False)
                    saved_files.append((file.storage, file.name))
                contributor.save()
            if not active_pincodes().filter(pk=contributor.pincode_id).exists():
                raise ValidationError('Your PIN code is unavailable. Contact News Desk before submitting.')
            now = timezone.now()
            submission = NewsSubmission.objects.create(contributor=contributor, topic=data['topic'], body=data['body'],
                submission_token=data['token'], terms_accepted_at=now, accuracy_accepted_at=now)
            notify_editors(submission)
            return submission
    except Exception:
        for storage, name in saved_files:
            storage.delete(name)
        raise


@transaction.atomic
def review_submission(user, pk, data):
    submission = editor_submissions(user).select_for_update().select_related('contributor__pincode').get(pk=pk)
    if submission.status != NewsSubmission.Status.PENDING:
        return submission
    if not active_pincodes().filter(pk=submission.contributor.pincode_id).exists():
        raise ValidationError('This PIN code is no longer active.')
    now = timezone.now()
    if data['decision'] == 'publish':
        if not data.get('identity_checked'):
            raise ValidationError('Review the identity document before publishing.')
        story = NewsItem(author=user, pincode=submission.contributor.pincode, title=data['topic'],
            body=data['body'], category=data['category'], status=NewsItem.Status.PUBLISHED)
        # The model establishes published_at in save; set it before full validation too.
        story.published_at = now
        story.full_clean()
        story.save()
        submission.published_story = story
        submission.status = NewsSubmission.Status.PUBLISHED
        NewsContributor.objects.filter(pk=submission.contributor_id).update(document_checked_at=now, document_checked_by=user)
    else:
        if not data.get('note', '').strip():
            raise ValidationError('Provide a reason before rejecting a submission.')
        submission.status = NewsSubmission.Status.REJECTED
    submission.reviewed_by = user
    submission.reviewed_at = now
    submission.review_note = data.get('note', '').strip()
    submission.save(update_fields=['published_story', 'status', 'reviewed_by', 'reviewed_at', 'review_note'])
    if submission.contributor.user_id:
        UserNotification.objects.create(user_id=submission.contributor.user_id,
            title='Your news submission was reviewed', message=f'{submission.reference}: {submission.get_status_display()}.',
            link=reverse('newsdesk:detail', args=[submission.published_story_id]) if submission.published_story_id else reverse('newsdesk:share'))
    return submission
