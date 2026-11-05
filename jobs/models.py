from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class RideTrip(models.Model):
    VEHICLES = [('bike', 'Bike'), ('car', 'Car')]
    STATUSES = [('open', 'Open'), ('full', 'Full'), ('completed', 'Completed'), ('cancelled', 'Cancelled')]
    owner = models.ForeignKey('User', on_delete=models.CASCADE, related_name='ride_trips')
    origin = models.CharField(max_length=80)
    destination = models.CharField(max_length=80)
    departure_at = models.DateTimeField(db_index=True)
    vehicle = models.CharField(max_length=4, choices=VEHICLES)
    seats = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(7)])
    meeting_area = models.CharField(max_length=120)
    notes = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=10, choices=STATUSES, default='open', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['departure_at', 'pk']
        indexes = [models.Index(fields=['status', 'departure_at'], name='ride_status_departure_idx')]
        constraints = [
            models.CheckConstraint(condition=models.Q(seats__gte=1, seats__lte=7), name='ride_seats_range'),
            models.CheckConstraint(condition=~models.Q(vehicle='bike') | models.Q(seats=1), name='ride_bike_one_passenger'),
            models.CheckConstraint(condition=models.Q(vehicle__in=['bike', 'car']), name='ride_vehicle_valid'),
            models.CheckConstraint(condition=models.Q(status__in=['open', 'full', 'completed', 'cancelled']), name='ride_status_valid'),
        ]

    @property
    def available_seats(self):
        count = self.accepted_count if hasattr(self, 'accepted_count') else self.requests.filter(status='accepted').count()
        return max(0, self.seats - count)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('ride_detail', args=[self.pk])

    def __str__(self):
        return f'{self.origin} to {self.destination}'


class RideRequest(models.Model):
    STATUSES = [('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Declined'), ('withdrawn', 'Withdrawn'), ('cancelled', 'Trip cancelled')]
    trip = models.ForeignKey(RideTrip, on_delete=models.CASCADE, related_name='requests')
    requester = models.ForeignKey('User', on_delete=models.CASCADE, related_name='ride_requests')
    note = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=10, choices=STATUSES, default='pending')
    conversation = models.ForeignKey('Conversation', on_delete=models.SET_NULL, null=True, blank=True, related_name='ride_requests')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at', 'pk']
        constraints = [
            models.UniqueConstraint(fields=['trip', 'requester'], name='ride_unique_requester'),
            models.CheckConstraint(condition=models.Q(status__in=['pending', 'accepted', 'rejected', 'withdrawn', 'cancelled']), name='ride_request_status_valid'),
        ]

    def __str__(self):
        return f'Ride request {self.pk}: {self.status}'


class User(AbstractUser):
    USER_TYPES = [
        # ── Employer types ───────────────────────────────
        ('company',             'Company'),
        ('shop',                'Shop'),
        ('recruiter',           'Recruiter / Placement Agency'),
        ('factory',             'Factory'),
        ('startup',             'Startup'),
        ('institution',         'Institution'),
        ('ngo',                 'NGO'),
        ('hospital',            'Hospital'),
        ('hotel',               'Hotel / Restaurant'),
        ('farm',                'Farm'),
        ('individual_employer', 'Individual Employer'),
        # ── Job-seeker types ─────────────────────────────
        ('employee',            'Employee'),
        ('individual',          'Individual'),
        ('freelancer',          'Freelancer'),
        # ── Advertiser ────────────────────────────────────
        ('advertiser',          'Advertiser'),
    ]

    EMPLOYER_TYPES = [
        'company', 'shop', 'recruiter', 'factory', 'startup',
        'institution', 'ngo', 'hospital', 'hotel',
        'farm', 'individual_employer',
    ]

    ADMIN_ROLES = [
        ('',               'Regular User'),
        ('scoped_admin',   'Assigned Admin'),
        ('super_admin',    'Super Admin'),
        ('state_admin',    'State Admin'),
        ('district_admin', 'District Admin'),
    ]
    user_type     = models.CharField(max_length=20, choices=USER_TYPES, default='employee')
    admin_role    = models.CharField(max_length=20, choices=ADMIN_ROLES, blank=True, default='')
    phone          = models.CharField(max_length=10, blank=True)
    business_phone = models.CharField(max_length=10, blank=True, help_text='Business/shop phone — can also be used to login')
    whatsapp       = models.CharField(max_length=10, blank=True)
    address       = models.TextField(blank=True)
    city          = models.CharField(max_length=100, blank=True)
    pincode       = models.CharField(max_length=6, blank=True)
    preferred_pincode_1 = models.CharField(max_length=6, blank=True)
    preferred_pincode_2 = models.CharField(max_length=6, blank=True)
    referral_code = models.CharField(max_length=12, unique=True, blank=True, null=True)
    salesman_biz_id = models.CharField(max_length=16, unique=True, blank=True, null=True,
                                       help_text='Unique ID shared with salesman for business linkage')

    def __str__(self):
        return self.username

    def is_employer(self):       return self.user_type in self.EMPLOYER_TYPES
    def is_super_admin(self):    return self.admin_role == 'super_admin'
    def is_state_admin(self):    return self.admin_role == 'state_admin'
    def is_district_admin(self): return self.admin_role == 'district_admin'
    def is_any_admin(self):      return bool(self.admin_role)


class CompanyProfile(models.Model):
    PRODUCT_ACCESS_STATUS = [('', 'No request'), ('pending', 'Waiting for review'), ('approved', 'Approved'), ('declined', 'Changes requested')]
    user         = models.OneToOneField(User, on_delete=models.CASCADE, related_name='company')
    company_name = models.CharField(max_length=200)
    description = models.TextField(blank=True, max_length=1000)
    industry     = models.CharField(max_length=100, blank=True)
    website      = models.URLField(blank=True)
    company_size = models.CharField(max_length=50, blank=True)
    company_id   = models.CharField(max_length=20, unique=True, blank=True, db_index=True)
    logo         = models.ImageField(upload_to='business_logos/', blank=True, null=True)
    banner_image = models.ImageField(upload_to='business_banners/', blank=True, null=True)
    product_limit = models.PositiveIntegerField(default=10)
    requested_product_limit = models.PositiveIntegerField(null=True, blank=True)
    product_access_status = models.CharField(max_length=12, choices=PRODUCT_ACCESS_STATUS, blank=True, default='')
    product_access_requested_at = models.DateTimeField(null=True, blank=True)
    product_access_note = models.TextField(blank=True)

    def __str__(self):
        return self.company_name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('business_profile', args=[self.company_id])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.company_id:
            self.company_id = f'CO-{self.pk:06d}'
            CompanyProfile.objects.filter(pk=self.pk).update(company_id=self.company_id)


class AnalyticsVisitor(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    first_seen=models.DateTimeField(auto_now_add=True)
    last_seen=models.DateTimeField(db_index=True)


class AnalyticsVisit(models.Model):
    visitor=models.ForeignKey(AnalyticsVisitor,on_delete=models.CASCADE,related_name='visits')
    user=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name='site_visits')
    started_at=models.DateTimeField(auto_now_add=True,db_index=True)
    last_seen=models.DateTimeField(db_index=True)
    ended_at=models.DateTimeField(null=True,blank=True)
    engagement_updated_at=models.DateTimeField()
    engaged_seconds=models.PositiveIntegerField(default=0)
    current_path=models.CharField(max_length=200,blank=True)
    device=models.CharField(max_length=10,default='desktop')
    source=models.CharField(max_length=100,default='Direct')


class AnalyticsEvent(models.Model):
    id=models.UUIDField(primary_key=True,editable=False)
    visit=models.ForeignKey(AnalyticsVisit,on_delete=models.CASCADE,related_name='events')
    event_type=models.CharField(max_length=12,choices=[('pageview','Page view'),('click','Click'),('submit','Form submit')])
    path=models.CharField(max_length=200)
    label=models.CharField(max_length=80,blank=True)
    target=models.CharField(max_length=200,blank=True)
    created_at=models.DateTimeField(auto_now_add=True,db_index=True)

    class Meta:
        indexes=[models.Index(fields=['event_type','created_at'],name='analytics_type_time')]


class PromotionEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    offer = models.ForeignKey('LocalOffer', null=True, blank=True, on_delete=models.CASCADE, related_name='engagement_events')
    ad = models.ForeignKey('AdPost', null=True, blank=True, on_delete=models.CASCADE, related_name='engagement_events')
    action = models.CharField(max_length=5, choices=[('view', 'View'), ('click', 'Click')])
    visitor = models.UUIDField()
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        constraints = [models.CheckConstraint(
            condition=(models.Q(offer__isnull=False, ad__isnull=True) | models.Q(offer__isnull=True, ad__isnull=False)),
            name='promotion_exactly_one_target',
        )]


class LocalFromFollow(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE,related_name='local_from_follow')
    is_following=models.BooleanField(default=False,db_index=True)
    prompt_dismissed=models.BooleanField(default=False)
    followed_at=models.DateTimeField(null=True,blank=True)


class BusinessFollow(models.Model):
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='followers')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='business_follows')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [models.UniqueConstraint(fields=['company', 'user'], name='one_business_follow_per_user')]


class BusinessReview(models.Model):
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='business_reviews')
    rating = models.PositiveSmallIntegerField()
    text = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(fields=['company', 'user'], name='one_review_per_business_customer'),
            models.CheckConstraint(condition=models.Q(rating__gte=1, rating__lte=5), name='business_review_rating_range'),
        ]


class BusinessReviewReport(models.Model):
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='review_reports')
    month = models.DateField()
    summary = models.TextField()
    ai_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    emailed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-month']
        constraints = [models.UniqueConstraint(fields=['company', 'month'], name='one_business_report_per_month')]


class ShopDirectoryEntry(models.Model):
    """Superadmin's imported shop list, available for account-matched onboarding."""
    name=models.CharField(max_length=150,db_index=True)
    normalized_name=models.CharField(max_length=150)
    phone=models.CharField(max_length=10,db_index=True,blank=True)
    alternate_phones=models.JSONField(default=list,blank=True)
    source_phone=models.TextField(blank=True,max_length=1000)
    phone_note=models.CharField(max_length=500,blank=True)
    contacts_reviewed=models.BooleanField(default=False)
    pincode=models.CharField(max_length=6,blank=True)
    city=models.CharField(max_length=100,blank=True)
    address=models.CharField(max_length=500,blank=True)
    category=models.CharField(max_length=100,blank=True)
    registered_shop=models.OneToOneField(CompanyProfile,on_delete=models.SET_NULL,null=True,blank=True,related_name='directory_entry')
    uploaded_by=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name='uploaded_shops')
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    class Meta:
        ordering=['name','pk']
        constraints=[models.UniqueConstraint(fields=['phone','normalized_name'],name='unique_directory_shop_phone')]


class ShopProfile(models.Model):
    user         = models.OneToOneField(User, on_delete=models.CASCADE, related_name='shop')
    shop_name    = models.CharField(max_length=200)
    shop_type    = models.CharField(max_length=100, blank=True)
    owner_name   = models.CharField(max_length=100, blank=True)
    website      = models.URLField(blank=True)
    logo         = models.ImageField(upload_to='business_logos/', blank=True, null=True)
    banner_image = models.ImageField(upload_to='business_banners/', blank=True, null=True)

    def __str__(self):
        return self.shop_name


class JobSeekerProfile(models.Model):
    COLLAR = [('white', 'White Collar'), ('blue', 'Blue Collar'), ('any', 'Any')]
    GENDER = [
        ('male',       'Male'),
        ('female',     'Female'),
        ('other',      'Other'),
        ('prefer_not', 'Prefer not to say'),
    ]
    AVAILABILITY = [
        ('immediate',      'Immediate Joiner'),
        ('within_1month',  'Within 1 Month'),
        ('within_3months', 'Within 3 Months'),
        ('not_looking',    'Not Actively Looking'),
    ]
    SALARY_TYPE = [('month', 'Per Month'), ('day', 'Per Day'), ('hour', 'Per Hour')]

    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seeker')
    seeker_id  = models.CharField(max_length=20, unique=True, blank=True, db_index=True)

    # ── Personal ──────────────────────────────────
    photo      = models.ImageField(upload_to='seeker_photos/', blank=True, null=True)
    dob        = models.DateField(null=True, blank=True)
    gender     = models.CharField(max_length=15, choices=GENDER, blank=True)

    # ── Location ──────────────────────────────────
    district   = models.ForeignKey('District', null=True, blank=True, on_delete=models.SET_NULL, related_name='seekers')
    state      = models.ForeignKey('State',    null=True, blank=True, on_delete=models.SET_NULL, related_name='seekers')
    preferred_location = models.CharField(max_length=500, blank=True)
    preferred_pincode  = models.CharField(max_length=200, blank=True)
    open_to_relocate   = models.BooleanField(default=False)

    # ── Career Preferences ────────────────────────
    job_category      = models.CharField(max_length=10, choices=COLLAR, default='any')
    blue_collar_type  = models.CharField(max_length=30, blank=True)
    industry          = models.CharField(max_length=300, blank=True)
    preferred_roles   = models.CharField(max_length=500, blank=True)
    availability    = models.CharField(max_length=20, choices=AVAILABILITY, default='immediate')

    # ── Compensation ──────────────────────────────
    salary_min  = models.IntegerField(null=True, blank=True)
    salary_max  = models.IntegerField(null=True, blank=True)
    salary_type = models.CharField(max_length=10, choices=SALARY_TYPE, default='month')
    rate        = models.CharField(max_length=100, blank=True)   # freelancer rate

    # ── Qualifications ────────────────────────────
    education         = models.CharField(max_length=100, blank=True)
    education_details = models.TextField(blank=True)
    experience        = models.CharField(max_length=50, blank=True)
    skills            = models.TextField(blank=True)
    languages         = models.CharField(max_length=300, blank=True)
    primary_skill     = models.CharField(max_length=100, blank=True)

    # ── Documents ─────────────────────────────────
    resume           = models.FileField(upload_to='resumes/',    blank=True, null=True)
    driving_license  = models.FileField(upload_to='licenses/',   blank=True, null=True)
    portfolio_url    = models.URLField(blank=True)
    portfolio_file   = models.FileField(upload_to='portfolios/', blank=True, null=True)

    # ── Meta ──────────────────────────────────────
    is_verified        = models.BooleanField(default=False)
    profile_completed  = models.BooleanField(default=False)
    updated_at         = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} — {self.primary_skill or self.industry or 'Job Seeker'}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.seeker_id:
            self.seeker_id = f'JS-{self.pk:06d}'
            JobSeekerProfile.objects.filter(pk=self.pk).update(seeker_id=self.seeker_id)

    def completion_percent(self):
        fields = [
            self.photo, self.dob, self.gender,
            self.district_id, self.preferred_location,
            self.industry, self.preferred_roles,
            self.education, self.experience,
            self.skills, self.languages,
            self.resume,
        ]
        filled = sum(1 for f in fields if f)
        return int((filled / len(fields)) * 100)


class Conversation(models.Model):
    TYPES = [
        ('job_inquiry',      'Job Inquiry'),
        ('interview_invite', 'Interview Invitation'),
        ('support',          'Support / Complaint'),
        ('general',          'General'),
    ]
    # user_a.pk is always < user_b.pk — enforced in get_or_create helper
    user_a     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conv_as_a')
    user_b     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conv_as_b')
    conv_type  = models.CharField(max_length=20, choices=TYPES, default='general')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def other_user(self, me):
        return self.user_b if self.user_a_id == me.id else self.user_a

    def unread_for(self, user):
        return self.messages.filter(is_read=False).exclude(sender=user).count()

    def last_msg(self):
        return self.messages.order_by('-sent_at').first()

    def __str__(self):
        return f"{self.user_a} ↔ {self.user_b}"


class Message(models.Model):
    MSG_TYPES = [
        ('text',             'Text'),
        ('image',            'Image'),
        ('file',             'File / PDF'),
        ('resume',           'Resume'),
        ('interview_invite', 'Interview Invitation'),
    ]
    INVITE_STATUS = [
        ('pending',  'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE,
                                     related_name='messages', null=True, blank=True)
    sender   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE,
                                 related_name='received_messages', null=True, blank=True)

    msg_type  = models.CharField(max_length=20, choices=MSG_TYPES, default='text')
    content   = models.TextField(blank=True)

    # Attachment
    file      = models.FileField(upload_to='chat_files/%Y/%m/', blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True)

    # Interview invite payload (only when msg_type='interview_invite')
    invite_date     = models.DateField(null=True, blank=True)
    invite_time     = models.TimeField(null=True, blank=True)
    invite_mode     = models.CharField(max_length=20, blank=True,
                                       choices=[('in_person','In Person'),
                                                ('phone','Phone Call'),
                                                ('video','Video Call')])
    invite_location = models.CharField(max_length=300, blank=True)
    invite_link     = models.URLField(blank=True)
    invite_notes    = models.TextField(blank=True)
    invite_status   = models.CharField(max_length=20, choices=INVITE_STATUS,
                                       default='pending', blank=True)

    is_read  = models.BooleanField(default=False)
    read_at  = models.DateTimeField(null=True, blank=True)
    sent_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sent_at']

    def __str__(self):
        return f"{self.sender.username} [{self.msg_type}]: {self.content[:40]}"

    def is_image(self):
        return self.msg_type == 'image'

    def is_file(self):
        return self.msg_type in ('file', 'resume')

    def is_invite(self):
        return self.msg_type == 'interview_invite'


# ============================================================
# ADVERTISER MODULE
# ============================================================

class Advertiser(models.Model):
    ADVERTISER_STATUS = [
        ('pending',   'Pending Approval'),
        ('approved',  'Approved'),
        ('rejected',  'Rejected'),
        ('suspended', 'Suspended'),
    ]
    user           = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='advertiser')
    business_name  = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100)
    phone          = models.CharField(max_length=10)
    email          = models.EmailField()
    address        = models.TextField()
    description    = models.TextField(blank=True, help_text='About your business / what you offer')
    gst            = models.CharField(max_length=15, blank=True)
    website        = models.URLField(blank=True)
    banner_image   = models.ImageField(upload_to='advertiser_banners/', blank=True, null=True)
    status         = models.CharField(max_length=20, choices=ADVERTISER_STATUS, default='pending')
    rejection_note = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    approved_at    = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.business_name


class AdPackage(models.Model):
    AD_TYPES = [
        ('homepage_banner',    'Homepage Banner'),
        ('district_banner',    'District Banner'),
        ('state_banner',       'State Banner'),
        ('featured_employer',  'Featured Employer'),
        ('featured_job',       'Featured Job'),
        ('sidebar',            'Sidebar Ad'),
        ('dashboard_banner',   'Dashboard Banner'),
        ('popup',              'Popup Ad'),
        ('sponsored_job',      'Sponsored Job'),
        ('sponsored_employer', 'Sponsored Employer'),
    ]
    name          = models.CharField(max_length=100)
    ad_type       = models.CharField(max_length=30, choices=AD_TYPES)
    duration_days = models.IntegerField(default=30)
    price         = models.DecimalField(max_digits=10, decimal_places=2)
    description   = models.TextField(blank=True)
    size_specs    = models.CharField(max_length=100, blank=True)
    is_active     = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ad_type', 'price']

    def __str__(self):
        return f"{self.name} — ₹{self.price}/{self.duration_days}d"


class Advertisement(models.Model):
    AD_STATUS = [
        ('draft',           'Draft'),
        ('pending_payment', 'Pending Payment'),
        ('pending_review',  'Pending Review'),
        ('active',          'Active'),
        ('paused',          'Paused'),
        ('expired',         'Expired'),
        ('rejected',        'Rejected'),
    ]
    advertiser = models.ForeignKey(Advertiser, on_delete=models.CASCADE, related_name='ads')
    package    = models.ForeignKey(AdPackage, on_delete=models.CASCADE)
    title      = models.CharField(max_length=200)
    image      = models.ImageField(upload_to='ads/', blank=True)
    link_url   = models.URLField(blank=True)
    content    = models.TextField(blank=True)
    district   = models.CharField(max_length=100, blank=True)
    state      = models.CharField(max_length=100, blank=True)
    status     = models.CharField(max_length=20, choices=AD_STATUS, default='draft')
    start_date = models.DateField(null=True, blank=True)
    end_date   = models.DateField(null=True, blank=True)
    views      = models.IntegerField(default=0)
    clicks     = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} [{self.package.get_ad_type_display()}]"

    def ctr(self):
        return round((self.clicks / self.views) * 100, 2) if self.views else 0

    def days_remaining(self):
        from django.utils import timezone
        if self.end_date:
            return max(0, (self.end_date - timezone.now().date()).days)
        return 0

    def is_expiring_soon(self):
        return 0 < self.days_remaining() <= 7


class AdPayment(models.Model):
    PAYMENT_STATUS = [
        ('pending',  'Pending'),
        ('paid',     'Paid'),
        ('failed',   'Failed'),
        ('refunded', 'Refunded'),
    ]
    advertisement  = models.OneToOneField(Advertisement, on_delete=models.CASCADE, related_name='payment')
    amount         = models.DecimalField(max_digits=10, decimal_places=2)
    gst_amount     = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status         = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    invoice_number = models.CharField(max_length=50, blank=True)
    paid_at        = models.DateTimeField(null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"INV-{self.invoice_number} ₹{self.total_amount} [{self.status}]"


# ============================================================
# ADMIN HIERARCHY MODULE
# ============================================================

class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=2, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class State(models.Model):
    country = models.ForeignKey(Country, null=True, blank=True, on_delete=models.PROTECT, related_name="states")
    geonames_id = models.PositiveBigIntegerField(null=True, blank=True, unique=True, editable=False)
    name      = models.CharField(max_length=100, unique=True)
    code      = models.CharField(max_length=16, unique=True)
    is_active = models.BooleanField(default=True)
    created_at= models.DateTimeField(auto_now_add=True)
    created_by= models.ForeignKey('User', null=True, blank=True, on_delete=models.SET_NULL, related_name='created_states')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"

    def district_count(self):
        return self.districts.count()

class District(models.Model):
    state     = models.ForeignKey(State, on_delete=models.CASCADE, related_name='districts')
    geonames_id = models.PositiveBigIntegerField(null=True, blank=True, unique=True, editable=False)
    name      = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at= models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('state', 'name')
        ordering = ['name']

    def __str__(self):
        return f"{self.name}, {self.state.name}"


class PinCode(models.Model):
    district  = models.ForeignKey(District, on_delete=models.CASCADE, related_name='pincodes')
    code      = models.CharField(max_length=6, unique=True)
    area_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} — {self.area_name}"


class AdminProfile(models.Model):
    HIERARCHY_CHOICES = [('country', 'Country Admin'), ('state', 'State Admin'),
        ('district', 'District Admin'), ('area', 'Area Admin'), ('salesman', 'Salesman'), ('it', 'State IT Admin')]
    hierarchy_level = models.CharField(max_length=12, choices=HIERARCHY_CHOICES, blank=True)
    country = models.ForeignKey(Country, null=True, blank=True, on_delete=models.PROTECT)
    area = models.ForeignKey(PinCode, null=True, blank=True, on_delete=models.PROTECT)

    ADMIN_ROLES = [
        ('scoped_admin',   'Assigned Admin'),
        ('super_admin',    'Super Admin'),
        ('state_admin',    'State Admin'),
        ('district_admin', 'District Admin'),
    ]
    user         = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')
    role         = models.CharField(max_length=20, choices=ADMIN_ROLES)
    state        = models.ForeignKey(State, null=True, blank=True, on_delete=models.SET_NULL, related_name='state_admin_profiles')
    district     = models.ForeignKey(District, null=True, blank=True, on_delete=models.SET_NULL, related_name='district_admin_profiles')
    appointed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='appointed_admins')
    notes        = models.TextField(blank=True)
    all_states   = models.BooleanField(default=False)
    sections     = models.JSONField(default=list, blank=True)
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_role_display()} — {self.user.get_full_name() or self.user.username}"


class AdminActivity(models.Model):
    actor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='admin_activities')
    actor_name = models.CharField(max_length=150)
    section = models.CharField(max_length=30)
    action = models.CharField(max_length=30)
    target_id = models.CharField(max_length=40, blank=True)
    target_name = models.CharField(max_length=250, blank=True)
    state_name = models.CharField(max_length=100, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at', '-pk']


class Industry(models.Model):
    COLLAR_TYPES = [('white', 'White Collar'), ('blue', 'Blue Collar'), ('both', 'Both')]
    name      = models.CharField(max_length=100, unique=True)
    collar    = models.CharField(max_length=10, choices=COLLAR_TYPES, default='both')
    icon      = models.CharField(max_length=50, blank=True, default='fas fa-industry')
    is_active = models.BooleanField(default=True)
    order     = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Discount(models.Model):
    DISCOUNT_TYPES = [('percent', 'Percentage'), ('flat', 'Flat Amount')]
    code          = models.CharField(max_length=20, unique=True)
    description   = models.CharField(max_length=200, blank=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES, default='percent')
    value         = models.DecimalField(max_digits=8, decimal_places=2)
    min_amount    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_uses      = models.IntegerField(default=0, help_text='0 = unlimited')
    used_count    = models.IntegerField(default=0)
    valid_from    = models.DateField(null=True, blank=True)
    valid_until   = models.DateField(null=True, blank=True)
    is_active     = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} ({self.value}{'%' if self.discount_type == 'percent' else '₹'} off)"

    def is_valid(self):
        from django.utils import timezone
        today = timezone.now().date()
        if not self.is_active:
            return False
        if self.valid_from and today < self.valid_from:
            return False
        if self.valid_until and today > self.valid_until:
            return False
        if self.max_uses and self.used_count >= self.max_uses:
            return False
        return True


class Complaint(models.Model):
    COMPLAINT_STATUS = [
        ('open',      'Open'),
        ('in_review', 'In Review'),
        ('resolved',  'Resolved'),
        ('closed',    'Closed'),
    ]
    COMPLAINT_TYPES = [
        ('job',        'Misleading Job'),
        ('employer',   'Employer Misconduct'),
        ('payment',    'Payment Issue'),
        ('harassment', 'Harassment'),
        ('spam',       'Spam / Fake'),
        ('other',      'Other'),
    ]
    submitted_by   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='complaints')
    complaint_type = models.CharField(max_length=20, choices=COMPLAINT_TYPES, default='other')
    subject        = models.CharField(max_length=200)
    description    = models.TextField()
    district       = models.ForeignKey(District, null=True, blank=True, on_delete=models.SET_NULL, related_name='complaints')
    status         = models.CharField(max_length=20, choices=COMPLAINT_STATUS, default='open')
    assigned_to    = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_complaints')
    resolution     = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    resolved_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_complaint_type_display()}] {self.subject}"


class SystemNotification(models.Model):
    NOTIF_TYPES = [
        ('info',    'Info'),
        ('warning', 'Warning'),
        ('success', 'Success'),
        ('alert',   'Alert'),
    ]
    title      = models.CharField(max_length=200)
    message    = models.TextField()
    notif_type = models.CharField(max_length=10, choices=NOTIF_TYPES, default='info')
    target_role= models.CharField(max_length=20, blank=True, help_text='Leave blank for all users')
    is_active  = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


# ============================================================
# EMPLOYER DASHBOARD MODELS
# ============================================================

class UserNotification(models.Model):
    TYPES = [
        ('info',    'Info'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('alert',   'Alert'),
    ]
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title      = models.CharField(max_length=200)
    message    = models.TextField()
    notif_type = models.CharField(max_length=10, choices=TYPES, default='info')
    link       = models.CharField(max_length=200, blank=True)
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


# ── FLICKS ────────────────────────────────────────────────────────────────────

class FlickAdSettings(models.Model):
    upi_id       = models.CharField(max_length=100, default='mypincod@upi')
    price        = models.DecimalField(max_digits=10, decimal_places=2, default=499)
    duration_days = models.IntegerField(default=84)

    class Meta:
        verbose_name = 'Flick Ad Settings'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"₹{self.price} / {self.duration_days} days — UPI: {self.upi_id}"


class Flick(models.Model):
    PLAN_CHOICES = [('', 'No Plan'), ('basic', 'Basic'), ('premium', 'Premium'), ('featured', 'Featured')]
    CAT_CHOICES  = [('general', 'General'), ('health', 'Health'), ('job', 'Job'), ('business', 'Business')]
    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flicks')
    title          = models.CharField(max_length=150, blank=True)
    caption        = models.TextField(blank=True)
    category       = models.CharField(max_length=20, choices=CAT_CHOICES, default='general')
    video          = models.FileField(upload_to='flicks/videos/', blank=True, null=True)
    image          = models.ImageField(upload_to='flicks/images/', blank=True, null=True)
    views          = models.PositiveIntegerField(default=0)
    is_promoted    = models.BooleanField(default=False)
    advertise_plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='', blank=True)
    promoted_until = models.DateField(null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} — {self.title or 'Flick'}"

    def like_count(self):
        return self.likes.count()

    def comment_count(self):
        return self.comments.count()

    def is_active_promoted(self):
        from django.utils import timezone
        if self.promoted_until and self.promoted_until >= timezone.now().date():
            return True
        return self.is_promoted


class FlickAdPayment(models.Model):
    STATUS = [('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')]
    flick          = models.ForeignKey(Flick, on_delete=models.CASCADE, related_name='ad_payments')
    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flick_ad_payments')
    transaction_id = models.CharField(max_length=100)
    amount         = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days  = models.IntegerField(default=84)
    status         = models.CharField(max_length=20, choices=STATUS, default='pending')
    created_at     = models.DateTimeField(auto_now_add=True)
    approved_at    = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.flick} — ₹{self.amount} [{self.status}]"


class FlickLike(models.Model):
    flick      = models.ForeignKey(Flick, on_delete=models.CASCADE, related_name='likes')
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flick_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('flick', 'user')


class FlickComment(models.Model):
    flick      = models.ForeignKey(Flick, on_delete=models.CASCADE, related_name='comments')
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flick_comments')
    text       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username}: {self.text[:40]}"


class FlickReport(models.Model):
    REASONS = [
        ('inappropriate', 'Inappropriate Content'),
        ('spam',          'Spam or Misleading'),
        ('violence',      'Violence or Dangerous'),
        ('harassment',    'Harassment or Bullying'),
        ('misinformation','False Information'),
        ('other',         'Other'),
    ]
    STATUS = [('pending', 'Pending'), ('reviewed', 'Reviewed'), ('dismissed', 'Dismissed')]
    flick      = models.ForeignKey(Flick, on_delete=models.CASCADE, related_name='reports')
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flick_reports')
    reason     = models.CharField(max_length=20, choices=REASONS)
    note       = models.TextField(blank=True)
    status     = models.CharField(max_length=20, choices=STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('flick', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} reported {self.flick} — {self.reason}"


# ── SIMPLE ADS ────────────────────────────────────────────────────────────────

class AdSettings(models.Model):
    upi_id        = models.CharField(max_length=100, blank=True)
    renewal_price = models.PositiveIntegerField(default=199)
    renewal_days  = models.PositiveIntegerField(default=30)

    class Meta:
        verbose_name = 'Ad Settings'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'Ad Settings'


class AdPost(models.Model):
    STATUS = [('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')]
    AD_TYPES = [('shop', 'Shop promotion'), ('product', 'Product promotion'), ('offer', 'Offer promotion')]
    ad_type = models.CharField(max_length=20, choices=AD_TYPES, default='shop')
    title = models.CharField(max_length=160, blank=True)
    contact_name = models.CharField(max_length=100, blank=True)
    contact_phone = models.CharField(max_length=10, blank=True)
    requested_days = models.PositiveSmallIntegerField(default=7, choices=[(7, '7 days'), (14, '14 days'), (30, '30 days')])
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ad_posts')
    company_name = models.CharField(max_length=200)
    pincode      = models.CharField(max_length=10, blank=True)
    description  = models.TextField()
    image        = models.ImageField(upload_to='ad_posts/')
    website      = models.URLField(blank=True)
    status       = models.CharField(max_length=20, choices=STATUS, default='pending')
    reject_note  = models.TextField(blank=True)
    views        = models.PositiveIntegerField(default=0)
    clicks       = models.PositiveIntegerField(default=0)
    created_at   = models.DateTimeField(auto_now_add=True)
    approved_at  = models.DateTimeField(null=True, blank=True)
    expires_at   = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.company_name} [{self.status}]"

    @property
    def is_live(self):
        from django.utils import timezone
        if self.status != 'approved':
            return False
        if not self.expires_at:
            return True
        return self.expires_at >= timezone.now().date()

    @property
    def is_expired(self):
        from django.utils import timezone
        if self.status != 'approved' or not self.expires_at:
            return False
        return self.expires_at < timezone.now().date()

    @property
    def pending_renewal(self):
        return self.renewals.filter(status='pending').exists()


class AdRenewal(models.Model):
    STATUS = [('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')]
    ad             = models.ForeignKey(AdPost, on_delete=models.CASCADE, related_name='renewals')
    transaction_id = models.CharField(max_length=200)
    screenshot     = models.ImageField(upload_to='ad_renewals/')
    amount         = models.PositiveIntegerField()
    status         = models.CharField(max_length=20, choices=STATUS, default='pending')
    reject_note    = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    approved_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ad.company_name} renewal [{self.status}]"


class BusinessGalleryImage(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gallery_images')
    image      = models.ImageField(upload_to='business_gallery/')
    caption    = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} gallery image"


class LocalOffer(models.Model):
    owner = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name='local_offers')
    CATEGORY_CHOICES = [
        ('food',     'Food & Drinks'),
        ('salon',    'Salon & Beauty'),
        ('health',   'Health & Pharmacy'),
        ('shop',     'Shopping'),
        ('services', 'Services'),
        ('other',    'Other'),
    ]
    business_name  = models.CharField(max_length=150)
    title          = models.CharField(max_length=200)
    discount_text  = models.CharField(max_length=60, help_text='e.g. 20% OFF, Buy 1 Get 1, Free Delivery')
    category       = models.CharField(max_length=50, default='other')
    image          = models.ImageField(upload_to='offers/', blank=True, null=True)
    description    = models.TextField(blank=True)
    valid_until    = models.DateField(null=True, blank=True)
    valid_days     = models.CharField(max_length=50, blank=True, help_text='Comma-separated days e.g. Mon,Tue for recurring weekly offers')
    contact_phone  = models.CharField(max_length=15, blank=True)
    link_url       = models.URLField(blank=True)
    is_flash       = models.BooleanField(default=False, help_text='Show in Flash Deals with countdown')
    is_active      = models.BooleanField(default=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.business_name} – {self.discount_text}"


class Product(models.Model):
    shop = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True, max_length=3000)
    category = models.CharField(max_length=80, blank=True)
    image = models.ImageField(upload_to='products/')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_percent = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gt=0), name='product_positive_price'),
            models.CheckConstraint(condition=models.Q(discount_percent__lte=100), name='product_discount_range'),
        ]
        indexes = [models.Index(fields=['shop', 'is_active', '-created_at'], name='product_shop_active_idx')]

    @property
    def sale_price(self):
        from decimal import Decimal, ROUND_HALF_UP
        return (self.price * (Decimal('100') - self.discount_percent) / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('product_detail', args=[self.pk])

    def __str__(self):
        return f'{self.name} — {self.shop.company_name}'


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/gallery/')
    position = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ['position', 'pk']
        constraints = [
            models.UniqueConstraint(fields=['product', 'position'], name='product_image_position_unique'),
            models.CheckConstraint(condition=models.Q(position__gte=1, position__lte=5), name='product_image_position_range'),
        ]


class ShopVideo(models.Model):
    shop = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='videos')
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, max_length=1500)
    video = models.FileField(upload_to='shop_videos/')
    thumbnail = models.ImageField(upload_to='shop_videos/thumbnails/', blank=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']

    def __str__(self):
        return f'{self.title} — {self.shop.company_name}'
