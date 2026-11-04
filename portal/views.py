from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
User = get_user_model()
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.cache import never_cache

from .models import Category, Community, CommunityLeader, CommunityMember, Cause, CauseSupport, VolunteerRequest, Activity, ActivityPhoto, Post, PostLike, PostComment, ShortVideo, PortalNotification, Flick, FlickLike, FlickComment


def _notify(user, notif_type, message, link=''):
    PortalNotification.objects.create(user=user, notif_type=notif_type, message=message, link=link)


def _is_member(community, user):
    if not user.is_authenticated:
        return False
    return community.memberships.filter(user=user, status='approved').exists()


# ──────────────────────────────────────────────
# PUBLIC PAGES
# ──────────────────────────────────────────────

def portal_home(request):
    communities = Community.objects.filter(is_active=True, is_verified=True).order_by('-created_at')
    from jobs.account import selected_area
    pincode = selected_area(request)
    category = request.GET.get('category', '').strip()
    q = request.GET.get('q', '').strip()

    if pincode:
        communities = communities.filter(pincode__startswith=pincode)
    if category:
        communities = communities.filter(category__slug=category)
    if q:
        communities = communities.filter(Q(name__icontains=q) | Q(page_id__icontains=q) | Q(purpose__icontains=q))

    categories = Category.objects.all()
    return render(request, 'portal/home.html', {
        'communities': communities,
        'categories': categories,
        'pincode': pincode, 'category': category, 'q': q,
    })


def community_list(request):
    communities = Community.objects.filter(is_active=True, is_verified=True)
    q       = request.GET.get('q', '').strip()
    from jobs.account import selected_area
    pincode = selected_area(request)
    cat     = request.GET.get('category', '').strip()
    if q:
        communities = communities.filter(Q(name__icontains=q) | Q(page_id__icontains=q))
    if pincode:
        communities = communities.filter(pincode__startswith=pincode)
    if cat:
        communities = communities.filter(category__slug=cat)
    communities = communities.order_by('-created_at')
    return render(request, 'portal/community_list.html', {
        'communities': communities,
        'categories': Category.objects.all(),
        'q': q, 'pincode': pincode, 'selected_cat': cat,
    })


@never_cache
def community_page(request, page_id):
    community = get_object_or_404(Community, page_id=page_id, is_active=True)
    is_member  = _is_member(community, request.user)
    is_admin   = community.is_admin(request.user)
    membership = None
    if request.user.is_authenticated:
        membership = community.memberships.filter(user=request.user).first()

    posts      = community.posts.filter(is_active=True).order_by('-created_at')[:20]
    causes     = community.causes.filter(is_active=True).order_by('-created_at')[:5]
    activities = community.activities.filter(is_active=True).order_by('-date')[:5]
    videos     = community.videos.filter(is_active=True).order_by('-created_at')[:6]
    flicks     = community.flicks.filter(is_active=True).order_by('-created_at')[:6]
    leaders    = community.leaders.filter(status='accepted').order_by('role')
    members    = community.memberships.filter(status='approved').select_related('user').prefetch_related('user__seeker')[:12]

    # Gallery timeline — image posts grouped by year/month
    _MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    gallery_groups = []
    image_posts = community.posts.filter(is_active=True).exclude(image='').order_by('-event_date', '-created_at')
    _cur_ym = None
    _cur_grp = None
    _last_year = None
    for p in image_posts:
        d = p.event_date or p.created_at.date()
        ym = (d.year, d.month)
        if ym != _cur_ym:
            if _cur_grp:
                gallery_groups.append(_cur_grp)
            _cur_grp = {
                'year': d.year,
                'show_year': d.year != _last_year,
                'month_name': _MONTHS[d.month - 1],
                'count': 0,
                'items': [],
            }
            _last_year = d.year
            _cur_ym = ym
        _cur_grp['items'].append(p)
        _cur_grp['count'] += 1
    if _cur_grp:
        gallery_groups.append(_cur_grp)

    return render(request, 'portal/community_page.html', {
        'community': community, 'is_member': is_member,
        'is_admin': is_admin, 'membership': membership,
        'posts': posts, 'causes': causes,
        'activities': activities, 'videos': videos, 'flicks': flicks,
        'leaders': leaders, 'members': members,
        'gallery_groups': gallery_groups,
    })


def causes_list(request):
    causes = Cause.objects.filter(is_active=True).select_related('community').order_by('-created_at')
    q = request.GET.get('q', '')
    if q:
        causes = causes.filter(Q(name__icontains=q) | Q(description__icontains=q))
    return render(request, 'portal/causes_list.html', {'causes': causes, 'q': q})


def cause_detail(request, pk):
    cause    = get_object_or_404(Cause, pk=pk, is_active=True)
    supported = request.user.is_authenticated and CauseSupport.objects.filter(cause=cause, user=request.user).exists()
    return render(request, 'portal/cause_detail.html', {
        'cause': cause, 'supported': supported,
    })


def activities_list(request):
    activities = Activity.objects.filter(is_active=True).select_related('community').order_by('-date')
    q = request.GET.get('q', '')
    if q:
        activities = activities.filter(Q(name__icontains=q) | Q(location__icontains=q))
    return render(request, 'portal/activities_list.html', {'activities': activities, 'q': q})


def activity_detail(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    return render(request, 'portal/activity_detail.html', {'activity': activity})


def videos_list(request):
    videos = ShortVideo.objects.filter(is_active=True).select_related('community', 'uploader').order_by('-created_at')
    cat = request.GET.get('category', '')
    if cat:
        videos = videos.filter(category=cat)
    return render(request, 'portal/videos_list.html', {
        'videos': videos, 'cat': cat,
        'categories': ShortVideo.VIDEO_CATS,
    })


def portal_search(request):
    q = request.GET.get('q', '').strip()
    results = {}
    if q:
        results['communities'] = Community.objects.filter(
            Q(name__icontains=q) | Q(page_id__icontains=q) | Q(purpose__icontains=q),
            is_active=True, is_verified=True)[:8]
        results['causes']  = Cause.objects.filter(Q(name__icontains=q), is_active=True)[:6]
        results['activities'] = Activity.objects.filter(Q(name__icontains=q), is_active=True)[:6]
        results['videos']  = ShortVideo.objects.filter(Q(title__icontains=q), is_active=True)[:6]
    return render(request, 'portal/search.html', {'q': q, 'results': results})


# ──────────────────────────────────────────────
# COMMUNITY CREATE / EDIT
# ──────────────────────────────────────────────

@login_required
def create_community(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        p = request.POST

        # ── resolve creator account ──────────────────────────────
        if request.user.is_authenticated:
            creator = request.user
            full_name = p.get('full_name', '').strip()
            new_email = p.get('creator_email', '').strip().lower()
            new_pass  = p.get('creator_password', '').strip()
            if full_name:
                parts = full_name.split(' ', 1)
                creator.first_name = parts[0]
                creator.last_name  = parts[1] if len(parts) > 1 else ''
            if new_email and new_email != creator.email:
                if not User.objects.filter(email=new_email).exclude(pk=creator.pk).exists():
                    creator.email = new_email
            if new_pass:
                creator.set_password(new_pass)
            creator.save()
            if new_pass:
                from django.contrib.auth import login as auth_login
                auth_login(request, creator, backend='django.contrib.auth.backends.ModelBackend')
            if 'creator_photo' in request.FILES:
                from jobs.models import JobSeekerProfile
                profile, _ = JobSeekerProfile.objects.get_or_create(user=creator)
                profile.photo = request.FILES['creator_photo']
                profile.save(update_fields=['photo'])
        else:
            full_name = p.get('full_name', '').strip()
            email     = p.get('creator_email', '').strip().lower()
            password  = p.get('creator_password', '').strip()
            phone_c   = p.get('creator_phone', '').strip()

            # If phone matches an existing account, require login first
            if phone_c and User.objects.filter(phone=phone_c).exists():
                messages.error(request, 'An account with this phone number already exists. Please log in first, then create your community.')
                return redirect(f'/login/?next=/portal/community/create/')

            if not email or not password:
                messages.error(request, 'Email and password are required to create your account.')
                return render(request, 'portal/community_create.html', {'categories': categories})
            if User.objects.filter(email=email).exists():
                messages.error(request, 'An account with this email already exists. Please log in first.')
                return render(request, 'portal/community_create.html', {'categories': categories})

            base_uname = email.split('@')[0]
            username = base_uname
            n = 1
            while User.objects.filter(username=username).exists():
                username = f'{base_uname}{n}'; n += 1

            creator = User(username=username, email=email, user_type='individual')
            creator.set_password(password)
            if full_name:
                parts = full_name.split(' ', 1)
                creator.first_name = parts[0]
                creator.last_name  = parts[1] if len(parts) > 1 else ''
            if phone_c:
                creator.phone = phone_c
            creator.save()
            from django.contrib.auth import login as auth_login
            auth_login(request, creator, backend='django.contrib.auth.backends.ModelBackend')

        # save profile photo if provided
        if 'creator_photo' in request.FILES:
            from jobs.models import JobSeekerProfile
            profile, _ = JobSeekerProfile.objects.get_or_create(user=creator)
            profile.photo = request.FILES['creator_photo']
            profile.save(update_fields=['photo'])

        # ── create community ─────────────────────────────────────
        community = Community(
            name=p.get('name','').strip(),
            purpose=p.get('purpose','').strip(),
            description=p.get('description','').strip(),
            location=p.get('location','').strip(),
            pincode=p.get('pincode','').strip(),
            email=p.get('comm_email','').strip(),
            phone=p.get('comm_phone','').strip(),
            join_mode=p.get('join_mode','open'),
            created_by=creator,
        )
        cat_id = p.get('category')
        if cat_id:
            community.category_id = cat_id
        if 'logo' in request.FILES:
            community.logo = request.FILES['logo']
        if 'cover' in request.FILES:
            community.cover = request.FILES['cover']
        if getattr(request.user, 'admin_role', '') == 'super_admin':
            community.is_verified = True
        community.save()

        CommunityMember.objects.create(community=community, user=creator, status='approved', approved_at=timezone.now())
        CommunityLeader.objects.create(community=community, user=creator, role='president', status='accepted')

        messages.success(request, f'Community "{community.name}" created! Page ID: {community.page_id}')
        return redirect('portal_community', page_id=community.page_id)

    return render(request, 'portal/community_create.html', {'categories': categories})


def _notify_leader(leader, email, phone='', temp_password=''):
    try:
        accept_url = f"{settings.SITE_URL}/portal/leader/accept/{leader.token}/"
        login_url  = f"{settings.SITE_URL}/login/"
        community  = leader.community
        role_label = leader.get_role_display()
        msg = (
            f"Dear {leader.user.get_full_name() or leader.user.username},\n\n"
            f"You have been nominated as {role_label} of {community.name}.\n\n"
            f"Community   : {community.name} ({community.page_id})\n"
            f"Nominated by: {leader.nominated_by.get_full_name() or leader.nominated_by.username}\n"
        )
        if phone:
            msg += f"Phone       : {phone}\n"
        if temp_password:
            msg += (
                f"\nYour login credentials:\n"
                f"  Website  : {settings.SITE_URL}\n"
                f"  Email    : {email}\n"
                f"  Password : {temp_password}\n"
                f"  (Please change your password after first login)\n"
            )
        msg += f"\nClick below to accept your nomination:\n{accept_url}\n\nThank you,\nLocal From Team"
        send_mail(
            subject=f"Nomination: {role_label} — {community.name}",
            message=msg,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,
        )
    except Exception:
        pass


@login_required
def nominations_step(request, page_id):
    community = get_object_or_404(Community, page_id=page_id, created_by=request.user)
    errors = []

    if request.method == 'POST':
        action = request.POST.get('action', 'nominate')
        if action == 'skip':
            messages.info(request, 'You can add leaders later from the community dashboard.')
            return redirect('portal_community', page_id=community.page_id)

        email = request.POST.get('email', '').strip()
        role  = request.POST.get('role', 'president')

        if not email:
            errors.append('Please enter an email address.')
        else:
            try:
                nominee = User.objects.get(email=email)
            except User.DoesNotExist:
                nominee = None

            leader = CommunityLeader(
                community=community, role=role,
                nominated_by=request.user,
                user=nominee if nominee else request.user,
            )
            leader.save()
            leader.generate_token()
            _notify_leader(leader, email if not nominee else nominee.email)
            messages.success(request, f'Nomination sent to {email}.')
            return redirect('portal_nominations_step', page_id=community.page_id)

    leaders = community.leaders.select_related('user')
    roles   = CommunityLeader.ROLES
    return render(request, 'portal/nominations_step.html', {
        'community': community, 'leaders': leaders, 'roles': roles, 'errors': errors,
    })


def leader_accept(request, token):
    leader = get_object_or_404(CommunityLeader, token=token)
    if leader.status != 'pending':
        messages.info(request, f'This nomination has already been {leader.status}.')
        return redirect('portal_community', page_id=leader.community.page_id)

    action = request.GET.get('action', '')
    if action == 'accept':
        leader.status = 'accepted'
        leader.accepted_at = timezone.now()
        leader.save()
        # Also ensure they are a member
        CommunityMember.objects.get_or_create(
            community=leader.community, user=leader.user,
            defaults={'status': 'approved', 'approved_at': timezone.now()}
        )
        messages.success(request, f'You have accepted the role of {leader.get_role_display()} in {leader.community.name}!')
    elif action == 'decline':
        leader.status = 'declined'
        leader.save()
        messages.info(request, 'You have declined the nomination.')
    return render(request, 'portal/leader_accept.html', {'leader': leader, 'action': action})


# ──────────────────────────────────────────────
# JOIN COMMUNITY
# ──────────────────────────────────────────────

@login_required
def join_community(request, page_id):
    community = get_object_or_404(Community, page_id=page_id, is_active=True)
    existing  = community.memberships.filter(user=request.user).first()

    if existing:
        messages.info(request, f'Your membership status: {existing.get_status_display()}')
        return redirect('portal_community', page_id=page_id)

    user = request.user
    # Check if profile is complete
    try:
        profile = user.seeker
        has_photo = bool(profile.photo)
    except Exception:
        profile = None
        has_photo = False

    profile_incomplete = (
        not user.get_full_name().strip() or
        not user.pincode or
        not has_photo
    )

    if profile_incomplete and request.method != 'POST':
        return render(request, 'portal/join_profile.html', {
            'community': community,
            'user': user,
        })

    if request.method == 'POST':
        # Save profile details
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        pincode    = request.POST.get('pincode', '').strip()
        email      = request.POST.get('email', '').strip().lower()

        if first_name:
            user.first_name = first_name
            user.last_name  = last_name
        if pincode:
            user.pincode = pincode
        if email and not user.email:
            if not User.objects.filter(email=email).exclude(pk=user.pk).exists():
                user.email = email
        user.save(update_fields=['first_name', 'last_name', 'pincode', 'email'])

        # Save profile photo
        if 'photo' in request.FILES and profile:
            profile.photo = request.FILES['photo']
            profile.save(update_fields=['photo'])
        elif 'photo' in request.FILES and not profile:
            from jobs.models import JobSeekerProfile
            try:
                profile = JobSeekerProfile.objects.create(user=user)
                profile.photo = request.FILES['photo']
                profile.save()
            except Exception:
                pass

        # Re-check after saving — block join if still missing photo or pincode
        try:
            has_photo = bool(user.seeker.photo)
        except Exception:
            has_photo = False
        errors = []
        if not has_photo:
            errors.append('Please upload a profile photo.')
        if not user.pincode:
            errors.append('Please enter your pincode.')
        if not user.get_full_name().strip():
            errors.append('Please enter your full name.')
        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'portal/join_profile.html', {
                'community': community,
                'user': user,
            })

    status = 'approved' if community.join_mode == 'open' else 'pending'
    membership, created = CommunityMember.objects.get_or_create(
        community=community, user=request.user,
        defaults={'status': status, 'approved_at': timezone.now() if status == 'approved' else None},
    )
    if created and status == 'approved':
        _notify(request.user, 'join_approved', f'Welcome to {community.name}!', f'/portal/c/{page_id}/')
        messages.success(request, f'You joined {community.name}!')
    elif created:
        if community.created_by:
            _notify(community.created_by, 'join_request',
                    f'{request.user.get_full_name()} wants to join {community.name}.',
                    f'/portal/c/{page_id}/members/')
        messages.success(request, 'Join request sent. Awaiting admin approval.')

    return redirect('portal_community', page_id=page_id)


# ──────────────────────────────────────────────
# COMMUNITY ADMIN DASHBOARD
# ──────────────────────────────────────────────

@login_required
def community_dashboard(request, page_id):
    community = get_object_or_404(Community, page_id=page_id)
    if not community.is_admin(request.user):
        messages.error(request, 'Access denied.')
        return redirect('portal_community', page_id=page_id)

    return render(request, 'portal/community_dashboard.html', {
        'community': community,
        'can_manage_members': community.can_manage_members(request.user),
        'members_pending': community.memberships.filter(status='pending').count(),
        'members_approved': community.memberships.filter(status='approved').count(),
        'volunteers_pending': community.volunteer_requests.filter(status='pending').count(),
        'volunteers_approved': community.volunteer_requests.filter(status='approved').count(),
        'videos_count': community.videos.filter(is_active=True).count(),
        'posts_count': community.posts.filter(is_active=True).count(),
        'recent_requests': community.memberships.filter(status='pending').select_related('user')[:5],
        'recent_volunteers': community.volunteer_requests.filter(status='pending')[:5],
        'pending_flicks': community.flicks.filter(is_active=False).select_related('posted_by').order_by('-created_at'),
    })


def manage_members(request, page_id):
    community = get_object_or_404(Community, page_id=page_id, is_active=True)
    can_manage = community.can_manage_members(request.user)  # president / creator only
    is_admin   = can_manage  # controls template — only president gets admin view

    # Non-presidents (including VP/other role holders): read-only member list
    if not can_manage:
        memberships = community.memberships.filter(status='approved').select_related('user').prefetch_related('user__seeker').order_by('-joined_at')
        leader_map = {l.user_id: l for l in CommunityLeader.objects.filter(community=community, status='accepted')}
        memberships = list(memberships)
        for m in memberships:
            ldr = leader_map.get(m.user_id)
            m.current_role     = ldr.get_role_label() if ldr else ''
            m.current_role_key = ldr.role if ldr else ''
        return render(request, 'portal/manage_members.html', {
            'community': community, 'memberships': memberships,
            'status_filter': 'approved', 'is_admin': False, 'taken_roles': set(),
        })

    if request.method == 'POST':
        member_id = request.POST.get('member_id')
        action    = request.POST.get('action')
        member    = get_object_or_404(CommunityMember, pk=member_id, community=community)
        if action == 'approve':
            member.status = 'approved'
            member.approved_at = timezone.now()
            member.save()
            _notify(member.user, 'join_approved', f'Your membership in {community.name} has been approved!', f'/portal/c/{page_id}/')
        elif action in ('reject', 'remove'):
            member.status = 'rejected' if action == 'reject' else 'removed'
            member.save()
            _notify(member.user, 'join_rejected', f'Your membership in {community.name} was {member.status}.', '')
        elif action == 'assign_role':
            role = request.POST.get('role', '').strip()
            valid_roles = [r[0] for r in CommunityLeader.ROLES]
            custom_role = request.POST.get('custom_role', '').strip()
            if role and role in valid_roles:
                CommunityLeader.objects.filter(community=community, user=member.user).delete()
                CommunityLeader.objects.create(
                    community=community, user=member.user, role=role, status='accepted',
                    custom_role=custom_role if role == 'member' else ''
                )
                role_label = custom_role if role == 'member' and custom_role else dict(CommunityLeader.ROLES).get(role, role)
                messages.success(request, f'{member.user.get_full_name() or member.user.username} assigned as {role_label}.')
        return redirect(f'/portal/c/{page_id}/members/?status={request.POST.get("status_filter","approved")}')

    status_filter = request.GET.get('status', 'pending')
    memberships = community.memberships.filter(status=status_filter).select_related('user').prefetch_related('user__seeker').order_by('-joined_at')

    # Roles already taken in this community (excluding 'other')
    taken_roles = set(
        CommunityLeader.objects.filter(community=community, status='accepted')
        .exclude(role='member')
        .values_list('role', flat=True)
    )
    # Annotate each membership with the member's current leader role label
    leader_map = {
        l.user_id: l
        for l in CommunityLeader.objects.filter(community=community, status='accepted')
    }
    memberships = list(memberships)
    for m in memberships:
        ldr = leader_map.get(m.user_id)
        m.current_role      = ldr.get_role_label() if ldr else ''
        m.current_role_key  = ldr.role if ldr else ''

    return render(request, 'portal/manage_members.html', {
        'community': community,
        'memberships': memberships,
        'status_filter': status_filter,
        'taken_roles': taken_roles,
        'is_admin': True,
    })


@login_required
def add_leader(request, page_id):
    community = get_object_or_404(Community, page_id=page_id)
    if not community.is_admin(request.user):
        return redirect('portal_community', page_id=page_id)

    if request.method == 'POST':
        import random, string
        p          = request.POST
        role       = p.get('role', 'member')
        email      = p.get('email', '').strip()
        phone      = p.get('phone', '').strip()
        role_label = dict(CommunityLeader.ROLES).get(role, role)
        temp_password = ''
        is_new     = False

        # ── Phone uniqueness check ─────────────────────────
        if phone and User.objects.filter(phone=phone).exclude(email=email).exists():
            messages.error(request, f'Phone {phone} is already linked to another account.')
            return redirect('portal_add_leader', page_id=page_id)

        # ── Get or create account ──────────────────────────
        try:
            nominee = User.objects.get(email=email)
            if phone and not nominee.phone:
                nominee.phone = phone
                nominee.save(update_fields=['phone'])
        except User.DoesNotExist:
            is_new = True
            temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            uname = email.split('@')[0] + str(random.randint(10, 99))
            while User.objects.filter(username=uname).exists():
                uname = email.split('@')[0] + str(random.randint(100, 999))
            nominee = User.objects.create_user(
                username=uname, email=email,
                password=temp_password, phone=phone,
            )

        # ── Remove old pending nomination, create accepted one ──
        CommunityLeader.objects.filter(community=community, user=nominee).delete()
        leader = CommunityLeader.objects.create(
            community=community, user=nominee, role=role,
            custom_role=p.get('custom_role', ''),
            nominated_by=request.user,
            status='accepted',
        )
        leader.generate_token()

        # ── Auto-add as approved community member ──────────
        mem, created = CommunityMember.objects.get_or_create(
            community=community, user=nominee,
            defaults={'status': 'approved', 'approved_at': timezone.now()}
        )
        if not created and mem.status != 'approved':
            mem.status = 'approved'
            mem.approved_at = timezone.now()
            mem.save()

        # ── Send email with credentials ────────────────────
        try:
            msg = (
                f"Dear Friend,\n\n"
                f"You have been appointed as {role_label} of {community.name}.\n\n"
                f"{'─'*40}\n"
                f"Community : {community.name}\n"
                f"Your Role : {role_label}\n"
                f"Appointed by: {request.user.get_full_name() or request.user.username}"
                + (f"\nPhone     : {phone}" if phone else "") +
                f"\n{'─'*40}\n\n"
                f"Login to Local From:\n"
                f"  Website  : {settings.SITE_URL}\n"
                f"  Email    : {email}\n"
            )
            if is_new:
                msg += (
                    f"  Password : {temp_password}\n"
                    f"  (Please change your password after first login)\n\n"
                )
            msg += (
                f"\nAfter login you will be taken directly to {community.name}.\n\n"
                f"As {role_label} you can:\n"
                f"  ✓ Share community posts\n"
                f"  ✓ Post updates and announcements\n"
                f"  ✓ Manage community members\n"
                f"  ✓ Create causes and activities\n\n"
                f"Community page: {settings.SITE_URL}/portal/c/{community.page_id}/\n\n"
                f"Thank you,\nLocal From Team"
            )
            send_mail(
                subject=f"You are now {role_label} of {community.name} — Local From",
                message=msg,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=True,
            )
        except Exception:
            pass

        _notify(nominee, 'leader_nomination',
                f'You are now {role_label} of {community.name}!',
                f'/portal/c/{community.page_id}/')
        messages.success(request, f'✅ {email} appointed as {role_label} and email sent with login details.')
        return redirect('portal_dashboard', page_id=page_id)

    return render(request, 'portal/add_leader.html', {
        'community': community,
        'roles': CommunityLeader.ROLES,
        'leaders': community.leaders.select_related('user').order_by('role'),
    })


# ──────────────────────────────────────────────
# CAUSES
# ──────────────────────────────────────────────

@login_required
def create_cause(request, page_id):
    community = get_object_or_404(Community, page_id=page_id)
    if not community.is_admin(request.user):
        messages.error(request, 'Only community admins can create causes.')
        return redirect('portal_community', page_id=page_id)

    if request.method == 'POST':
        p = request.POST
        cause = Cause(
            community=community, created_by=request.user,
            name=p.get('name','').strip(),
            description=p.get('description','').strip(),
            objective=p.get('objective','').strip(),
            start_date=p.get('start_date'),
            end_date=p.get('end_date') or None,
            location=p.get('location','').strip(),
            target_goal=p.get('target_goal','').strip(),
        )
        if 'image' in request.FILES:
            cause.image = request.FILES['image']
        cause.save()
        # Notify all members
        for m in community.memberships.filter(status='approved').select_related('user'):
            _notify(m.user, 'new_cause', f'New cause in {community.name}: {cause.name}', f'/portal/cause/{cause.pk}/')
        messages.success(request, 'Cause created!')
        return redirect('portal_cause_detail', pk=cause.pk)
    return render(request, 'portal/cause_create.html', {'community': community})


@login_required
def support_cause(request, pk):
    cause = get_object_or_404(Cause, pk=pk)
    obj, created = CauseSupport.objects.get_or_create(cause=cause, user=request.user)
    if not created:
        obj.delete()
        return JsonResponse({'status': 'unsupported', 'count': cause.support_count()})
    return JsonResponse({'status': 'supported', 'count': cause.support_count()})


# ──────────────────────────────────────────────
# VOLUNTEER
# ──────────────────────────────────────────────

def volunteer_form(request, page_id):
    community = get_object_or_404(Community, page_id=page_id, is_active=True)

    if request.method == 'POST':
        p = request.POST
        vr = VolunteerRequest(
            community=community,
            name=p.get('name','').strip(),
            email=p.get('email','').strip(),
            mobile=p.get('mobile','').strip(),
            volunteer_interest=p.get('volunteer_interest','').strip(),
            message=p.get('message','').strip(),
            availability=p.get('availability','').strip(),
        )
        if request.user.is_authenticated:
            vr.user = request.user
        vr.save()
        if community.created_by:
            _notify(community.created_by, 'join_request',
                    f'{vr.name} wants to volunteer for {community.name}.',
                    f'/portal/c/{page_id}/volunteers/')
        messages.success(request, 'Volunteer request submitted! Community admin will review it.')
        return redirect('portal_community', page_id=page_id)

    return render(request, 'portal/volunteer_form.html', {'community': community})


@login_required
def manage_volunteers(request, page_id):
    community = get_object_or_404(Community, page_id=page_id)
    if not community.is_admin(request.user):
        return redirect('portal_community', page_id=page_id)

    if request.method == 'POST':
        vr_id  = request.POST.get('vr_id')
        action = request.POST.get('action')
        vr = get_object_or_404(VolunteerRequest, pk=vr_id, community=community)
        if action == 'approve':
            vr.status = 'approved'
            vr.save()
            if vr.user:
                _notify(vr.user, 'volunteer_approved', f'Your volunteer request for {community.name} is approved!', f'/portal/c/{page_id}/')
        elif action == 'reject':
            vr.status = 'rejected'
            vr.save()
        return redirect('portal_manage_volunteers', page_id=page_id)

    status_filter = request.GET.get('status', 'pending')
    vrs = community.volunteer_requests.filter(status=status_filter).order_by('-created_at')
    return render(request, 'portal/manage_volunteers.html', {
        'community': community, 'vrs': vrs, 'status_filter': status_filter,
        'pending_count': community.volunteer_requests.filter(status='pending').count(),
        'approved_count': community.volunteer_requests.filter(status='approved').count(),
    })


# ──────────────────────────────────────────────
# ACTIVITIES
# ──────────────────────────────────────────────

@login_required
def create_activity(request, page_id):
    community = get_object_or_404(Community, page_id=page_id)
    if not community.is_admin(request.user):
        messages.error(request, 'Only community admins can log activities.')
        return redirect('portal_community', page_id=page_id)

    causes = community.causes.filter(is_active=True)
    if request.method == 'POST':
        p = request.POST
        activity = Activity(
            community=community, created_by=request.user,
            name=p.get('name','').strip(),
            description=p.get('description','').strip(),
            date=p.get('date'),
            location=p.get('location','').strip(),
            participant_count=int(p.get('participant_count',0) or 0),
            volunteer_count=int(p.get('volunteer_count',0) or 0),
            result_impact=p.get('result_impact','').strip(),
        )
        if p.get('cause'):
            activity.cause_id = p.get('cause')
        activity.save()
        # Save photos
        for f in request.FILES.getlist('photos'):
            ActivityPhoto.objects.create(activity=activity, image=f)
        messages.success(request, 'Activity logged!')
        return redirect('portal_activity_detail', pk=activity.pk)
    return render(request, 'portal/activity_create.html', {'community': community, 'causes': causes})


# ──────────────────────────────────────────────
# COMMUNITY FEED (POSTS)
# ──────────────────────────────────────────────

@login_required
def create_post(request, page_id):
    community = get_object_or_404(Community, page_id=page_id)
    if not (_is_member(community, request.user) or community.is_admin(request.user)):
        messages.error(request, 'Only members can post.')
        return redirect('portal_community', page_id=page_id)

    if request.method == 'POST':
        from datetime import date as _date
        p = request.POST
        content = p.get('content', '').strip().strip('\u200b\ufeff').strip()
        imgs = request.FILES.getlist('image')
        meaningful_text = content.replace('\u200b', '').replace('\ufeff', '').strip()
        if not meaningful_text and not imgs:
            messages.error(request, 'Write a message or attach a photo before publishing.')
            return redirect('portal_community', page_id=page_id)
        if imgs:
            from django.forms import ImageField
            from django.core.exceptions import ValidationError
            try:
                ImageField().clean(imgs[0])
            except ValidationError:
                messages.error(request, 'Please attach a valid photo.')
                return redirect('portal_community', page_id=page_id)
        event_date = None
        raw_date = p.get('event_date', '').strip()
        if raw_date:
            try:
                event_date = _date.fromisoformat(raw_date)
            except ValueError:
                pass
        post = Post(
            community=community, author=request.user,
            post_type=p.get('post_type', 'update'),
            content=content,
            event_date=event_date,
        )
        if imgs:
            post.image = imgs[0]
        post.save()
        messages.success(request, 'Post published!')
    return redirect('portal_community', page_id=page_id)


@login_required
def like_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    obj, created = PostLike.objects.get_or_create(post=post, user=request.user)
    if not created:
        obj.delete()
    return JsonResponse({'liked': created, 'count': post.like_count()})


@login_required
def comment_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == 'POST':
        content = request.POST.get('content','').strip()
        if content:
            PostComment.objects.create(post=post, user=request.user, content=content)
    return redirect(request.META.get('HTTP_REFERER', f'/portal/c/{post.community.page_id}/'))


@login_required
def delete_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    community = post.community
    if post.author == request.user or community.is_admin(request.user):
        page_id = community.page_id
        post.delete()
        return redirect(f'/portal/c/{page_id}/')
    messages.error(request, 'Permission denied.')
    return redirect(f'/portal/c/{community.page_id}/')


# ──────────────────────────────────────────────
# VIDEOS
# ──────────────────────────────────────────────

@login_required
def upload_video(request, page_id):
    community = get_object_or_404(Community, page_id=page_id)
    if not (_is_member(community, request.user) or community.is_admin(request.user)):
        messages.error(request, 'Only members can upload videos.')
        return redirect('portal_community', page_id=page_id)

    causes     = community.causes.filter(is_active=True)
    activities = community.activities.filter(is_active=True)

    if request.method == 'POST':
        p = request.POST
        video = ShortVideo(
            community=community, uploader=request.user,
            title=p.get('title','').strip(),
            category=p.get('category','story'),
            pincode=p.get('pincode','').strip(),
            location=p.get('location','').strip(),
        )
        if 'video' in request.FILES:
            video.video = request.FILES['video']
        if 'thumbnail' in request.FILES:
            video.thumbnail = request.FILES['thumbnail']
        if p.get('related_cause'):
            video.related_cause_id = p.get('related_cause')
        if p.get('related_activity'):
            video.related_activity_id = p.get('related_activity')
        video.save()
        messages.success(request, 'Video uploaded!')
        return redirect('portal_community', page_id=page_id)

    return render(request, 'portal/video_upload.html', {
        'community': community, 'causes': causes, 'activities': activities,
        'categories': ShortVideo.VIDEO_CATS,
    })


@login_required
def delete_video(request, pk):
    video = get_object_or_404(ShortVideo, pk=pk)
    if request.user == video.uploader or video.community.is_admin(request.user) or request.user.is_staff:
        video.is_active = False
        video.save()
        messages.success(request, 'Video removed.')
    return redirect(request.META.get('HTTP_REFERER', '/portal/videos/'))


# ──────────────────────────────────────────────
# USER: MY PAGES
# ──────────────────────────────────────────────

@login_required
def my_communities(request):
    memberships = CommunityMember.objects.filter(user=request.user).select_related('community').order_by('-joined_at')
    return render(request, 'portal/my_communities.html', {'memberships': memberships})


@login_required
def portal_notifications(request):
    notifs = request.user.portal_notifications.all()[:50]
    request.user.portal_notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'portal/notifications.html', {'notifs': notifs})


# ──────────────────────────────────────────────
# PLATFORM ADMIN
# ──────────────────────────────────────────────

def _require_staff(request):
    return request.user.is_authenticated and request.user.is_staff


# ──────────────────────────────────────────────
# COMMUNITY EDIT
# ──────────────────────────────────────────────

@login_required
def edit_community(request, page_id):
    community = get_object_or_404(Community, page_id=page_id, is_active=True)
    if not community.is_admin(request.user):
        messages.error(request, 'Only community admins can edit.')
        return redirect('portal_community', page_id=page_id)

    if request.method == 'POST':
        p = request.POST
        community.name        = p.get('name', '').strip() or community.name
        community.purpose     = p.get('purpose', '').strip()
        community.description = p.get('description', '').strip()
        community.location    = p.get('location', '').strip()
        community.pincode     = p.get('pincode', '').strip()
        community.email       = p.get('comm_email', '').strip()
        community.phone       = p.get('comm_phone', '').strip()
        community.join_mode   = p.get('join_mode', community.join_mode)
        cat_id = p.get('category')
        community.category_id = cat_id if cat_id else None
        def _save_b64(field_name, file_name):
            import base64, io
            from django.core.files.base import ContentFile
            data = request.POST.get(field_name + '_cropped', '')
            if data and data.startswith('data:image'):
                fmt, imgstr = data.split(';base64,', 1)
                return ContentFile(base64.b64decode(imgstr), name=file_name + '.jpg')
            return None
        logo_file = _save_b64('logo', f'logo_{community.page_id}')
        cover_file = _save_b64('cover', f'cover_{community.page_id}')
        if logo_file:
            community.logo = logo_file
        elif 'logo' in request.FILES:
            community.logo = request.FILES['logo']
        if cover_file:
            community.cover = cover_file
        elif 'cover' in request.FILES:
            community.cover = request.FILES['cover']
        community.save()
        messages.success(request, 'Community updated successfully!')
        return redirect('portal_community', page_id=community.page_id)

    return render(request, 'portal/community_edit.html', {
        'community': community,
        'categories': Category.objects.all(),
    })


# ──────────────────────────────────────────────
# FLICK
# ──────────────────────────────────────────────

def flick_feed(request):
    community_filter = request.GET.get('community', '')

    # Auto-promote ShortVideos to Flick records so likes/comments work
    videos_qs = ShortVideo.objects.filter(is_active=True).select_related('community', 'uploader')
    if community_filter:
        videos_qs = videos_qs.filter(community__page_id=community_filter)
    for v in videos_qs:
        Flick.objects.get_or_create(
            source_video_id=v.pk,
            defaults={
                'community': v.community,
                'posted_by': v.uploader,
                'caption': v.title,
                'media': v.video,
                'media_type': 'video',
                'is_active': True,
                'created_at': v.created_at,
            }
        )

    flicks_qs = Flick.objects.filter(is_active=True).select_related('community', 'posted_by')
    if community_filter:
        flicks_qs = flicks_qs.filter(community__page_id=community_filter)
    flicks_qs = flicks_qs.order_by('-created_at')

    liked_ids = set()
    admin_community_ids = set()
    if request.user.is_authenticated:
        liked_ids = set(FlickLike.objects.filter(user=request.user).values_list('flick_id', flat=True))
        # Communities where current user is admin/leader
        from portal.models import CommunityLeader
        admin_community_ids = set(
            Community.objects.filter(created_by=request.user, is_active=True).values_list('page_id', flat=True)
        ) | set(
            CommunityLeader.objects.filter(user=request.user, status='accepted').values_list('community__page_id', flat=True)
        )
        if getattr(request.user, 'admin_role', '') == 'super_admin':
            admin_community_ids = set(Community.objects.values_list('page_id', flat=True))

    my_pending = []
    if request.user.is_authenticated:
        my_pending = Flick.objects.filter(posted_by=request.user, is_active=False).order_by('-created_at')

    return render(request, 'portal/flick_feed.html', {
        'flicks': flicks_qs,
        'liked_ids': liked_ids,
        'community_filter': community_filter,
        'admin_community_ids': admin_community_ids,
        'my_pending': my_pending,
    })


@login_required
def create_flick(request):
    user_communities = Community.objects.filter(
        memberships__user=request.user, memberships__status='approved', is_active=True
    ).distinct()

    if request.method == 'POST':
        p = request.POST
        community_id = p.get('community')
        community = get_object_or_404(Community, page_id=community_id)
        if not community.memberships.filter(user=request.user, status='approved').exists():
            messages.error(request, 'You must be a member of this community to post a Flick.')
            return redirect('portal_flicks')

        if 'media' not in request.FILES:
            messages.error(request, 'Please upload a video or image.')
            return render(request, 'portal/flick_create.html', {'user_communities': user_communities})

        media = request.FILES['media']
        media_type = 'video' if media.content_type.startswith('video') else 'image'

        is_comm_admin = community.is_admin(request.user)
        flick = Flick.objects.create(
            community=community,
            posted_by=request.user,
            caption=p.get('caption', '').strip()[:300],
            media=media,
            media_type=media_type,
            is_active=is_comm_admin,
        )
        if is_comm_admin:
            messages.success(request, 'Flick posted!')
        else:
            if community.created_by:
                _notify(community.created_by, 'flick_request', f'{request.user.get_full_name() or request.user.username} posted a Flick in {community.name} — awaiting your approval.', f'/portal/c/{community.page_id}/dashboard/')
            messages.success(request, 'Flick submitted! Waiting for admin approval.')
        return redirect('portal_flicks')

    preselect = request.GET.get('community', '')
    return render(request, 'portal/flick_create.html', {
        'user_communities': user_communities,
        'preselect': preselect,
    })


@login_required
def like_flick(request, pk):
    flick = get_object_or_404(Flick, pk=pk, is_active=True)
    obj, created = FlickLike.objects.get_or_create(flick=flick, user=request.user)
    if not created:
        obj.delete()
        return JsonResponse({'liked': False, 'count': flick.like_count()})
    return JsonResponse({'liked': True, 'count': flick.like_count()})


@login_required
def delete_flick(request, pk):
    flick = get_object_or_404(Flick, pk=pk, posted_by=request.user)
    if request.method == 'POST':
        flick.is_active = False
        flick.save()
        return JsonResponse({'deleted': True})
    return JsonResponse({'error': 'POST required'}, status=405)


def member_profile(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    # Only community admins can view this
    if not request.user.is_authenticated:
        return redirect(f'/login/?next=/portal/member/{user_id}/')
    is_any_admin = (
        getattr(request.user, 'admin_role', '') == 'super_admin' or
        CommunityLeader.objects.filter(user=request.user, status='accepted').exists() or
        Community.objects.filter(created_by=request.user).exists()
    )
    if not is_any_admin:
        messages.error(request, 'Access denied.')
        return redirect('portal_home')
    try:
        profile = target.seeker
    except Exception:
        profile = None
    return render(request, 'portal/member_profile.html', {
        'target': target,
        'profile': profile,
    })


@login_required
def approve_flick(request, pk):
    flick = get_object_or_404(Flick, pk=pk)
    if flick.community and flick.community.is_admin(request.user):
        flick.is_active = True
        flick.approved_by = request.user
        flick.save(update_fields=['is_active', 'approved_by'])
        messages.success(request, 'Flick approved and published.')
    return redirect(f'/portal/c/{flick.community.page_id}/dashboard/')


@login_required
def reject_flick(request, pk):
    flick = get_object_or_404(Flick, pk=pk)
    if flick.community and flick.community.is_admin(request.user):
        page_id = flick.community.page_id
        flick.delete()
        messages.success(request, 'Flick rejected and removed.')
        return redirect(f'/portal/c/{page_id}/dashboard/')
    return redirect('portal_home')


def flick_comments(request, pk):
    flick = get_object_or_404(Flick, pk=pk, is_active=True)
    comments = list(flick.flick_comments.select_related('user').values(
        'id', 'text', 'created_at', 'user__first_name', 'user__last_name', 'user__username'
    ))
    for c in comments:
        name = (c['user__first_name'] + ' ' + c['user__last_name']).strip()
        c['name'] = name or c['user__username']
        del c['user__first_name']; del c['user__last_name']; del c['user__username']
        c['created_at'] = c['created_at'].strftime('%d %b')
    return JsonResponse({'comments': comments, 'count': len(comments)})


@login_required
def flick_comment_add(request, pk):
    flick = get_object_or_404(Flick, pk=pk, is_active=True)
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        text = data.get('text', '').strip()[:500]
        if text:
            c = FlickComment.objects.create(flick=flick, user=request.user, text=text)
            name = request.user.get_full_name() or request.user.username
            return JsonResponse({'ok': True, 'id': c.pk, 'name': name, 'text': text, 'created_at': c.created_at.strftime('%d %b'), 'count': flick.flick_comments.count()})
    return JsonResponse({'ok': False})


@login_required
def admin_communities(request):
    if not _require_staff(request):
        return redirect('portal_home')
    communities = Community.objects.all().select_related('created_by', 'category').order_by('-created_at')
    status = request.GET.get('status', '')
    if status == 'pending':
        communities = communities.filter(is_verified=False, is_active=True)
    elif status == 'unverified':
        communities = communities.filter(is_verified=False, is_active=True)
    elif status == 'verified':
        communities = communities.filter(is_verified=True, is_active=True)
    elif status == 'rejected':
        communities = communities.filter(is_verified=False, is_active=False)
    elif status == 'suspended':
        communities = communities.filter(is_verified=True, is_active=False)
    return render(request, 'portal/admin_communities.html', {
        'communities': communities, 'status': status,
        'total': Community.objects.count(),
        'unverified': Community.objects.filter(is_verified=False, is_active=True).count(),
        'verified': Community.objects.filter(is_verified=True, is_active=True).count(),
        'rejected': Community.objects.filter(is_verified=False, is_active=False).count(),
    })


@login_required
def admin_verify_community(request, pk):
    if not _require_staff(request):
        return redirect('portal_home')
    community = get_object_or_404(Community, pk=pk)
    community.is_verified = True
    community.save()
    if community.created_by:
        _notify(community.created_by, 'announcement',
                f'Your community {community.name} has been verified and is now live!',
                f'/portal/c/{community.page_id}/')
    messages.success(request, f'{community.name} verified.')
    return redirect('portal_admin_communities')


@login_required
def admin_suspend_community(request, pk):
    if not _require_staff(request):
        return redirect('portal_home')
    community = get_object_or_404(Community, pk=pk)
    community.is_active = not community.is_active
    community.save()
    action = 'reactivated' if community.is_active else 'suspended'
    messages.success(request, f'{community.name} {action}.')
    return redirect('portal_admin_communities')


@login_required
def admin_reject_community(request, pk):
    if not _require_staff(request):
        return redirect('portal_home')
    community = get_object_or_404(Community, pk=pk)
    community.is_verified = False
    community.is_active = False
    community.save()
    if community.created_by:
        _notify(community.created_by, 'announcement',
                f'Your community "{community.name}" was not approved. Please contact support for details.',
                '/portal/create/')
    messages.success(request, f'{community.name} rejected.')
    return redirect('portal_admin_communities')


@login_required
def admin_delete_community(request, pk):
    if not _require_staff(request):
        return redirect('portal_home')
    community = get_object_or_404(Community, pk=pk)
    if request.method == 'POST':
        name = community.name
        community.delete()
        messages.success(request, f'Community "{name}" permanently deleted.')
        return redirect('portal_admin_communities')
    return render(request, 'portal/admin_community_confirm_delete.html', {'community': community})


@login_required
def admin_delete_video(request, pk):
    if not _require_staff(request):
        return redirect('portal_home')
    video = get_object_or_404(ShortVideo, pk=pk)
    video.is_active = False
    video.save()
    messages.success(request, 'Video removed.')
    return redirect('portal_videos')


@login_required
@never_cache
def membership_status(request, page_id):
    community = get_object_or_404(Community, page_id=page_id, is_active=True)
    membership = community.memberships.filter(user=request.user).first()
    return JsonResponse({
        'member_count': community.member_count(),
        'status': membership.status if membership else None,
    })
