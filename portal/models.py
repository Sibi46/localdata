from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify

User = get_user_model()
import secrets, re
from .network_activities import ACTIVITY_CHOICES, activity_emoji, network_name


class NetworkPost(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='network_posts')
    pincode = models.CharField(max_length=6)
    text = models.CharField(max_length=500)
    activity = models.CharField(max_length=20, choices=ACTIVITY_CHOICES, default='social')
    is_open = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at', '-pk']
        indexes = [models.Index(fields=['pincode', 'is_open', '-created_at'], name='network_local_open_idx')]

    @property
    def emoji(self):
        return activity_emoji(self.activity)

    @property
    def author_name(self):
        return network_name(self.author)


class NetworkConnection(models.Model):
    post = models.ForeignKey(NetworkPost, on_delete=models.CASCADE, related_name='connections')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='network_connections')
    conversation = models.ForeignKey('jobs.Conversation', null=True, on_delete=models.SET_NULL,
                                     related_name='network_connections')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['post', 'user'], name='unique_network_post_connection')]

    @property
    def member_name(self):
        return network_name(self.user)


def _initials(name):
    words = re.sub(r'[^a-zA-Z\s]', '', name).strip().split()
    return ''.join(w[0].upper() for w in words if w)[:4]


def generate_page_id(name):
    code = _initials(name) or 'COM'
    prefix = f'OPC-{code}-'
    count = Community.objects.filter(page_id__startswith=prefix).count()
    return f'{prefix}{str(count + 1).zfill(3)}'


class Category(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=10, default='🏘️')
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class Community(models.Model):
    JOIN_MODES = [('open', 'Open Join'), ('approval', 'Admin Approval'), ('private', 'Private — Invite Only')]

    name        = models.CharField(max_length=200)
    page_id     = models.CharField(max_length=25, unique=True, editable=False)
    slug        = models.SlugField(unique=True, max_length=220)
    logo        = models.ImageField(upload_to='portal/logos/', blank=True)
    cover       = models.ImageField(upload_to='portal/covers/', blank=True)
    purpose     = models.CharField(max_length=300)
    description = models.TextField()
    category    = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    location    = models.CharField(max_length=200)
    pincode     = models.CharField(max_length=10)
    email       = models.EmailField(blank=True)
    phone       = models.CharField(max_length=20, blank=True)
    created_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_communities')
    join_mode   = models.CharField(max_length=10, choices=JOIN_MODES, default='open')
    is_verified = models.BooleanField(default=False)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.page_id:
            self.page_id = generate_page_id(self.name)
        if not self.slug:
            base = slugify(self.name)
            slug = base
            n = 1
            while Community.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def member_count(self):
        return self.memberships.filter(status='approved').count()

    def is_admin(self, user):
        if not user.is_authenticated:
            return False
        if getattr(user, 'admin_role', '') == 'super_admin':
            return True
        if self.created_by == user:
            return True
        return self.leaders.filter(user=user, status='accepted').exists()

    def can_manage_members(self, user):
        """Only creator or president can approve/remove/assign members."""
        if not user.is_authenticated:
            return False
        if self.created_by == user:
            return True
        return self.leaders.filter(user=user, role='president', status='accepted').exists()

    def president(self):
        return self.leaders.filter(role='president', status='accepted').first()

    def vice_president(self):
        return self.leaders.filter(role='vice_president', status='accepted').first()

    def __str__(self):
        return f'{self.name} ({self.page_id})'


class CommunityLeader(models.Model):
    ROLES = [
        ('president', 'President'),
        ('vice_president', 'Vice President'),
        ('secretary', 'Secretary'),
        ('treasurer', 'Treasurer'),
        ('event_coordinator', 'Event Coordinator'),
        ('volunteer_coordinator', 'Volunteer Coordinator'),
        ('media_coordinator', 'Media Coordinator'),
        ('member', 'Member'),
    ]
    STATUSES = [('pending', 'Pending'), ('accepted', 'Accepted'), ('declined', 'Declined')]

    community    = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='leaders')
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leadership_roles')
    role         = models.CharField(max_length=30, choices=ROLES)
    custom_role  = models.CharField(max_length=100, blank=True)
    status       = models.CharField(max_length=10, choices=STATUSES, default='pending')
    nominated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='nominations_made')
    token        = models.CharField(max_length=80, blank=True)
    accepted_at  = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def generate_token(self):
        self.token = secrets.token_urlsafe(40)
        self.save(update_fields=['token'])

    def get_role_label(self):
        if self.role == 'other' and self.custom_role:
            return self.custom_role
        return self.get_role_display()

    def __str__(self):
        return f'{self.user.get_full_name()} — {self.get_role_display()} @ {self.community.name}'


class CommunityMember(models.Model):
    STATUSES = [('pending','Pending'),('approved','Approved'),('rejected','Rejected'),('removed','Removed')]

    community   = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='memberships')
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    status      = models.CharField(max_length=10, choices=STATUSES, default='pending')
    joined_at   = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('community', 'user')

    def __str__(self):
        return f'{self.user.get_full_name()} → {self.community.name} ({self.status})'


class Cause(models.Model):
    community   = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='causes')
    created_by  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_causes')
    name        = models.CharField(max_length=200)
    description = models.TextField()
    objective   = models.TextField()
    image       = models.ImageField(upload_to='portal/causes/', blank=True)
    start_date  = models.DateField()
    end_date    = models.DateField(null=True, blank=True)
    location    = models.CharField(max_length=200, blank=True)
    target_goal = models.CharField(max_length=200, blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def support_count(self):
        return self.supporters.count()

    def __str__(self):
        return self.name


class CauseSupport(models.Model):
    cause      = models.ForeignKey(Cause, on_delete=models.CASCADE, related_name='supporters')
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cause', 'user')


class Event(models.Model):
    STATUS_CHOICES = [('upcoming','Upcoming'),('ongoing','Ongoing'),('completed','Completed'),('cancelled','Cancelled')]

    community        = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='events', null=True, blank=True)
    cause            = models.ForeignKey(Cause, on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    created_by       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_events')
    name             = models.CharField(max_length=200)
    description      = models.TextField()
    date             = models.DateField()
    time             = models.TimeField()
    end_date         = models.DateField(null=True, blank=True)
    end_time         = models.TimeField(null=True, blank=True)
    location         = models.CharField(max_length=300)
    pincode          = models.CharField(max_length=10, blank=True)
    map_link         = models.URLField(blank=True)
    is_online         = models.BooleanField(default=False)
    online_link       = models.URLField(blank=True)
    meeting_password  = models.CharField(max_length=100, blank=True)
    image            = models.ImageField(upload_to='portal/events/', blank=True)
    max_participants = models.PositiveIntegerField(null=True, blank=True)
    is_paid          = models.BooleanField(default=False)
    ticket_price     = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    tags             = models.CharField(max_length=300, blank=True)
    rsvp_questions        = models.JSONField(default=list, blank=True)
    require_profile_photo = models.BooleanField(default=False)
    collect_contact       = models.BooleanField(default=False)
    upi_id                = models.CharField(max_length=100, blank=True)
    payment_qr            = models.ImageField(upload_to='portal/payment_qr/', blank=True)
    contact_person   = models.CharField(max_length=200, blank=True)
    contact_phone    = models.CharField(max_length=20, blank=True)
    status           = models.CharField(max_length=12, choices=STATUS_CHOICES, default='upcoming')
    is_active        = models.BooleanField(default=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    def participant_count(self):
        return self.participants.filter(status='approved').count()

    def waitlist_count(self):
        return self.participants.filter(status='waitlist').count()

    def is_full(self):
        if not self.max_participants:
            return False
        return self.participant_count() >= self.max_participants

    def avg_rating(self):
        r = self.ratings.aggregate(a=models.Avg('rating'))['a']
        return round(r, 1) if r else None

    def __str__(self):
        return self.name


class EventParticipant(models.Model):
    ROLES    = [('attendee','Attendee'),('volunteer','Volunteer'),('guest','Guest'),('sponsor','Sponsor'),('partner','Partner')]
    STATUSES = [('pending','Pending'),('approved','Approved'),('rejected','Rejected'),('waitlist','Waitlist'),('cancelled','Cancelled')]

    PAYMENT_STATUSES = [('','—'),('pending','Pending'),('approved','Approved'),('rejected','Rejected')]

    event              = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='participants')
    user               = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_participations')
    role               = models.CharField(max_length=10, choices=ROLES, default='attendee')
    status             = models.CharField(max_length=10, choices=STATUSES, default='pending')
    rsvp_answers       = models.JSONField(default=dict, blank=True)
    rsvp_email         = models.EmailField(blank=True)
    rsvp_phone         = models.CharField(max_length=20, blank=True)
    payment_screenshot = models.ImageField(upload_to='portal/payment_screenshots/', blank=True)
    payment_status     = models.CharField(max_length=10, choices=PAYMENT_STATUSES, blank=True)
    attended           = models.BooleanField(default=False)
    registered_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'user')


class EventComment(models.Model):
    event      = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='comments')
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_comments')
    text       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class EventAnnouncement(models.Model):
    event      = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='announcements')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    title      = models.CharField(max_length=200)
    body       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class EventPhoto(models.Model):
    event       = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='photos')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    image       = models.ImageField(upload_to='portal/event_photos/')
    caption     = models.CharField(max_length=200, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class EventRating(models.Model):
    event      = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='ratings')
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_ratings')
    rating     = models.PositiveSmallIntegerField()  # 1-5
    review     = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'user')


class AttendeeRating(models.Model):
    """User rates another user who attended the same event."""
    event      = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendee_ratings')
    rater      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_attendee_ratings')
    ratee      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_attendee_ratings')
    rating     = models.PositiveSmallIntegerField()  # 1-5
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'rater', 'ratee')

    def __str__(self):
        return f'{self.rater} rated {self.ratee} @ {self.event} — {self.rating}★'


class VolunteerRequest(models.Model):
    STATUSES = [('pending','Pending'),('approved','Approved'),('rejected','Rejected')]

    community          = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='volunteer_requests')
    user               = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    name               = models.CharField(max_length=200)
    email              = models.EmailField()
    mobile             = models.CharField(max_length=20)
    event              = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True)
    volunteer_interest = models.CharField(max_length=300)
    message            = models.TextField(blank=True)
    availability       = models.CharField(max_length=200)
    status             = models.CharField(max_length=10, choices=STATUSES, default='pending')
    created_at         = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} → {self.community.name}'


class Activity(models.Model):
    community         = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='activities')
    cause             = models.ForeignKey(Cause, on_delete=models.SET_NULL, null=True, blank=True)
    created_by        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_activities')
    name              = models.CharField(max_length=200)
    description       = models.TextField()
    date              = models.DateField()
    location          = models.CharField(max_length=200, blank=True)
    participant_count = models.PositiveIntegerField(default=0)
    volunteer_count   = models.PositiveIntegerField(default=0)
    result_impact     = models.TextField(blank=True)
    is_active         = models.BooleanField(default=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Activities'

    def __str__(self):
        return self.name


class ActivityPhoto(models.Model):
    activity    = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='photos')
    image       = models.ImageField(upload_to='portal/activity_photos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)


class Post(models.Model):
    POST_TYPES = [
        ('update','Update'),('announcement','Announcement'),('achievement','Achievement'),
        ('event','Event'),('cause','Cause'),('activity','Activity'),
    ]
    community  = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='posts')
    author     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='portal_posts')
    post_type  = models.CharField(max_length=15, choices=POST_TYPES, default='update')
    content    = models.TextField()
    image      = models.ImageField(upload_to='portal/posts/', blank=True)
    event_date = models.DateField(null=True, blank=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def like_count(self):
        return self.likes.count()


class PostLike(models.Model):
    post       = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')


class PostComment(models.Model):
    post       = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    content    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class ShortVideo(models.Model):
    VIDEO_CATS = [
        ('story','Community Story'),('event','Event'),('activity','Activity'),
        ('cause','Cause'),('announcement','Announcement'),('achievement','Achievement'),
        ('volunteer','Volunteer Story'),('testimonial','Testimonial'),
    ]
    community        = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='videos')
    uploader         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='portal_videos')
    title            = models.CharField(max_length=200)
    video            = models.FileField(upload_to='portal/videos/')
    thumbnail        = models.ImageField(upload_to='portal/video_thumbs/', blank=True)
    category         = models.CharField(max_length=15, choices=VIDEO_CATS, default='story')
    pincode          = models.CharField(max_length=10, blank=True)
    location         = models.CharField(max_length=200, blank=True)
    related_event    = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True)
    related_cause    = models.ForeignKey(Cause, on_delete=models.SET_NULL, null=True, blank=True)
    related_activity = models.ForeignKey(Activity, on_delete=models.SET_NULL, null=True, blank=True)
    is_active        = models.BooleanField(default=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Flick(models.Model):
    MEDIA_TYPES = [('video', 'Video'), ('image', 'Image')]

    community       = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='flicks')
    posted_by       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='portal_flicks')
    caption         = models.CharField(max_length=300, blank=True)
    media           = models.FileField(upload_to='portal/flicks/')
    media_type      = models.CharField(max_length=5, choices=MEDIA_TYPES, default='video')
    is_active       = models.BooleanField(default=True)
    approved_by     = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_flicks')
    created_at      = models.DateTimeField(auto_now_add=True)
    source_video_id = models.IntegerField(null=True, blank=True, unique=True)

    class Meta:
        ordering = ['-created_at']

    def like_count(self):
        return self.flick_likes.count()

    def __str__(self):
        return f'{self.posted_by.get_full_name()} — {self.community.name}'


class FlickLike(models.Model):
    flick      = models.ForeignKey(Flick, on_delete=models.CASCADE, related_name='flick_likes')
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('flick', 'user')


class FlickComment(models.Model):
    flick      = models.ForeignKey(Flick, on_delete=models.CASCADE, related_name='flick_comments')
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    text       = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def comment_count(self):
        return self.flick.flick_comments.count()


class PortalNotification(models.Model):
    NOTIF_TYPES = [
        ('join_request','Join Request'),('join_approved','Membership Approved'),
        ('join_rejected','Membership Rejected'),('leader_nomination','Leadership Nomination'),
        ('new_event','New Event'),('event_approved','Event Registration Approved'),
        ('volunteer_approved','Volunteer Approved'),('new_cause','New Cause'),
        ('announcement','Announcement'),('activity_update','Activity Update'),
    ]
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='portal_notifications')
    notif_type = models.CharField(max_length=30, choices=NOTIF_TYPES)
    message    = models.TextField()
    link       = models.CharField(max_length=300, blank=True)
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


# ── Community Points & Recognition ──────────────────────────────────────────

class PointConfig(models.Model):
    ACTION_CHOICES = [
        ('attend_event','Attend Event'),
        ('volunteer_event','Volunteer at Event'),
        ('organise_event','Organise Event'),
        ('complete_activity','Complete Activity'),
        ('volunteer_activity','Volunteer Activity'),
        ('support_cause','Support Cause'),
        ('upload_contribution','Upload Contribution'),
        ('financial_contribution','Financial Contribution'),
        ('other','Other'),
    ]
    action     = models.CharField(max_length=50, unique=True, choices=ACTION_CHOICES)
    label      = models.CharField(max_length=100)
    points     = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.label} → {self.points} pts'


class Participation(models.Model):
    ROLES    = [('organiser','Organiser'),('volunteer','Volunteer'),
                ('contributor','Contributor'),('guest','Guest'),('sponsor','Sponsor'),
                ('performer','Performer'),('leadership','Leadership'),('bonus','Bonus Points')]
    STATUSES = [('pending','Pending'),('confirmed','Confirmed'),('rejected','Rejected')]

    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='participations')
    community     = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='participations')
    event         = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True, related_name='participations')
    activity      = models.ForeignKey(Activity, on_delete=models.SET_NULL, null=True, blank=True, related_name='participations')
    cause         = models.ForeignKey(Cause, on_delete=models.SET_NULL, null=True, blank=True, related_name='participations')
    role          = models.CharField(max_length=15, choices=ROLES, default='attendee')
    status        = models.CharField(max_length=10, choices=STATUSES, default='pending')
    points_awarded = models.PositiveIntegerField(default=0)
    verified_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_participations')
    verified_at   = models.DateTimeField(null=True, blank=True)
    notes         = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'event', 'activity', 'cause', 'role')

    def __str__(self):
        return f'{self.user.get_full_name()} — {self.role} @ {self.community.name}'


class Contribution(models.Model):
    TYPES = [
        ('financial','Financial'),('food','Food'),('equipment','Equipment'),
        ('materials','Materials'),('books','Books'),('clothing','Clothing'),
        ('transport','Transport'),('professional','Professional Service'),
        ('sponsorship','Sponsorship'),('venue','Venue Support'),('other','Other'),
    ]
    STATUSES = [('pending','Pending'),('approved','Approved'),('rejected','Rejected')]

    user              = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contributions')
    community         = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='contributions')
    event             = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True, related_name='contributions')
    activity          = models.ForeignKey(Activity, on_delete=models.SET_NULL, null=True, blank=True, related_name='contributions')
    cause             = models.ForeignKey(Cause, on_delete=models.SET_NULL, null=True, blank=True, related_name='contributions')
    contribution_type = models.CharField(max_length=20, choices=TYPES)
    amount            = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description       = models.TextField()
    estimated_value   = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status            = models.CharField(max_length=10, choices=STATUSES, default='pending')
    points_awarded    = models.PositiveIntegerField(default=0)
    verified_by       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_contributions')
    verified_at       = models.DateTimeField(null=True, blank=True)
    transaction_ref   = models.CharField(max_length=200, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.get_full_name()} — {self.contribution_type} @ {self.community.name}'


class MemberPoints(models.Model):
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='member_points')
    community    = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='member_points')
    total_points = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'community')

    def __str__(self):
        return f'{self.user.get_full_name()} — {self.total_points} pts @ {self.community.name}'


class Badge(models.Model):
    icon_image = models.ImageField(upload_to="badges/icons/", blank=True)
    image = models.ImageField(upload_to="badges/images/", blank=True)
    CRITERIA_CHOICES = [
        ('points','Points Threshold'),('events','Events Attended'),
        ('organised','Events Organised'),('volunteer','Volunteer Activities'),
        ('causes','Causes Supported'),('manual','Manual Award'),
    ]
    community      = models.ForeignKey(Community, on_delete=models.SET_NULL, null=True, blank=True, related_name='badges')
    name           = models.CharField(max_length=100)
    description    = models.TextField()
    icon           = models.CharField(max_length=10, default='🏅')
    criteria_type  = models.CharField(max_length=30, choices=CRITERIA_CHOICES, default='manual')
    criteria_value = models.PositiveIntegerField(default=0)
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.icon} {self.name}'


class MemberBadge(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='badges')
    community  = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='awarded_badges')
    badge      = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='awards')
    awarded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='badges_awarded')
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'community', 'badge')

    def __str__(self):
        return f'{self.user.get_full_name()} — {self.badge.name}'


class Recognition(models.Model):
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recognitions')
    community   = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='recognitions')
    award_name  = models.CharField(max_length=200)
    year        = models.PositiveSmallIntegerField()
    description = models.TextField(blank=True)
    awarded_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='recognitions_given')
    awarded_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.award_name} — {self.user.get_full_name()} ({self.year})'


class PointAuditLog(models.Model):
    community     = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='audit_logs')
    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='point_audit_logs')
    action        = models.CharField(max_length=100)
    points_before = models.IntegerField(default=0)
    points_after  = models.IntegerField(default=0)
    note          = models.TextField(blank=True)
    done_by       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_actions')
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.get_full_name()} {self.action} ({self.points_after} pts)'


# ── Helper functions ─────────────────────────────────────────────────────────

def award_points(user, community, points, action_note, done_by=None):
    """Award points, update MemberPoints, log audit, then check badges."""
    mp, _ = MemberPoints.objects.get_or_create(user=user, community=community)
    before = mp.total_points
    mp.total_points += points
    mp.save()
    PointAuditLog.objects.create(
        community=community, user=user, action=action_note[:100],
        points_before=before, points_after=mp.total_points, done_by=done_by,
    )
    check_auto_badges(user, community)


def check_auto_badges(user, community):
    """Auto-award badges based on criteria."""
    mp = MemberPoints.objects.filter(user=user, community=community).first()
    total = mp.total_points if mp else 0
    events_attended = Participation.objects.filter(
        user=user, community=community, role='attendee', status='confirmed').count()
    organised = Participation.objects.filter(
        user=user, community=community, role='organiser', status='confirmed').count()
    volunteered = Participation.objects.filter(
        user=user, community=community, role='volunteer', status='confirmed').count()
    causes = Participation.objects.filter(
        user=user, community=community, cause__isnull=False, status='confirmed'
    ).values('cause').distinct().count()

    for badge in Badge.objects.filter(community=community).exclude(criteria_type='manual'):
        if MemberBadge.objects.filter(user=user, community=community, badge=badge).exists():
            continue
        earned = False
        if badge.criteria_type == 'points' and total >= badge.criteria_value:
            earned = True
        elif badge.criteria_type == 'events' and events_attended >= badge.criteria_value:
            earned = True
        elif badge.criteria_type == 'organised' and organised >= badge.criteria_value:
            earned = True
        elif badge.criteria_type == 'volunteer' and volunteered >= badge.criteria_value:
            earned = True
        elif badge.criteria_type == 'causes' and causes >= badge.criteria_value:
            earned = True
        if earned:
            MemberBadge.objects.create(user=user, community=community, badge=badge, awarded_by=None)


def get_point_value(action_key, default=0):
    """Get point value from PointConfig, creating defaults if missing."""
    DEFAULTS = {
        'attend_event': 10,
        'volunteer_event': 20,
        'organise_event': 50,
        'complete_activity': 30,
        'volunteer_activity': 20,
        'support_cause': 10,
        'upload_contribution': 5,
        'financial_contribution': 10,
    }
    obj, _ = PointConfig.objects.get_or_create(
        action=action_key,
        defaults={'label': action_key.replace('_', ' ').title(), 'points': DEFAULTS.get(action_key, default)},
    )
    return obj.points
