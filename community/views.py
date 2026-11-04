from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.http import Http404
from .models import LocalHero, LocalHeroLike, LocalHeroComment, VolunteerActivity, VolunteerSignup, VolunteerComment, BusinessStory, BusinessStoryLike, BusinessStoryComment, HallOfFameEntry, HallOfFameVote, HallOfFameComment, MarketplaceListing, ListingInterest, ListingComment, WatchReport, WatchConfirm, WatchComment, Notification

MODULES = [
    {'slug': 'local-heroes',        'icon': '🦸', 'name': 'Local Heroes',           'desc': 'Celebrate unsung heroes in your community',           'color': '#dc2626', 'soon': False},
    {'slug': 'volunteer',           'icon': '🤝', 'name': 'Volunteer Activities',   'desc': 'Blood donation, tree plantation & health camps',      'color': '#16a34a', 'soon': False},
    {'slug': 'business-stories',    'icon': '🏪', 'name': 'Business Stories',       'desc': 'Local business journeys — not ads, real stories',     'color': '#ea580c', 'soon': False},
    {'slug': 'community-watch',     'icon': '👁️', 'name': 'Community Watch',        'desc': 'Report, block & keep the community safe',             'color': '#374151', 'soon': False},
]

CAT_ICONS = {
    'birthday':    '🎂',
    'achievement': '🏅',
    'tradition':   '🎎',
    'celebration': '🎉',
    'vacation':    '✈️',
    'gardening':   '🌱',
    'other':       '📸',
}

CAT_LABELS = {
    'birthday':    'Birthday',
    'achievement': 'Achievement',
    'tradition':   'Tradition',
    'celebration': 'Celebration',
    'vacation':    'Vacation',
    'gardening':   'Gardening',
    'other':       'Other',
}


# ── COMMUNITY HUB ──────────────────────────────────────────────────────────────
def hub(request):
    return render(request, 'community/hub.html', {'modules': MODULES})


def module_page(request, slug):
    module = next((m for m in MODULES if m['slug'] == slug), None)
    if not module:
        raise Http404
    return redirect('/community/' + module['slug'] + '/')


# ── SCHOOL & KIDS HUB ──────────────────────────────────────────────────────────


# ── SCHOOL CORNER ──────────────────────────────────────────────────────────────

POST_TYPE_ICONS = {
    'annual_day':   '🎭',
    'sports_day':   '⚽',
    'science_fair': '🔬',
    'admission':    '📋',
    'achievement':  '🏆',
    'event':        '📅',
    'announcement': '📢',
    'other':        '📌',
}


def _require_super_admin(request):
    from django.http import HttpResponseForbidden
    if not request.user.is_authenticated or getattr(request.user, 'admin_role', None) != 'super_admin':
        return HttpResponseForbidden('Super admin only.')
    return None


# ── STUDENT SUCCESS ────────────────────────────────────────────────────────────
SS_CAT_ICONS = {
    'academics':   '📚',
    'sports':      '⚽',
    'arts':        '🎨',
    'music':       '🎵',
    'scholarship': '🏅',
    'competition': '🏆',
    'other':       '🎓',
}

SS_CAT_LABELS = {
    'academics':   'Academics',
    'sports':      'Sports',
    'arts':        'Arts',
    'music':       'Music',
    'scholarship': 'Scholarship',
    'competition': 'Competition',
    'other':       'Other',
}


# ── KIDS CORNER ────────────────────────────────────────────────────────────────
KIDS_TYPE_ICONS = {
    'story':    '📖',
    'drawing':  '🎨',
    'craft':    '✂️',
    'poem':     '✍️',
    'joke':     '😄',
    'activity': '🎯',
    'other':    '🧒',
}


# ── PARENTING ──────────────────────────────────────────────────────────────────
PT_CAT_ICONS = {
    'tips':      '💡',
    'activity':  '🎯',
    'health':    '🏥',
    'education': '📚',
    'food':      '🥗',
    'emotion':   '💛',
    'other':     '👨‍👩‍👧',
}


# ── GRANDPARENTS ARCHIVE ───────────────────────────────────────────────────────
GP_CAT_ICONS = {
    'memory':    '🕰️',
    'wisdom':    '📜',
    'recipe':    '🍲',
    'tradition': '🎎',
    'history':   '🏛️',
    'other':     '👴',
}


# ── LOCAL HEROES ───────────────────────────────────────────────────────────────
LH_CAT_ICONS = {
    'social':      '🤝',
    'environment': '🌿',
    'education':   '📚',
    'health':      '🏥',
    'sports':      '🏅',
    'arts':        '🎨',
    'other':       '🦸',
}


def local_heroes_feed(request):
    cat   = request.GET.get('cat', '')
    heroes = LocalHero.objects.filter(is_active=True).select_related('posted_by')
    if cat:
        heroes = heroes.filter(category=cat)
    liked_ids = set()
    if request.user.is_authenticated:
        liked_ids = set(LocalHeroLike.objects.filter(
            user=request.user).values_list('hero_id', flat=True))
    return render(request, 'community/local_heroes.html', {
        'heroes':     heroes,
        'liked_ids':  liked_ids,
        'active_cat': cat,
        'cat_icons':  LH_CAT_ICONS,
        'categories': LocalHero.CAT_CHOICES,
    })


@login_required
def local_hero_post(request):
    if request.method == 'POST':
        title     = request.POST.get('title', '').strip()
        content   = request.POST.get('content', '').strip()
        category  = request.POST.get('category', 'social')
        hero_name = request.POST.get('hero_name', '').strip()
        image     = request.FILES.get('image')
        pincode   = getattr(request.user, 'pincode', '') or ''
        if title and content and hero_name:
            LocalHero.objects.create(
                posted_by=request.user, title=title, content=content,
                category=category, hero_name=hero_name,
                image=image, pincode=pincode,
            )
            messages.success(request, 'Hero story published!')
            return redirect('/community/local-heroes/')
    return render(request, 'community/local_hero_post.html', {
        'cat_icons':  LH_CAT_ICONS,
        'categories': LocalHero.CAT_CHOICES,
    })


def local_hero_detail(request, pk):
    hero     = get_object_or_404(LocalHero, pk=pk, is_active=True)
    comments = hero.comments.select_related('user').all()
    liked    = (request.user.is_authenticated and
                LocalHeroLike.objects.filter(user=request.user, hero=hero).exists())
    if request.method == 'POST' and request.user.is_authenticated:
        text = request.POST.get('comment', '').strip()
        if text:
            LocalHeroComment.objects.create(user=request.user, hero=hero, text=text)
        return redirect(f'/community/local-heroes/{pk}/')
    return render(request, 'community/local_hero_detail.html', {
        'hero':      hero,
        'comments':  comments,
        'liked':     liked,
        'cat_icons': LH_CAT_ICONS,
    })


@login_required
def local_hero_like(request, pk):
    hero = get_object_or_404(LocalHero, pk=pk)
    like, created = LocalHeroLike.objects.get_or_create(user=request.user, hero=hero)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
    return JsonResponse({'liked': liked, 'count': hero.like_count()})


@login_required
def local_hero_delete(request, pk):
    hero = get_object_or_404(LocalHero, pk=pk, posted_by=request.user)
    hero.delete()
    return redirect('/community/local-heroes/')


# ── COMMUNITY EVENTS ───────────────────────────────────────────────────────────
import datetime

EV_CAT_ICONS = {
    'festival':  '🎉',
    'sports':    '⚽',
    'cultural':  '🎭',
    'health':    '🏥',
    'education': '📚',
    'religious': '🕌',
    'cleanup':   '🧹',
    'other':     '📅',
}


# ── VOLUNTEER ACTIVITIES ───────────────────────────────────────────────────────
VOL_CAT_ICONS = {
    'blood':     '🩸',
    'tree':      '🌳',
    'health':    '🏥',
    'education': '📚',
    'cleanup':   '🧹',
    'food':      '🍱',
    'other':     '🤝',
}


def volunteer_feed(request):
    cat        = request.GET.get('cat', '')
    today      = datetime.date.today()
    activities = VolunteerActivity.objects.filter(is_active=True, activity_date__gte=today)
    if cat:
        activities = activities.filter(category=cat)
    my_signups = set()
    if request.user.is_authenticated:
        my_signups = set(VolunteerSignup.objects.filter(
            user=request.user).values_list('activity_id', flat=True))
    return render(request, 'community/volunteer.html', {
        'activities': activities,
        'my_signups': my_signups,
        'active_cat': cat,
        'cat_icons':  VOL_CAT_ICONS,
        'categories': VolunteerActivity.CAT_CHOICES,
        'today':      today,
    })


@login_required
def volunteer_post(request):
    if request.method == 'POST':
        title    = request.POST.get('title', '').strip()
        desc     = request.POST.get('description', '').strip()
        category = request.POST.get('category', 'other')
        act_date = request.POST.get('activity_date', '')
        act_time = request.POST.get('activity_time', '') or None
        venue    = request.POST.get('venue', '').strip()
        needed   = request.POST.get('volunteers_needed', '0')
        contact  = request.POST.get('contact', '').strip()
        image    = request.FILES.get('image')
        pincode  = getattr(request.user, 'pincode', '') or ''
        if title and desc and act_date and venue:
            VolunteerActivity.objects.create(
                posted_by=request.user, title=title, description=desc,
                category=category, activity_date=act_date, activity_time=act_time,
                venue=venue, volunteers_needed=int(needed) if needed.isdigit() else 0,
                contact=contact, image=image, pincode=pincode,
            )
            messages.success(request, 'Volunteer activity posted!')
            return redirect('/community/volunteer/')
    return render(request, 'community/volunteer_post.html', {
        'cat_icons':  VOL_CAT_ICONS,
        'categories': VolunteerActivity.CAT_CHOICES,
        'today':      datetime.date.today().isoformat(),
    })


def volunteer_detail(request, pk):
    activity = get_object_or_404(VolunteerActivity, pk=pk, is_active=True)
    comments = activity.comments.select_related('user').all()
    signed_up = (request.user.is_authenticated and
                 VolunteerSignup.objects.filter(user=request.user, activity=activity).exists())
    if request.method == 'POST' and request.user.is_authenticated:
        text = request.POST.get('comment', '').strip()
        if text:
            VolunteerComment.objects.create(user=request.user, activity=activity, text=text)
        return redirect(f'/community/volunteer/{pk}/')
    return render(request, 'community/volunteer_detail.html', {
        'activity':  activity,
        'comments':  comments,
        'signed_up': signed_up,
        'cat_icons': VOL_CAT_ICONS,
    })


@login_required
def volunteer_signup(request, pk):
    activity = get_object_or_404(VolunteerActivity, pk=pk)
    signup, created = VolunteerSignup.objects.get_or_create(user=request.user, activity=activity)
    if not created:
        signup.delete()
        signed_up = False
    else:
        signed_up = True
    return JsonResponse({'signed_up': signed_up, 'count': activity.volunteer_count()})


@login_required
def volunteer_delete(request, pk):
    activity = get_object_or_404(VolunteerActivity, pk=pk, posted_by=request.user)
    activity.delete()
    return redirect('/community/volunteer/')


# ── BUSINESS STORIES ───────────────────────────────────────────────────────────
BS_CAT_ICONS = {
    'startup':   '🚀',
    'family':    '🏠',
    'comeback':  '💪',
    'milestone': '🏆',
    'lesson':    '📖',
    'other':     '🏪',
}


def business_stories_feed(request):
    cat    = request.GET.get('cat', '')
    stories = BusinessStory.objects.filter(is_active=True).select_related('user')
    if cat:
        stories = stories.filter(category=cat)
    liked_ids = set()
    if request.user.is_authenticated:
        liked_ids = set(BusinessStoryLike.objects.filter(
            user=request.user).values_list('story_id', flat=True))
    return render(request, 'community/business_stories.html', {
        'stories':    stories,
        'liked_ids':  liked_ids,
        'active_cat': cat,
        'cat_icons':  BS_CAT_ICONS,
        'categories': BusinessStory.CAT_CHOICES,
    })


@login_required
def business_story_post(request):
    if request.method == 'POST':
        title         = request.POST.get('title', '').strip()
        content       = request.POST.get('content', '').strip()
        category      = request.POST.get('category', 'other')
        business_name = request.POST.get('business_name', '').strip()
        years         = request.POST.get('years', '').strip()
        image         = request.FILES.get('image')
        pincode       = getattr(request.user, 'pincode', '') or ''
        if title and content and business_name:
            BusinessStory.objects.create(
                user=request.user, title=title, content=content,
                category=category, business_name=business_name,
                years=int(years) if years.isdigit() else None,
                image=image, pincode=pincode,
            )
            messages.success(request, 'Business story shared!')
            return redirect('/community/business-stories/')
    return render(request, 'community/business_story_post.html', {
        'cat_icons':  BS_CAT_ICONS,
        'categories': BusinessStory.CAT_CHOICES,
    })


def business_story_detail(request, pk):
    story    = get_object_or_404(BusinessStory, pk=pk, is_active=True)
    comments = story.comments.select_related('user').all()
    liked    = (request.user.is_authenticated and
                BusinessStoryLike.objects.filter(user=request.user, story=story).exists())
    if request.method == 'POST' and request.user.is_authenticated:
        text = request.POST.get('comment', '').strip()
        if text:
            BusinessStoryComment.objects.create(user=request.user, story=story, text=text)
        return redirect(f'/community/business-stories/{pk}/')
    return render(request, 'community/business_story_detail.html', {
        'story':     story,
        'comments':  comments,
        'liked':     liked,
        'cat_icons': BS_CAT_ICONS,
    })


@login_required
def business_story_like(request, pk):
    story = get_object_or_404(BusinessStory, pk=pk)
    like, created = BusinessStoryLike.objects.get_or_create(user=request.user, story=story)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
    return JsonResponse({'liked': liked, 'count': story.like_count()})


@login_required
def business_story_delete(request, pk):
    story = get_object_or_404(BusinessStory, pk=pk, user=request.user)
    story.delete()
    return redirect('/community/business-stories/')


# ── HALL OF FAME ───────────────────────────────────────────────────────────────
import datetime as _dt

HOF_CAT_ICONS = {
    'academics': '📚',
    'sports':    '⚽',
    'arts':      '🎨',
    'social':    '🤝',
    'business':  '🏪',
    'other':     '🏆',
}


def hall_of_fame_feed(request):
    cat    = request.GET.get('cat', '')
    year   = request.GET.get('year', '')
    entries = HallOfFameEntry.objects.filter(is_active=True)
    if cat:
        entries = entries.filter(category=cat)
    if year:
        entries = entries.filter(year=year)

    voted_ids = set()
    if request.user.is_authenticated:
        voted_ids = set(HallOfFameVote.objects.filter(
            user=request.user).values_list('entry_id', flat=True))

    current_year = _dt.date.today().year
    years = list(range(current_year, current_year - 6, -1))

    return render(request, 'community/hall_of_fame.html', {
        'entries':      entries,
        'voted_ids':    voted_ids,
        'active_cat':   cat,
        'active_year':  year,
        'cat_icons':    HOF_CAT_ICONS,
        'categories':   HallOfFameEntry.CAT_CHOICES,
        'years':        years,
        'current_year': current_year,
    })


@login_required
def hall_of_fame_nominate(request):
    if request.method == 'POST':
        nominee_name = request.POST.get('nominee_name', '').strip()
        category     = request.POST.get('category', 'other')
        achievement  = request.POST.get('achievement', '').strip()
        description  = request.POST.get('description', '').strip()
        year         = request.POST.get('year', str(_dt.date.today().year))
        image        = request.FILES.get('image')
        pincode      = getattr(request.user, 'pincode', '') or ''
        if nominee_name and achievement and description:
            HallOfFameEntry.objects.create(
                nominated_by=request.user, nominee_name=nominee_name,
                category=category, achievement=achievement,
                description=description, year=int(year),
                image=image, pincode=pincode,
            )
            messages.success(request, f'{nominee_name} has been nominated!')
            return redirect('/community/hall-of-fame/')
    current_year = _dt.date.today().year
    return render(request, 'community/hall_of_fame_nominate.html', {
        'cat_icons':    HOF_CAT_ICONS,
        'categories':   HallOfFameEntry.CAT_CHOICES,
        'current_year': current_year,
        'years':        list(range(current_year, current_year - 4, -1)),
    })


def hall_of_fame_detail(request, pk):
    entry    = get_object_or_404(HallOfFameEntry, pk=pk, is_active=True)
    comments = entry.comments.select_related('user').all()
    voted    = (request.user.is_authenticated and
                HallOfFameVote.objects.filter(user=request.user, entry=entry).exists())
    if request.method == 'POST' and request.user.is_authenticated:
        text = request.POST.get('comment', '').strip()
        if text:
            HallOfFameComment.objects.create(user=request.user, entry=entry, text=text)
        return redirect(f'/community/hall-of-fame/{pk}/')
    return render(request, 'community/hall_of_fame_detail.html', {
        'entry':      entry,
        'comments':   comments,
        'voted':      voted,
        'vote_count': entry.vote_count(),
        'cat_icons':  HOF_CAT_ICONS,
    })


@login_required
def hall_of_fame_vote(request, pk):
    entry = get_object_or_404(HallOfFameEntry, pk=pk)
    vote, created = HallOfFameVote.objects.get_or_create(user=request.user, entry=entry)
    if not created:
        vote.delete()
        voted = False
    else:
        voted = True
    return JsonResponse({'voted': voted, 'count': entry.vote_count()})


# ── MARKETPLACE ────────────────────────────────────────────────────────────────
MP_CAT_ICONS = {
    'electronics': '📱', 'furniture': '🛋️', 'clothing': '👗', 'books': '📚',
    'vehicles': '🚗', 'appliances': '🏠', 'sports': '⚽', 'toys': '🧸',
    'food': '🥗', 'services': '🔧', 'other': '🛒',
}
MP_TYPE_ICONS = {
    'sell': '🏷️', 'rent': '🔑', 'free': '🎁', 'wanted': '🔍',
}


def marketplace_feed(request):
    cat  = request.GET.get('cat', '')
    ltype = request.GET.get('type', '')
    listings = MarketplaceListing.objects.filter(is_active=True)
    if cat:
        listings = listings.filter(category=cat)
    if ltype:
        listings = listings.filter(listing_type=ltype)
    interest_ids = set()
    if request.user.is_authenticated:
        interest_ids = set(ListingInterest.objects.filter(
            user=request.user).values_list('listing_id', flat=True))
    return render(request, 'community/marketplace.html', {
        'listings':     listings,
        'interest_ids': interest_ids,
        'active_cat':   cat,
        'active_type':  ltype,
        'cat_icons':    MP_CAT_ICONS,
        'type_icons':   MP_TYPE_ICONS,
        'categories':   MarketplaceListing.CAT_CHOICES,
        'types':        MarketplaceListing.TYPE_CHOICES,
    })


@login_required
def marketplace_post(request):
    if request.method == 'POST':
        listing_type = request.POST.get('listing_type', 'sell')
        price_raw    = request.POST.get('price', '').strip()
        price        = float(price_raw) if price_raw else None
        listing = MarketplaceListing.objects.create(
            user         = request.user,
            title        = request.POST['title'],
            category     = request.POST['category'],
            listing_type = listing_type,
            condition    = request.POST.get('condition', 'good') if listing_type != 'wanted' else '',
            price        = price,
            description  = request.POST['description'],
            pincode      = request.POST.get('pincode', ''),
            contact      = request.POST.get('contact', ''),
            image        = request.FILES.get('image'),
        )
        return redirect(f'/community/marketplace/{listing.pk}/')
    return render(request, 'community/marketplace_post.html', {
        'cat_icons':  MP_CAT_ICONS,
        'type_icons': MP_TYPE_ICONS,
        'categories': MarketplaceListing.CAT_CHOICES,
        'types':      MarketplaceListing.TYPE_CHOICES,
        'conditions': MarketplaceListing.CONDITION_CHOICES,
    })


def marketplace_detail(request, pk):
    listing  = get_object_or_404(MarketplaceListing, pk=pk, is_active=True)
    comments = listing.mp_comments.select_related('user').all()
    interested = (request.user.is_authenticated and
                  ListingInterest.objects.filter(user=request.user, listing=listing).exists())
    if request.method == 'POST' and request.user.is_authenticated:
        text = request.POST.get('comment', '').strip()
        if text:
            ListingComment.objects.create(user=request.user, listing=listing, text=text)
        return redirect(f'/community/marketplace/{pk}/')
    return render(request, 'community/marketplace_detail.html', {
        'listing':    listing,
        'comments':   comments,
        'interested': interested,
        'interest_count': listing.interest_count(),
        'cat_icons':  MP_CAT_ICONS,
        'type_icons': MP_TYPE_ICONS,
    })


@login_required
def marketplace_interest(request, pk):
    listing = get_object_or_404(MarketplaceListing, pk=pk)
    obj, created = ListingInterest.objects.get_or_create(user=request.user, listing=listing)
    if not created:
        obj.delete()
        interested = False
    else:
        interested = True
    return JsonResponse({'interested': interested, 'count': listing.interest_count()})


@login_required
def marketplace_sold(request, pk):
    listing = get_object_or_404(MarketplaceListing, pk=pk, user=request.user)
    listing.is_sold = not listing.is_sold
    listing.save()
    return JsonResponse({'sold': listing.is_sold})


@login_required
def marketplace_delete(request, pk):
    listing = get_object_or_404(MarketplaceListing, pk=pk, user=request.user)
    listing.is_active = False
    listing.save()
    return redirect('/community/marketplace/')


# ── COMMUNITY WATCH ────────────────────────────────────────────────────────────
WATCH_CAT_ICONS = {
    'theft':      '🚨', 'suspicious': '👁️', 'hazard': '⚠️',
    'lost_found': '🔍', 'noise':      '📢', 'stray':  '🐕',
    'infra':      '🏗️', 'other':      '📋',
}
SEVERITY_COLORS = {
    'low':    '#16a34a',
    'medium': '#d97706',
    'high':   '#dc2626',
}


def watch_feed(request):
    cat      = request.GET.get('cat', '')
    severity = request.GET.get('sev', '')
    reports  = WatchReport.objects.filter(is_active=True)
    if cat:
        reports = reports.filter(category=cat)
    if severity:
        reports = reports.filter(severity=severity)
    confirm_ids = set()
    if request.user.is_authenticated:
        confirm_ids = set(WatchConfirm.objects.filter(
            user=request.user).values_list('report_id', flat=True))
    return render(request, 'community/community_watch.html', {
        'reports':      reports,
        'confirm_ids':  confirm_ids,
        'active_cat':   cat,
        'active_sev':   severity,
        'cat_icons':    WATCH_CAT_ICONS,
        'sev_colors':   SEVERITY_COLORS,
        'categories':   WatchReport.CAT_CHOICES,
        'severities':   WatchReport.SEVERITY_CHOICES,
    })


@login_required
def watch_post(request):
    if request.method == 'POST':
        report = WatchReport.objects.create(
            user        = request.user,
            category    = request.POST['category'],
            severity    = request.POST.get('severity', 'medium'),
            title       = request.POST['title'],
            description = request.POST['description'],
            location    = request.POST.get('location', ''),
            pincode     = request.POST.get('pincode', ''),
            image       = request.FILES.get('image'),
        )
        return redirect(f'/community/community-watch/{report.pk}/')
    return render(request, 'community/watch_post.html', {
        'cat_icons':  WATCH_CAT_ICONS,
        'categories': WatchReport.CAT_CHOICES,
        'severities': WatchReport.SEVERITY_CHOICES,
        'sev_colors': SEVERITY_COLORS,
    })


def watch_detail(request, pk):
    report   = get_object_or_404(WatchReport, pk=pk, is_active=True)
    comments = report.watch_comments.select_related('user').all()
    confirmed = (request.user.is_authenticated and
                 WatchConfirm.objects.filter(user=request.user, report=report).exists())
    if request.method == 'POST' and request.user.is_authenticated:
        text = request.POST.get('comment', '').strip()
        if text:
            WatchComment.objects.create(user=request.user, report=report, text=text)
        return redirect(f'/community/community-watch/{pk}/')
    return render(request, 'community/watch_detail.html', {
        'report':         report,
        'comments':       comments,
        'confirmed':      confirmed,
        'confirm_count':  report.confirm_count(),
        'cat_icons':      WATCH_CAT_ICONS,
        'sev_colors':     SEVERITY_COLORS,
    })


@login_required
def watch_confirm(request, pk):
    report = get_object_or_404(WatchReport, pk=pk)
    obj, created = WatchConfirm.objects.get_or_create(user=request.user, report=report)
    if not created:
        obj.delete()
        confirmed = False
    else:
        confirmed = True
    return JsonResponse({'confirmed': confirmed, 'count': report.confirm_count()})


@login_required
def watch_resolve(request, pk):
    report = get_object_or_404(WatchReport, pk=pk, user=request.user)
    report.is_resolved = not report.is_resolved
    report.save()
    return JsonResponse({'resolved': report.is_resolved})


@login_required
def watch_delete(request, pk):
    report = get_object_or_404(WatchReport, pk=pk, user=request.user)
    report.is_active = False
    report.save()
    return redirect('/community/community-watch/')


# ── NOTIFICATIONS & SEARCH ─────────────────────────────────────────────────────
NOTIF_ICONS = {
    'like':     '❤️',  'comment':  '💬', 'confirm':  '🚨',
    'rsvp':     '📅',  'signup':   '🤝', 'vote':     '⭐',
    'interest': '🛒',  'follow':   '🏫', 'system':   '🔔',
}


@login_required
def notifications_page(request):
    notifs = Notification.objects.filter(user=request.user)
    unread_count = notifs.filter(is_read=False).count()
    notifs.filter(is_read=False).update(is_read=True)
    return render(request, 'community/notifications.html', {
        'notifs':       notifs[:50],
        'unread_count': unread_count,
        'notif_icons':  NOTIF_ICONS,
    })


@login_required
def notif_mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'ok': True})


def community_search(request):
    q       = request.GET.get('q', '').strip()
    pincode = request.GET.get('pincode', '').strip()
    results = []

    if q or pincode:
        from django.db.models import Q

        def _filter(qs, title_field, desc_field='description', pin_field='pincode'):
            f = Q()
            if q:
                f &= (Q(**{f'{title_field}__icontains': q}) |
                      Q(**{f'{desc_field}__icontains': q}))
            if pincode and pin_field:
                try:
                    f &= Q(**{f'{pin_field}__icontains': pincode})
                except Exception:
                    pass
            return qs.filter(f) if f else qs.none()

        # Local Heroes
        for s in _filter(LocalHero.objects.filter(is_active=True), 'name', 'story')[:5]:
            results.append({'type': 'Local Hero', 'icon': '🦸', 'title': s.name,
                            'desc': s.story[:80], 'url': f'/community/local-heroes/{s.pk}/',
                            'time': s.created_at})
        # Volunteer
        for s in _filter(VolunteerActivity.objects.filter(is_active=True), 'title')[:5]:
            results.append({'type': 'Volunteer', 'icon': '🤝', 'title': s.title,
                            'desc': s.description[:80], 'url': f'/community/volunteer/{s.pk}/',
                            'time': s.created_at})
        # Business Stories
        for s in _filter(BusinessStory.objects.filter(is_active=True), 'title', 'content')[:5]:
            results.append({'type': 'Business Story', 'icon': '🏪', 'title': s.title,
                            'desc': s.content[:80], 'url': f'/community/business-stories/{s.pk}/',
                            'time': s.created_at})
        # Hall of Fame
        for s in _filter(HallOfFameEntry.objects.filter(is_active=True), 'nominee_name', 'description')[:5]:
            results.append({'type': 'Hall of Fame', 'icon': '🏆', 'title': s.nominee_name,
                            'desc': s.description[:80], 'url': f'/community/hall-of-fame/{s.pk}/',
                            'time': s.created_at})
        # Marketplace
        for s in _filter(MarketplaceListing.objects.filter(is_active=True), 'title')[:5]:
            results.append({'type': 'Marketplace', 'icon': '🛒', 'title': s.title,
                            'desc': s.description[:80], 'url': f'/community/marketplace/{s.pk}/',
                            'time': s.created_at})
        # Watch
        for s in _filter(WatchReport.objects.filter(is_active=True), 'title', 'description', 'pincode')[:5]:
            results.append({'type': 'Community Watch', 'icon': '👁️', 'title': s.title,
                            'desc': s.description[:80], 'url': f'/community/community-watch/{s.pk}/',
                            'time': s.created_at})

        results.sort(key=lambda x: x['time'], reverse=True)

    return render(request, 'community/search.html', {
        'results': results,
        'q':       q,
        'pincode': pincode,
        'count':   len(results),
    })


# ── BIRTHDAY GIFT REDIRECT ─────────────────────────────────────────────────────
