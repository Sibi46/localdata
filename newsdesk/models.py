import uuid
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, MinLengthValidator
from django.db import models
from django.utils import timezone

from .uploads import private_storage, upload_path, validate_photo, validate_video
from .identity_uploads import identity_storage, validate_identity, validate_profile_photo


def contributor_reference():
    return 'NDC-' + secrets.token_hex(8).upper()


def submission_reference():
    return 'ND-' + secrets.token_hex(8).upper()


class NewsAgent(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='news_agent')
    pincode = models.ForeignKey('jobs.PinCode', on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.user} / {self.pincode.code}'


class NewsItem(models.Model):
    class Category(models.TextChoices):
        NEWS = 'news', 'News'
        FESTIVALS = 'festivals', 'Festivals'
        ACHIEVEMENTS = 'achievements', 'Achievements'
        SPORTS = 'sports', 'Sports'
        COMMUNITY = 'community', 'Community'
        BIRTHDAY = 'birthday', 'Birthday Wishes'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'

    pincode = models.ForeignKey('jobs.PinCode', on_delete=models.PROTECT, related_name='news_items')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='news_items')
    title = models.CharField(max_length=180)
    body = models.TextField(max_length=20000)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.NEWS)
    kind = models.CharField(max_length=10, choices=[('news', 'News'), ('event', 'Event')], default='news')
    event_start = models.DateTimeField(null=True, blank=True)
    event_end = models.DateTimeField(null=True, blank=True)
    venue = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    photo = models.ImageField(upload_to=upload_path, storage=private_storage, blank=True, validators=[validate_photo])
    video = models.FileField(upload_to=upload_path, storage=private_storage, blank=True, validators=[validate_video])
    published_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at', '-pk']
        indexes = [models.Index(fields=['pincode', 'status', '-published_at'])]
        permissions = [('manage_newsdesk', 'Manage all News Desk content and assignments')]
        constraints = [models.CheckConstraint(condition=~models.Q(status='published') | models.Q(published_at__isnull=False), name='news_published_has_date')]

    def clean(self):
        if self.kind == 'event' and (not self.event_start or not self.venue.strip()):
            raise ValidationError('Events require a start time and venue.')
        if self.event_end and (not self.event_start or self.event_end < self.event_start):
            raise ValidationError({'event_end': 'End time must be after the start time.'})

    def save(self, *args, **kwargs):
        # Republishing never resets the seven-day window. All application writes use
        # the locked service below; this also protects ordinary Django admin saves.
        original = type(self).objects.filter(pk=self.pk).values_list('published_at', flat=True).first() if self.pk else None
        if original:
            self.published_at = original
        elif self.status == self.Status.PUBLISHED:
            self.published_at = timezone.now()
        if kwargs.get('update_fields') is not None:
            kwargs['update_fields'] = set(kwargs['update_fields']) | {'published_at'}
        super().save(*args, **kwargs)

    @property
    def comment_deadline(self):
        return self.published_at + timedelta(days=7) if self.published_at else None

    @property
    def comments_open(self):
        now = timezone.now()
        return bool(self.status == self.Status.PUBLISHED and self.published_at and self.published_at <= now < self.comment_deadline)

    def __str__(self):
        return self.title


class Rating(models.Model):
    item = models.ForeignKey(NewsItem, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    stars = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['item', 'user'], name='news_one_rating_per_user'),
            models.CheckConstraint(condition=models.Q(stars__gte=1, stars__lte=5), name='news_rating_one_to_five'),
        ]


class Comment(models.Model):
    item = models.ForeignKey(NewsItem, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.CharField(max_length=160, validators=[MinLengthValidator(1)])
    is_hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    moderated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    moderated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at', 'pk']


class CommentReport(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='reports')
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reason = models.CharField(max_length=200)
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['comment', 'reporter'], name='news_one_report_per_user')]


class BirthdayCard(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    recipient = models.CharField(max_length=60)
    message = models.CharField(max_length=160)
    theme = models.CharField(max_length=12, choices=[('sunshine', 'Sunshine'), ('rose', 'Rose'), ('sky', 'Sky')], default='sunshine')
    is_public = models.BooleanField(default=False, help_text='Anyone with the link can see and download this card.')
    created_at = models.DateTimeField(auto_now_add=True)


class NewsContributor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=24, unique=True, default=contributor_reference, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='news_contributors')
    phone = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=120)
    pincode = models.ForeignKey('jobs.PinCode', on_delete=models.PROTECT)
    address = models.TextField(max_length=1000)
    aadhaar = models.FileField(upload_to=upload_path, storage=identity_storage, validators=[validate_identity])
    profile_photo = models.FileField(upload_to=upload_path, storage=identity_storage, validators=[validate_profile_photo])
    phone_verified_at = models.DateTimeField()
    document_checked_at = models.DateTimeField(null=True, blank=True)
    document_checked_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)


class NewsSubmission(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Waiting for editor review'
        REJECTED = 'rejected', 'Not approved'
        PUBLISHED = 'published', 'Published'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=24, unique=True, default=submission_reference, editable=False)
    contributor = models.ForeignKey(NewsContributor, on_delete=models.PROTECT, related_name='submissions')
    topic = models.CharField(max_length=180)
    body = models.TextField(max_length=12000)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    terms_version = models.CharField(max_length=20, default='news-sharing-v1', editable=False)
    terms_accepted_at = models.DateTimeField(editable=False)
    accuracy_accepted_at = models.DateTimeField(editable=False)
    submission_token = models.UUIDField(unique=True, editable=False)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_news_submissions')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(max_length=2000, blank=True)
    published_story = models.OneToOneField(NewsItem, null=True, blank=True, on_delete=models.PROTECT, related_name='reader_submission')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', '-created_at'])]
