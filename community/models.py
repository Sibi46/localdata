from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class FamilyStory(models.Model):
    CATEGORY_CHOICES = [
        ('birthday',    'Birthday'),
        ('achievement', 'Achievement'),
        ('tradition',   'Tradition'),
        ('celebration', 'Celebration'),
        ('vacation',    'Vacation'),
        ('gardening',   'Gardening'),
        ('other',       'Other'),
    ]

    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='family_stories')
    title      = models.CharField(max_length=200)
    content    = models.TextField()
    image      = models.ImageField(upload_to='family_stories/', blank=True, null=True)
    category   = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    pincode    = models.CharField(max_length=10, blank=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def like_count(self):
        return self.likes.count()

    def comment_count(self):
        return self.comments.count()


class FamilyStoryLike(models.Model):
    user  = models.ForeignKey(User, on_delete=models.CASCADE)
    story = models.ForeignKey(FamilyStory, on_delete=models.CASCADE, related_name='likes')

    class Meta:
        unique_together = ('user', 'story')


class FamilyStoryComment(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    story      = models.ForeignKey(FamilyStory, on_delete=models.CASCADE, related_name='comments')
    text       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user} on {self.story}"


# ── SCHOOL CORNER ──────────────────────────────────────────────────────────────
class School(models.Model):
    TYPE_CHOICES = [
        ('primary',    'Primary School'),
        ('secondary',  'Secondary School'),
        ('higher_sec', 'Higher Secondary'),
        ('college',    'College'),
        ('university', 'University'),
    ]
    name        = models.CharField(max_length=200)
    school_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='secondary')
    address     = models.TextField(blank=True)
    pincode     = models.CharField(max_length=10, blank=True)
    logo        = models.ImageField(upload_to='school_logos/', blank=True, null=True)
    cover       = models.ImageField(upload_to='school_covers/', blank=True, null=True)
    about       = models.TextField(blank=True)
    website     = models.URLField(blank=True)
    phone            = models.CharField(max_length=15, blank=True)
    principal_name   = models.CharField(max_length=150, blank=True)
    vice_principal   = models.CharField(max_length=150, blank=True)
    is_verified      = models.BooleanField(default=False)
    created_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='schools_created')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def follower_count(self):
        return self.followers.count()

    def post_count(self):
        return self.posts.count()


class SchoolAdmin(models.Model):
    ROLE_CHOICES = [
        ('owner',   'Owner'),
        ('admin',   'Admin'),
        ('teacher', 'Teacher'),
    ]
    school     = models.ForeignKey(School, on_delete=models.CASCADE, related_name='admins')
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='school_admin_roles')
    role       = models.CharField(max_length=10, choices=ROLE_CHOICES, default='admin')
    added_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='school_admins_added')
    phone      = models.CharField(max_length=15, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('school', 'user')

    def __str__(self):
        return f"{self.user.username} — {self.role} @ {self.school.name}"


class SchoolFollow(models.Model):
    user   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='school_follows')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'school')


class SchoolPost(models.Model):
    POST_TYPE_CHOICES = [
        ('daily',        '📌 Daily'),
        ('annual_day',   '🎭 Annual Day'),
        ('sports_day',   '⚽ Sports Day'),
        ('science_fair', '🔬 Fair'),
        ('achievement',  '🏆 Achievement'),
        ('event',        '📅 Event'),
        ('announcement', '📢 Announcement'),
        ('other',        '📌 Other'),
    ]
    school     = models.ForeignKey(School, on_delete=models.CASCADE, related_name='posts')
    posted_by  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='school_posts')
    post_type  = models.CharField(max_length=20, choices=POST_TYPE_CHOICES, default='other')
    title      = models.CharField(max_length=200)
    content    = models.TextField()
    image      = models.ImageField(upload_to='school_posts/', blank=True, null=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.school.name} — {self.title}"

    def like_count(self):
        return self.likes.count()


class SchoolPostLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(SchoolPost, on_delete=models.CASCADE, related_name='likes')

    class Meta:
        unique_together = ('user', 'post')


class SchoolPostComment(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    post       = models.ForeignKey(SchoolPost, on_delete=models.CASCADE, related_name='comments')
    text       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


# ── STUDENT SUCCESS ────────────────────────────────────────────────────────────
class StudentSuccess(models.Model):
    CAT_CHOICES = [
        ('academics',    'Academics'),
        ('sports',       'Sports'),
        ('arts',         'Arts & Culture'),
        ('music',        'Music'),
        ('scholarship',  'Scholarship'),
        ('competition',  'Competition'),
        ('other',        'Other'),
    ]
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_successes')
    student_name = models.CharField(max_length=100)
    school_name  = models.CharField(max_length=200, blank=True)
    grade        = models.CharField(max_length=30, blank=True)
    title        = models.CharField(max_length=200)
    content      = models.TextField()
    category     = models.CharField(max_length=20, choices=CAT_CHOICES, default='other')
    image        = models.ImageField(upload_to='student_success/', blank=True, null=True)
    pincode      = models.CharField(max_length=10, blank=True)
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Student Successes'

    def __str__(self):
        return f"{self.student_name} — {self.title}"

    def like_count(self):
        return self.likes.count()

    def comment_count(self):
        return self.comments.count()


class StudentSuccessLike(models.Model):
    user    = models.ForeignKey(User, on_delete=models.CASCADE)
    success = models.ForeignKey(StudentSuccess, on_delete=models.CASCADE, related_name='likes')

    class Meta:
        unique_together = ('user', 'success')


class StudentSuccessComment(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    success    = models.ForeignKey(StudentSuccess, on_delete=models.CASCADE, related_name='comments')
    text       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


# ── KIDS CORNER ────────────────────────────────────────────────────────────────
class KidsPost(models.Model):
    TYPE_CHOICES = [
        ('story',    'Story'),
        ('drawing',  'Drawing'),
        ('craft',    'Craft'),
        ('poem',     'Poem'),
        ('joke',     'Joke'),
        ('activity', 'Activity'),
        ('other',    'Other'),
    ]
    posted_by  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='kids_posts')
    kid_name   = models.CharField(max_length=100)
    age        = models.PositiveSmallIntegerField(null=True, blank=True)
    post_type  = models.CharField(max_length=20, choices=TYPE_CHOICES, default='other')
    title      = models.CharField(max_length=200)
    content    = models.TextField()
    image      = models.ImageField(upload_to='kids_corner/', blank=True, null=True)
    pincode    = models.CharField(max_length=10, blank=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.kid_name} — {self.title}"

    def like_count(self):
        return self.likes.count()

    def comment_count(self):
        return self.comments.count()


class KidsPostLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(KidsPost, on_delete=models.CASCADE, related_name='likes')

    class Meta:
        unique_together = ('user', 'post')


class KidsPostComment(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    post       = models.ForeignKey(KidsPost, on_delete=models.CASCADE, related_name='comments')
    text       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


# ── PARENTING ──────────────────────────────────────────────────────────────────
class ParentingPost(models.Model):
    CAT_CHOICES = [
        ('tips',      'Parenting Tips'),
        ('activity',  'Family Activity'),
        ('health',    'Child Health'),
        ('education', 'Education'),
        ('food',      'Food & Nutrition'),
        ('emotion',   'Emotional Support'),
        ('other',     'Other'),
    ]
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='parenting_posts')
    title      = models.CharField(max_length=200)
    content    = models.TextField()
    category   = models.CharField(max_length=20, choices=CAT_CHOICES, default='other')
    image      = models.ImageField(upload_to='parenting/', blank=True, null=True)
    pincode    = models.CharField(max_length=10, blank=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def like_count(self):
        return self.likes.count()

    def comment_count(self):
        return self.comments.count()


class ParentingLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(ParentingPost, on_delete=models.CASCADE, related_name='likes')

    class Meta:
        unique_together = ('user', 'post')


class ParentingComment(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    post       = models.ForeignKey(ParentingPost, on_delete=models.CASCADE, related_name='comments')
    text       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


# ── GRANDPARENTS ARCHIVE ───────────────────────────────────────────────────────
class GrandparentStory(models.Model):
    CAT_CHOICES = [
        ('memory',    'Childhood Memory'),
        ('wisdom',    'Life Wisdom'),
        ('recipe',    'Family Recipe'),
        ('tradition', 'Family Tradition'),
        ('history',   'Local History'),
        ('other',     'Other'),
    ]
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='grandparent_stories')
    elder_name  = models.CharField(max_length=100)
    age         = models.PositiveSmallIntegerField(null=True, blank=True)
    title       = models.CharField(max_length=200)
    content     = models.TextField()
    category    = models.CharField(max_length=20, choices=CAT_CHOICES, default='memory')
    image       = models.ImageField(upload_to='grandparents/', blank=True, null=True)
    pincode     = models.CharField(max_length=10, blank=True)
    era         = models.CharField(max_length=50, blank=True, help_text='e.g. 1960s, British era')
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.elder_name} — {self.title}"

    def like_count(self):
        return self.likes.count()

    def comment_count(self):
        return self.comments.count()


class GrandparentLike(models.Model):
    user  = models.ForeignKey(User, on_delete=models.CASCADE)
    story = models.ForeignKey(GrandparentStory, on_delete=models.CASCADE, related_name='likes')

    class Meta:
        unique_together = ('user', 'story')


class GrandparentComment(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    story      = models.ForeignKey(GrandparentStory, on_delete=models.CASCADE, related_name='comments')
    text       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


# ── LOCAL HEROES ───────────────────────────────────────────────────────────────
class LocalHero(models.Model):
    CAT_CHOICES = [
        ('social',       'Social Work'),
        ('environment',  'Environment'),
        ('education',    'Education'),
        ('health',       'Health & Medical'),
        ('sports',       'Sports'),
        ('arts',         'Arts & Culture'),
        ('other',        'Other'),
    ]
    posted_by   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='local_hero_posts')
    hero_name   = models.CharField(max_length=100)
    category    = models.CharField(max_length=20, choices=CAT_CHOICES, default='social')
    title       = models.CharField(max_length=200)
    content     = models.TextField()
    image       = models.ImageField(upload_to='local_heroes/', blank=True, null=True)
    pincode     = models.CharField(max_length=10, blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.hero_name} — {self.title}"

    def like_count(self):
        return self.likes.count()

    def comment_count(self):
        return self.comments.count()


class LocalHeroLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    hero = models.ForeignKey(LocalHero, on_delete=models.CASCADE, related_name='likes')

    class Meta:
        unique_together = ('user', 'hero')


class LocalHeroComment(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    hero       = models.ForeignKey(LocalHero, on_delete=models.CASCADE, related_name='comments')
    text       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


# ── COMMUNITY EVENTS ───────────────────────────────────────────────────────────
class CommunityEvent(models.Model):
    CAT_CHOICES = [
        ('festival',   'Festival'),
        ('sports',     'Sports'),
        ('cultural',   'Cultural'),
        ('health',     'Health Camp'),
        ('education',  'Education'),
        ('religious',  'Religious'),
        ('cleanup',    'Cleanup Drive'),
        ('other',      'Other'),
    ]
    posted_by   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events_posted')
    title       = models.CharField(max_length=200)
    description = models.TextField()
    category    = models.CharField(max_length=20, choices=CAT_CHOICES, default='other')
    event_date  = models.DateField()
    event_time  = models.TimeField(null=True, blank=True)
    venue       = models.CharField(max_length=300)
    pincode     = models.CharField(max_length=10, blank=True)
    image       = models.ImageField(upload_to='community_events/', blank=True, null=True)
    is_active   = models.BooleanField(default=True)
    deleted_at  = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['event_date']

    def __str__(self):
        return self.title

    def going_count(self):
        return self.rsvps.filter(status='going').count()

    def interested_count(self):
        return self.rsvps.filter(status='interested').count()

    def comment_count(self):
        return self.comments.count()


class EventRSVP(models.Model):
    STATUS_CHOICES = [('going', 'Going'), ('interested', 'Interested')]
    user   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_rsvps')
    event  = models.ForeignKey(CommunityEvent, on_delete=models.CASCADE, related_name='rsvps')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES)

    class Meta:
        unique_together = ('user', 'event')


class EventComment(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    event      = models.ForeignKey(CommunityEvent, on_delete=models.CASCADE, related_name='comments')
    text       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


# ── VOLUNTEER ACTIVITIES ───────────────────────────────────────────────────────
class VolunteerActivity(models.Model):
    CAT_CHOICES = [
        ('blood',      'Blood Donation'),
        ('tree',       'Tree Plantation'),
        ('health',     'Health Camp'),
        ('education',  'Education Drive'),
        ('cleanup',    'Cleanup Drive'),
        ('food',       'Food Drive'),
        ('other',      'Other'),
    ]
    posted_by        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='volunteer_posts')
    title            = models.CharField(max_length=200)
    description      = models.TextField()
    category         = models.CharField(max_length=20, choices=CAT_CHOICES, default='other')
    activity_date    = models.DateField()
    activity_time    = models.TimeField(null=True, blank=True)
    venue            = models.CharField(max_length=300)
    volunteers_needed = models.PositiveSmallIntegerField(default=0)
    contact          = models.CharField(max_length=100, blank=True)
    pincode          = models.CharField(max_length=10, blank=True)
    image            = models.ImageField(upload_to='volunteer/', blank=True, null=True)
    is_active        = models.BooleanField(default=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['activity_date']

    def __str__(self):
        return self.title

    def volunteer_count(self):
        return self.signups.count()

    def comment_count(self):
        return self.comments.count()


class VolunteerSignup(models.Model):
    user     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='volunteer_signups')
    activity = models.ForeignKey(VolunteerActivity, on_delete=models.CASCADE, related_name='signups')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'activity')


class VolunteerComment(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    activity   = models.ForeignKey(VolunteerActivity, on_delete=models.CASCADE, related_name='comments')
    text       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


# ── BUSINESS STORIES ───────────────────────────────────────────────────────────
class BusinessStory(models.Model):
    CAT_CHOICES = [
        ('startup',  'Startup Journey'),
        ('family',   'Family Business'),
        ('comeback', 'Comeback Story'),
        ('milestone','Milestone'),
        ('lesson',   'Lesson Learned'),
        ('other',    'Other'),
    ]
    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='business_stories')
    business_name  = models.CharField(max_length=200)
    years          = models.PositiveSmallIntegerField(null=True, blank=True, help_text='Years in business')
    category       = models.CharField(max_length=20, choices=CAT_CHOICES, default='other')
    title          = models.CharField(max_length=200)
    content        = models.TextField()
    image          = models.ImageField(upload_to='business_stories/', blank=True, null=True)
    pincode        = models.CharField(max_length=10, blank=True)
    is_active      = models.BooleanField(default=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.business_name} — {self.title}"

    def like_count(self):
        return self.likes.count()

    def comment_count(self):
        return self.comments.count()


class BusinessStoryLike(models.Model):
    user  = models.ForeignKey(User, on_delete=models.CASCADE)
    story = models.ForeignKey(BusinessStory, on_delete=models.CASCADE, related_name='likes')

    class Meta:
        unique_together = ('user', 'story')


class BusinessStoryComment(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    story      = models.ForeignKey(BusinessStory, on_delete=models.CASCADE, related_name='comments')
    text       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


# ── HALL OF FAME ───────────────────────────────────────────────────────────────
class HallOfFameEntry(models.Model):
    CAT_CHOICES = [
        ('academics',  'Academics'),
        ('sports',     'Sports'),
        ('arts',       'Arts & Culture'),
        ('social',     'Social Service'),
        ('business',   'Business'),
        ('other',      'Other'),
    ]
    nominated_by   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hof_nominations')
    nominee_name   = models.CharField(max_length=150)
    category       = models.CharField(max_length=20, choices=CAT_CHOICES, default='other')
    achievement    = models.CharField(max_length=300)
    description    = models.TextField()
    year           = models.PositiveSmallIntegerField()
    image          = models.ImageField(upload_to='hall_of_fame/', blank=True, null=True)
    pincode        = models.CharField(max_length=10, blank=True)
    is_active      = models.BooleanField(default=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-year', '-created_at']

    def __str__(self):
        return f"{self.nominee_name} — {self.year}"

    def vote_count(self):
        return self.votes.count()

    def comment_count(self):
        return self.comments.count()


class HallOfFameVote(models.Model):
    user  = models.ForeignKey(User, on_delete=models.CASCADE)
    entry = models.ForeignKey(HallOfFameEntry, on_delete=models.CASCADE, related_name='votes')

    class Meta:
        unique_together = ('user', 'entry')


class HallOfFameComment(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    entry      = models.ForeignKey(HallOfFameEntry, on_delete=models.CASCADE, related_name='comments')
    text       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


# ── MARKETPLACE ────────────────────────────────────────────────────────────────
class MarketplaceListing(models.Model):
    CAT_CHOICES = [
        ('electronics',  'Electronics'),
        ('furniture',    'Furniture'),
        ('clothing',     'Clothing & Accessories'),
        ('books',        'Books & Stationery'),
        ('vehicles',     'Vehicles'),
        ('appliances',   'Home Appliances'),
        ('sports',       'Sports & Fitness'),
        ('toys',         'Toys & Baby'),
        ('food',         'Food & Groceries'),
        ('services',     'Services'),
        ('other',        'Other'),
    ]
    CONDITION_CHOICES = [
        ('new',       'Brand New'),
        ('like_new',  'Like New'),
        ('good',      'Good'),
        ('fair',      'Fair'),
        ('for_parts', 'For Parts'),
    ]
    TYPE_CHOICES = [
        ('sell',    'For Sale'),
        ('rent',    'For Rent'),
        ('free',    'Free / Giveaway'),
        ('wanted',  'Wanted'),
    ]
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='listings')
    title        = models.CharField(max_length=200)
    category     = models.CharField(max_length=20, choices=CAT_CHOICES, default='other')
    listing_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='sell')
    condition    = models.CharField(max_length=10, choices=CONDITION_CHOICES, default='good', blank=True)
    price        = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description  = models.TextField()
    image        = models.ImageField(upload_to='marketplace/', blank=True, null=True)
    pincode      = models.CharField(max_length=10, blank=True)
    contact      = models.CharField(max_length=20, blank=True)
    is_sold      = models.BooleanField(default=False)
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def interest_count(self):
        return self.interests.count()

    def comment_count(self):
        return self.mp_comments.count()


class ListingInterest(models.Model):
    user    = models.ForeignKey(User, on_delete=models.CASCADE)
    listing = models.ForeignKey(MarketplaceListing, on_delete=models.CASCADE, related_name='interests')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'listing')


class ListingComment(models.Model):
    user    = models.ForeignKey(User, on_delete=models.CASCADE)
    listing = models.ForeignKey(MarketplaceListing, on_delete=models.CASCADE, related_name='mp_comments')
    text    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


# ── COMMUNITY WATCH ────────────────────────────────────────────────────────────
class WatchReport(models.Model):
    CAT_CHOICES = [
        ('theft',      'Theft / Robbery'),
        ('suspicious', 'Suspicious Activity'),
        ('hazard',     'Safety Hazard'),
        ('lost_found', 'Lost & Found'),
        ('noise',      'Noise / Nuisance'),
        ('stray',      'Stray Animals'),
        ('infra',      'Infrastructure Issue'),
        ('other',      'Other'),
    ]
    SEVERITY_CHOICES = [
        ('low',    'Low'),
        ('medium', 'Medium'),
        ('high',   'High / Urgent'),
    ]
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watch_reports')
    category    = models.CharField(max_length=20, choices=CAT_CHOICES, default='other')
    severity    = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    title       = models.CharField(max_length=200)
    description = models.TextField()
    location    = models.CharField(max_length=200, blank=True)
    pincode     = models.CharField(max_length=10, blank=True)
    image       = models.ImageField(upload_to='watch/', blank=True, null=True)
    is_resolved = models.BooleanField(default=False)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def confirm_count(self):
        return self.confirmations.count()

    def comment_count(self):
        return self.watch_comments.count()


class WatchConfirm(models.Model):
    user   = models.ForeignKey(User, on_delete=models.CASCADE)
    report = models.ForeignKey(WatchReport, on_delete=models.CASCADE, related_name='confirmations')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'report')


class WatchComment(models.Model):
    user    = models.ForeignKey(User, on_delete=models.CASCADE)
    report  = models.ForeignKey(WatchReport, on_delete=models.CASCADE, related_name='watch_comments')
    text    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


# ── NOTIFICATIONS ──────────────────────────────────────────────────────────────
class Notification(models.Model):
    TYPE_CHOICES = [
        ('like',     'Like'),
        ('comment',  'Comment'),
        ('confirm',  'Confirm'),
        ('rsvp',     'RSVP'),
        ('signup',   'Signup'),
        ('vote',     'Vote'),
        ('interest', 'Interest'),
        ('follow',   'Follow'),
        ('system',   'System'),
    ]
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_notifications')
    notif_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='system')
    actor_name = models.CharField(max_length=100, blank=True)
    message    = models.CharField(max_length=300)
    link       = models.CharField(max_length=300, blank=True)
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class FamilySetup(models.Model):
    is_public = models.BooleanField(default=False)
    GENDER_CHOICES = [('male', 'Male'), ('female', 'Female')]
    MARITAL_CHOICES = [('married', 'Married'), ('unmarried', 'Unmarried')]

    user             = models.OneToOneField(User, on_delete=models.CASCADE, related_name='family_setup')

    # Family house name
    house_name      = models.CharField(max_length=150, blank=True)

    # Family account credentials (separate login)
    family_email    = models.EmailField(unique=True, null=True, blank=True)
    family_password = models.CharField(max_length=128, blank=True)  # hashed

    # Step 2 — gender & marital status
    gender           = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    marital_status   = models.CharField(max_length=12, choices=MARITAL_CHOICES, blank=True)

    # Step 4 — self details
    self_full_name   = models.CharField(max_length=150, blank=True)
    self_dob         = models.DateField(null=True, blank=True)
    self_village     = models.CharField(max_length=150, blank=True)
    self_occupation  = models.CharField(max_length=150, blank=True)
    self_photo       = models.ImageField(upload_to='family/self/', blank=True, null=True)

    # Step 5 — partner details (if married)
    partner_full_name  = models.CharField(max_length=150, blank=True)
    partner_gender     = models.CharField(max_length=10, blank=True)
    partner_dob        = models.DateField(null=True, blank=True)
    partner_village    = models.CharField(max_length=150, blank=True)
    partner_occupation = models.CharField(max_length=150, blank=True)
    partner_photo      = models.ImageField(upload_to='family/partner/', blank=True, null=True)
    partner_email      = models.EmailField(blank=True)
    partner_password   = models.CharField(max_length=128, blank=True)

    # Legacy fields kept for backward compat
    spouse_name      = models.CharField(max_length=150, blank=True)
    display_name     = models.CharField(max_length=150, blank=True)
    village          = models.CharField(max_length=150, blank=True)
    age              = models.PositiveSmallIntegerField(null=True, blank=True)
    setup_done       = models.BooleanField(default=False)
    # counts — husband's side
    grandfather_count = models.PositiveSmallIntegerField(default=0)
    grandmother_count = models.PositiveSmallIntegerField(default=0)
    father_count      = models.PositiveSmallIntegerField(default=0)
    mother_count      = models.PositiveSmallIntegerField(default=0)
    son_count         = models.PositiveSmallIntegerField(default=0)
    daughter_count    = models.PositiveSmallIntegerField(default=0)
    uncle_count       = models.PositiveSmallIntegerField(default=0)
    aunt_count        = models.PositiveSmallIntegerField(default=0)
    cousin_count      = models.PositiveSmallIntegerField(default=0)
    brother_count     = models.PositiveSmallIntegerField(default=0)
    sister_count      = models.PositiveSmallIntegerField(default=0)
    pet_count         = models.PositiveSmallIntegerField(default=0)
    # counts — wife's side (only relevant when married)
    w_grandfather_count = models.PositiveSmallIntegerField(default=0)
    w_grandmother_count = models.PositiveSmallIntegerField(default=0)
    w_father_count      = models.PositiveSmallIntegerField(default=0)
    w_mother_count      = models.PositiveSmallIntegerField(default=0)
    w_uncle_count       = models.PositiveSmallIntegerField(default=0)
    w_aunt_count        = models.PositiveSmallIntegerField(default=0)
    w_cousin_count      = models.PositiveSmallIntegerField(default=0)
    w_brother_count     = models.PositiveSmallIntegerField(default=0)
    w_sister_count      = models.PositiveSmallIntegerField(default=0)
    updated_at        = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s family setup"

    def as_list(self):
        return [
            ('grandfather', 'Grandfather', '👴', self.grandfather_count),
            ('grandmother', 'Grandmother', '👵', self.grandmother_count),
            ('father',      'Father',      '👨', self.father_count),
            ('mother',      'Mother',      '👩', self.mother_count),
            ('son',         'Son',         '👦', self.son_count),
            ('daughter',    'Daughter',    '👧', self.daughter_count),
            ('uncle',       'Uncle',       '🧔', self.uncle_count),
            ('aunt',        'Aunt',        '👩‍🦳', self.aunt_count),
            ('cousin',      'Cousin',      '🧑', self.cousin_count),
            ('brother',     'Brother',     '👱', self.brother_count),
            ('sister',      'Sister',      '👱‍♀️', self.sister_count),
            ('pet',         'Pet',         '🐾', self.pet_count),
        ]


class FamilyMember(models.Model):
    SIDE_CHOICES = [
        ('husband', 'Husband Side'),
        ('wife',    'Wife Side'),
    ]
    TYPE_CHOICES = [
        ('grandfather', 'Grandfather'),
        ('grandmother', 'Grandmother'),
        ('father',      'Father'),
        ('mother',      'Mother'),
        ('son',         'Son'),
        ('daughter',    'Daughter'),
        ('uncle',       'Uncle'),
        ('aunt',        'Aunt'),
        ('cousin',      'Cousin'),
        ('brother',     'Brother'),
        ('sister',      'Sister'),
        ('friend',      'Friend'),
        ('colleague',   'Colleague'),
        ('pet',         'Pet / Animal'),
        ('other',       'Other'),
    ]
    STATUS_CHOICES = [
        ('living', 'Living'),
        ('passed', 'Passed Away'),
    ]

    creator     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='family_members')
    member_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    side        = models.CharField(max_length=10, choices=SIDE_CHOICES, default='husband', blank=True)
    name        = models.CharField(max_length=150)
    why         = models.CharField(max_length=300, blank=True)
    photo       = models.ImageField(upload_to='family_members/', blank=True, null=True)
    description = models.CharField(max_length=300, blank=True)
    about       = models.TextField(blank=True)

    dob         = models.DateField(blank=True, null=True)
    age         = models.PositiveIntegerField(blank=True, null=True)
    village     = models.CharField(max_length=150, blank=True)
    house_name  = models.CharField(max_length=150, blank=True)
    GENDER_CHOICES = [('male','Male'),('female','Female'),('other','Other')]
    gender      = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    occupation  = models.CharField(max_length=150, blank=True)
    education   = models.CharField(max_length=150, blank=True)
    phone       = models.CharField(max_length=20, blank=True)
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES, default='living')
    death_date  = models.DateField(blank=True, null=True)

    species     = models.CharField(max_length=100, blank=True)
    breed       = models.CharField(max_length=100, blank=True)

    # For children aged 18+ — give them a family login
    child_email       = models.EmailField(blank=True)
    child_password    = models.CharField(max_length=128, blank=True)  # hashed
    child_linked_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='family_child_profile'
    )

    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_member_type_display()})"


# ── BIRTHDAY NOTIFICATION LOG ──────────────────────────────────────────────────
class BirthdayNotificationLog(models.Model):
    """Idempotency guard — one row per (user, dob_owner_key, year, notif_type)."""
    NOTIF_TYPES = [('reminder', 'Reminder'), ('today', 'Today')]
    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='birthday_notif_logs')
    family_member = models.ForeignKey('FamilyMember', null=True, blank=True, on_delete=models.SET_NULL)
    # 'self' | 'partner' | str(FamilyMember.pk)
    dob_owner_key = models.CharField(max_length=20)
    year          = models.PositiveIntegerField()
    notif_type    = models.CharField(max_length=10, choices=NOTIF_TYPES)
    sent_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'dob_owner_key', 'year', 'notif_type')]

    def __str__(self):
        return f"{self.user} | {self.dob_owner_key} | {self.year} | {self.notif_type}"


class FamilyFlick(models.Model):
    creator    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='family_flicks')
    photo      = models.ImageField(upload_to='family_flicks/', blank=True, null=True)
    video      = models.FileField(upload_to='family_flick_videos/', blank=True, null=True)
    caption    = models.CharField(max_length=300, blank=True)
    event_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class FamilyPost(models.Model):
    creator   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='family_posts')
    text      = models.TextField()
    photo     = models.ImageField(upload_to='family_post_photos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class CommunityEventUserRating(models.Model):
    event   = models.ForeignKey(CommunityEvent, on_delete=models.CASCADE, related_name='user_ratings')
    rater   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_event_user_ratings')
    ratee   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_event_user_ratings')
    rating  = models.PositiveSmallIntegerField()  # 1-5
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'rater', 'ratee')
