from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db import transaction
from .admin_messages import send_review_message
from .models import (User, CompanyProfile, ShopProfile,
                     Message, Advertiser, AdPackage, Advertisement, AdPayment,
                     State, District, PinCode, AdminProfile, Industry,
                     Discount, Complaint, SystemNotification, LocalOffer, Product, ProductImage, ShopVideo)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    max_num = 5


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline]
    list_display = ('name', 'shop', 'price', 'discount_percent', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'shop__company_name')
    list_select_related = ('shop',)


@admin.register(ShopVideo)
class ShopVideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'shop', 'is_published', 'created_at')
    list_filter = ('is_published',)
    search_fields = ('title', 'shop__company_name')
    list_select_related = ('shop',)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ('username', 'user_type', 'phone', 'city', 'pincode', 'is_active', 'date_joined')
    list_filter   = ('user_type', 'is_active', 'city')
    search_fields = ('username', 'phone', 'email', 'city')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Extra Info', {'fields': ('user_type', 'phone', 'address', 'city', 'pincode')}),
    )


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display  = ('company_id', 'company_name', 'industry', 'website', 'company_size')
    search_fields = ('company_id', 'company_name', 'industry')


@admin.register(ShopProfile)
class ShopProfileAdmin(admin.ModelAdmin):
    list_display  = ('shop_name', 'shop_type', 'owner_name')
    search_fields = ('shop_name', 'owner_name')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'conversation':
            kwargs['queryset'] = db_field.remote_field.model.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    exclude = ('invite_date', 'invite_time', 'invite_mode', 'invite_location', 'invite_link', 'invite_notes', 'invite_status')
    list_display  = ('sender', 'receiver', 'sent_at', 'is_read')
    list_filter   = ('is_read',)
    search_fields = ('sender__username', 'receiver__username')


# ---- Advertiser Module ----
@admin.register(Advertiser)
class AdvertiserAdmin(admin.ModelAdmin):
    list_display  = ('business_name', 'contact_person', 'phone', 'email', 'status', 'created_at')
    list_filter   = ('status',)
    search_fields = ('business_name', 'contact_person', 'phone', 'email')
    actions       = ['approve_advertisers', 'reject_advertisers']

    @transaction.atomic
    def approve_advertisers(self, request, queryset):
        from django.utils import timezone
        count=0
        for advertiser in queryset.select_for_update().exclude(status='approved'):
            advertiser.status='approved'
            advertiser.approved_at=timezone.now()
            advertiser.save(update_fields=['status','approved_at'])
            send_review_message(request.user,advertiser.user,'Your advertiser account is approved',
                f'Your advertiser account for {advertiser.business_name} has been approved.', '/advertiser/dashboard/')
            count+=1
        self.message_user(request, f'{count} advertisers approved.')
    approve_advertisers.short_description = 'Approve selected advertisers'

    def reject_advertisers(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, f'{queryset.count()} advertisers rejected.')
    reject_advertisers.short_description = 'Reject selected advertisers'


@admin.register(AdPackage)
class AdPackageAdmin(admin.ModelAdmin):
    list_display  = ('name', 'ad_type', 'duration_days', 'price', 'size_specs', 'is_active')
    list_filter   = ('ad_type', 'is_active')
    list_editable = ('price', 'is_active')
    search_fields = ('name',)


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display  = ('title', 'advertiser', 'package', 'status', 'views', 'clicks', 'start_date', 'end_date')
    list_filter   = ('status', 'package__ad_type')
    search_fields = ('title', 'advertiser__business_name')
    actions       = ['activate_ads', 'reject_ads']

    @transaction.atomic
    def activate_ads(self, request, queryset):
        from datetime import date, timedelta
        for ad in queryset.select_for_update():
            if ad.status == 'pending_review':
                ad.status     = 'active'
                ad.start_date = date.today()
                ad.end_date   = date.today() + timedelta(days=ad.package.duration_days)
                ad.save()
                send_review_message(request.user,ad.advertiser.user,'Your advertisement is approved',
                    f'Your advertisement "{ad.title}" has been approved and is now live.', '/advertiser/dashboard/')
        self.message_user(request, 'Selected ads activated.')
    activate_ads.short_description = 'Activate selected ads'

    def reject_ads(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, 'Selected ads rejected.')
    reject_ads.short_description = 'Reject selected ads'


@admin.register(AdPayment)
class AdPaymentAdmin(admin.ModelAdmin):
    list_display  = ('advertisement', 'amount', 'gst_amount', 'total_amount', 'status', 'payment_method', 'paid_at')
    list_filter   = ('status', 'payment_method')
    search_fields = ('invoice_number', 'transaction_id', 'advertisement__title')


# ---- Admin Hierarchy Models ----
@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display  = ('name', 'code', 'is_active', 'created_at')
    list_filter   = ('is_active',)
    list_editable = ('is_active',)
    search_fields = ('name', 'code')


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display  = ('name', 'state', 'is_active', 'created_at')
    list_filter   = ('is_active', 'state')
    search_fields = ('name', 'state__name')


@admin.register(PinCode)
class PinCodeAdmin(admin.ModelAdmin):
    list_display  = ('code', 'area_name', 'district', 'is_active')
    list_filter   = ('is_active', 'district__state')
    search_fields = ('code', 'area_name')


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'role', 'state', 'district', 'is_active', 'created_at')
    list_filter   = ('role', 'is_active')
    search_fields = ('user__username', 'user__first_name')
    raw_id_fields = ('user', 'state', 'district', 'appointed_by')


@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display  = ('name', 'collar', 'icon', 'is_active', 'order')
    list_filter   = ('collar', 'is_active')
    list_editable = ('is_active', 'order')
    search_fields = ('name',)


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display  = ('code', 'discount_type', 'value', 'used_count', 'max_uses', 'valid_until', 'is_active')
    list_filter   = ('discount_type', 'is_active')
    search_fields = ('code',)


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request)

    list_display  = ('subject', 'complaint_type', 'submitted_by', 'district', 'status', 'created_at')
    list_filter   = ('complaint_type', 'status')
    search_fields = ('subject', 'submitted_by__username')
    raw_id_fields = ('submitted_by', 'assigned_to', 'district')


@admin.register(SystemNotification)
class SystemNotificationAdmin(admin.ModelAdmin):
    list_display  = ('title', 'notif_type', 'target_role', 'is_active', 'created_at')
    list_filter   = ('notif_type', 'is_active', 'target_role')
    search_fields = ('title',)


@admin.register(LocalOffer)
class LocalOfferAdmin(admin.ModelAdmin):
    list_display   = ('business_name', 'title', 'discount_text', 'category', 'is_flash', 'is_active', 'valid_until')
    list_filter    = ('category', 'is_flash', 'is_active')
    search_fields  = ('business_name', 'title')
    list_editable  = ('is_active', 'is_flash')
