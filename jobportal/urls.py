from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from jobs import views
from jobs import business_reviews
from jobs import account
from jobs import shop
from jobs import simple_accounts
from jobs import pilot_admin
from jobs import ad_applications
from jobs import notifications
from jobs import product_access
from jobs import password_recovery
from jobs import shop_directory
from jobs import local_from
from jobs import analytics
from jobs import chat_attachments
from jobs import quick_products
from jobs import promotion_metrics
from django.contrib.sitemaps import views as sitemap_views
from .seo import SITEMAPS, robots, sitemap_index

urlpatterns = [
    path('', include('jobs.assigned_admin')),
    path('', include('jobs.admin_hierarchy')),
    path('robots.txt', robots, name='robots'),
    path('sitemap.xml', sitemap_index, name='sitemap'),
    path('sitemaps/<section>.xml', sitemap_views.sitemap, {'sitemaps': SITEMAPS}, name='seo_sitemap'),
    path('news/', include('newsdesk.urls')),
    path('admin/',                  admin.site.urls),
    path('',                        views.home,               name='home'),
    path('favicon.ico',             views.favicon,            name='favicon'),
    path('api/pincode/<str:pin>/',  views.api_pincode_lookup, name='api_pincode_lookup'),

    path('shop/products/access/', product_access.request_access, name='product_access_request'),
    path('super-admin/product-requests/', product_access.requests, name='product_access_requests'),
    path('super-admin/shops/<int:pk>/product-access/', product_access.assign_access, name='product_access_assign'),
    path('notifications/', notifications.inbox, name='notifications'),
    path('messages/attachments/<int:message_id>/', chat_attachments.download, name='chat_attachment'),
    path('notifications/feed/', notifications.feed, name='notification_feed'),
    path('notifications/<int:pk>/open/', notifications.open_notification, name='notification_open'),
    path('advertise/applications/', ad_applications.applications, name='ad_applications'),
    path('advertise/applications/<int:pk>/edit/', ad_applications.apply, name='ad_application_edit'),
    path('super-admin/ads/', pilot_admin.ads, name='pilot_admin_ads'),
    path('super-admin/ads/<int:pk>/', pilot_admin.ad_detail, name='pilot_admin_ad'),
    path('super-admin/login/', pilot_admin.sign_in, name='pilot_admin_login'),
    path('super-admin/analytics/',analytics.dashboard,name='analytics_dashboard'),
    path('super-admin/analytics/live/',analytics.live,name='analytics_live'),
    path('super-admin/analytics/activity/',analytics.activity,name='analytics_activity'),
    path('analytics/collect/',analytics.collect,name='analytics_collect'),
    path('super-admin/logout/', pilot_admin.sign_out, name='pilot_admin_logout'),
    path('super-admin/shops/<int:pk>/', pilot_admin.shop_detail, name='pilot_admin_shop'),
    path('super-admin/users/<int:pk>/', pilot_admin.user_detail, name='pilot_admin_user'),

    # Auth
    path('register/',               simple_accounts.signup,   name='register'),
    path('account/', simple_accounts.personal_account, name='personal_account'),
    path('local-from/',local_from.profile,name='local_from_profile'),
    path('local-from/follow/',local_from.follow,name='local_from_follow'),
    path('business/create/', simple_accounts.business_create, name='business_create'),
    path('business/directory/search/',shop_directory.search,name='shop_directory_search'),
    path('super-admin/shop-directory/',shop_directory.directory,name='shop_directory'),
    path('super-admin/shop-directory/template/',shop_directory.template,name='shop_directory_template'),
    path('register/process/',       views.register_process,   name='register_process'),
    path('login/',                  views.login_view,         name='login'),
    path('forgot-password/',        password_recovery.recover,    name='forgot_password'),
    path('api/reset-password/',     views.reset_password,     name='reset_password'),
    path('logout/',                 views.logout_view,        name='logout'),
    path('dashboard/',              views.dashboard,          name='dashboard'),

    # OTP
    path('api/send-otp/',           views.send_otp,           name='send_otp'),
    path('api/verify-otp/',         views.verify_otp,         name='verify_otp'),
    path('api/quick-register/',     views.quick_register,     name='quick_register'),
    path('api/send-register-otp/',  views.send_register_otp,  name='send_register_otp'),
    path('api/verify-register-otp/',views.verify_register_otp,name='verify_register_otp'),
    path('api/check-phone/',        views.check_phone,        name='check_phone'),
    path('api/phone-login/',        views.phone_login,        name='phone_login'),

    # Business Public Profile
    path('products/', shop.product_list, name='product_list'),
    path('products/<int:pk>/', shop.product_detail, name='product_detail'),
    path('shop/products/add/', shop.product_form, name='product_add'),
    path('shop/products/easy/', quick_products.editor, name='product_easy_add'),
    path('shop/performance/', promotion_metrics.dashboard, name='shop_performance'),
    path('analytics/collect/promotions/', promotion_metrics.collect, name='promotion_collect'),
    path('shop/products/easy/publish/', quick_products.publish, name='product_easy_publish'),
    path('shop/products/<int:pk>/edit/', shop.product_form, name='product_edit'),
    path('shop/products/<int:pk>/delete/', shop.product_delete, name='product_delete'),
    path('shop/videos/add/', shop.video_form, name='shop_video_add'),
    path('shop/videos/<int:pk>/edit/', shop.video_form, name='shop_video_edit'),
    path('shop/videos/<int:pk>/delete/', shop.video_delete, name='shop_video_delete'),
    path('shop/offers/add/', shop.offer_form, name='shop_offer_add'),
    path('shop/offers/<int:pk>/edit/', shop.offer_form, name='shop_offer_edit'),
    path('shop/offers/<int:pk>/delete/', shop.offer_delete, name='shop_offer_delete'),
    path('businesses/', views.business_list, name='business_list'),
    path('offers/mine/', views.my_offers, name='my_offers'),
    path('offers/<int:pk>/store/', views.offer_store, name='offer_store'),
    path('business/<str:company_id>/', views.business_profile, name='business_profile'),
    path('business/<str:company_id>/follow/', account.follow_business, name='business_follow'),
    path('area/select/', account.select_area, name='select_area'),
    path('business/<str:company_id>/review/', business_reviews.submit_review, name='business_review'),

    # Dashboards
    path('employer/dashboard/',        views.employer_dashboard,       name='employer_dashboard'),
    path('employer/gallery/upload/',   shop.gallery_upload,           name='gallery_upload'),
    path('employer/gallery/<int:pk>/delete/', shop.gallery_delete,    name='gallery_delete'),

    # Messaging
    path('messages/',                            views.chat_list,          name='chat_list'),
    path('messages/<int:conv_id>/',              views.chat_room,          name='chat_room'),
    path('messages/start/<int:user_id>/',        views.start_conversation, name='start_conversation'),
    path('messages/send/',                       views.send_message,       name='send_message'),
    path('messages/poll/<int:conv_id>/',         views.poll_messages,      name='poll_messages'),

    # Advertiser — Public
    path('advertise/',                        views.ads_gallery,              name='ads_gallery'),
    path('advertise/sponsored/<int:ad_id>/', views.sponsored_detail, {'kind': 'post'}, name='sponsored_post_detail'),
    path('advertise/ad/<int:ad_id>/', views.sponsored_detail, {'kind': 'ad'}, name='sponsored_ad_detail'),
    path('advertise/business/<int:ad_id>/', views.sponsored_detail, {'kind': 'banner'}, name='sponsored_banner_detail'),
    path('advertise/register/',               ad_applications.apply,      name='advertiser_register'),
    path('advertise/success/',                ad_applications.applications, name='advertiser_register_success'),
    path('offers/post/',                      views.offer_post,               name='offer_post'),
    path('offers/post/success/',              views.offer_post_success,       name='offer_post_success'),

    # Advertiser — Logged-in
    path('advertiser/dashboard/',             views.advertiser_dashboard,     name='advertiser_dashboard'),
    path('advertiser/create-ad/',             views.create_advertisement,     name='create_advertisement'),
    path('advertiser/payment/<int:ad_id>/',   views.ad_payment,               name='ad_payment'),
    path('advertiser/payment/<int:ad_id>/success/', views.ad_payment_success, name='ad_payment_success'),
    path('advertiser/performance/<int:ad_id>/', views.ad_performance,         name='ad_performance'),
    path('advertiser/renew/<int:ad_id>/',     views.advertiser_renew_ad,      name='advertiser_renew_ad'),
    path('ads/click/<int:ad_id>/',            views.ad_click_track,           name='ad_click_track'),
    path('ads/adpost-click/<int:ad_id>/',     views.adpost_click_track,       name='adpost_click_track'),

    # Advertiser — Ad Panel (old admin)
    path('admin-panel/advertisers/',          views.admin_advertisers,          name='admin_advertisers'),
    path('admin-panel/advertisers/<int:adv_id>/approve/',        views.admin_approve_advertiser,         name='admin_approve_advertiser'),
    path('admin-panel/advertisers/<int:adv_id>/reject/',         views.admin_reject_advertiser,          name='admin_reject_advertiser'),
    path('admin-panel/advertisers/<int:adv_id>/remove/',         views.admin_remove_advertiser,          name='admin_remove_advertiser'),
    path('admin-panel/advertisers/<int:adv_id>/upload-banner/',  views.admin_upload_advertiser_banner,   name='admin_upload_advertiser_banner'),
    path('admin-panel/ads/',                  views.admin_ad_list,              name='admin_ad_list'),
    path('admin-panel/ads/<int:ad_id>/activate/', views.admin_activate_ad,      name='admin_activate_ad'),
    path('admin-panel/ads/<int:ad_id>/reject/',   views.admin_reject_ad,        name='admin_reject_ad'),
    path('admin-panel/ads/<int:ad_id>/delete/',   views.admin_delete_ad,        name='admin_delete_ad'),
    path('admin-panel/login/',                    views.admin_panel_login,       name='admin_panel_login'),
    path('admin-panel/ads/<int:ad_id>/image/',    views.admin_set_ad_image,     name='admin_set_ad_image'),
    path('admin-panel/users/',                    views.admin_users,             name='admin_users'),

    # ── SUPER ADMIN ─────────────────────────────────────────
    path('super-admin/users/',                          pilot_admin.users,     name='super_admin_users'),
    path('super-admin/users/<int:user_id>/delete/',     views.super_admin_delete_user, name='super_admin_delete_user'),
    path('super-admin/',                               pilot_admin.shops, name='super_admin_dashboard'),
    path('super-admin/states/',                        views.manage_states,         name='manage_states'),
    path('super-admin/states/<int:pk>/toggle/',        views.toggle_state,          name='toggle_state'),
    path('super-admin/states/<int:state_id>/districts/', views.manage_districts,    name='manage_districts'),
    path('super-admin/state-admins/',                  views.manage_state_admins,   name='manage_state_admins'),
    path('super-admin/state-admins/create/',           views.create_state_admin,    name='create_state_admin'),
    path('super-admin/admins/<int:pk>/toggle/',        views.toggle_admin,          name='toggle_admin'),
    path('super-admin/industries/',                    views.manage_industries,     name='manage_industries'),
    path('super-admin/ad-packages/',                   views.manage_ad_packages,    name='manage_ad_packages'),
    path('super-admin/ad-posts/',                      views.admin_ad_posts,        name='admin_ad_posts'),

    # ── SIMPLE ADS ──────────────────────────────────────────────────────────
    path('ads/post/',                                  views.post_simple_ad,        name='post_simple_ad'),
    path('ads/my-ads/',                                views.my_simple_ads,         name='my_simple_ads'),
    path('ads/<int:pk>/renew/',                        views.renew_ad,              name='renew_ad'),
    path('super-admin/ad-settings/',                   views.admin_ad_settings,     name='admin_ad_settings'),
    path('super-admin/discounts/',                     views.manage_discounts,      name='manage_discounts'),
    path('super-admin/pincodes/',                      views.manage_pincodes,       name='manage_pincodes'),
    path('super-admin/pincodes/<int:district_id>/',    views.manage_pincodes,       name='manage_pincodes_district'),
    path('super-admin/notifications/',                 views.manage_notifications,  name='manage_notifications'),
    path('super-admin/analytics/',                     views.national_analytics,    name='national_analytics'),
    path('super-admin/flicks/',                        views.admin_flicks,          name='admin_flicks'),
    path('super-admin/feedback/',                      views.admin_feedback,         name='admin_feedback'),

    # ── STATE ADMIN ─────────────────────────────────────────
    path('state-admin/',                               views.state_admin_dashboard, name='state_admin_dashboard'),
    path('state-admin/district-admins/create/',        views.create_district_admin, name='create_district_admin'),
    path('state-admin/employers/',                     views.verify_employers,      name='verify_employers'),
    path('state-admin/users/<int:user_id>/suspend/',   views.suspend_user,          name='suspend_user'),
    path('state-admin/reports/',                       views.state_reports,         name='state_reports'),

    # ── DISTRICT ADMIN ──────────────────────────────────────
    path('district-admin/',                            views.district_admin_dashboard,   name='district_admin_dashboard'),
    path('district-admin/employers/',                  views.approve_employers_district, name='approve_employers_district'),
    path('district-admin/complaints/',                 views.handle_complaints,          name='handle_complaints'),
    path('district-admin/complaints/<int:complaint_id>/resolve/', views.resolve_complaint, name='resolve_complaint'),
    path('district-admin/reports/',                    views.district_reports,           name='district_reports'),

    # ── PUBLIC ──────────────────────────────────────────────
    path('complaint/submit/',                          views.submit_complaint,      name='submit_complaint'),

    # ── UTILITY ─────────────────────────────────────────────
    path('profile/',                                   views.profile_redirect,      name='profile_redirect'),
    path('profile/edit/',                              views.profile_edit,           name='profile_edit'),
    path('my-accounts/',                               views.my_accounts,            name='my_accounts'),
    path('notifications/mark-all-read/',               notifications.mark_all_read, name='mark_all_notifications_read'),
    path('about/',                                     views.about_page,                   name='about'),
    path('terms/',                                     views.terms,                        name='terms'),
    path('privacy/',                                   views.privacy,                      name='privacy'),

    # ── FLICKS ──────────────────────────────────────────────────────────────
    path('flicks/',                                    views.flicks_feed,                  name='flicks_feed'),
    path('flicks/post/',                               views.post_flick,                   name='post_flick'),
    path('flicks/<int:pk>/like/',                      views.like_flick,                   name='like_flick'),
    path('flicks/<int:pk>/comment/',                   views.comment_flick,                name='comment_flick'),
    path('flicks/<int:pk>/delete/',                    views.delete_flick,                 name='delete_flick'),
    path('flicks/<int:pk>/advertise/',                 views.flick_advertise,              name='flick_advertise'),
    path('flicks/<int:pk>/report/',                    views.report_flick,                 name='report_flick'),
    path('super-admin/flick-reports/',                 views.admin_flick_reports,          name='admin_flick_reports'),
    path('super-admin/offers/',                       views.manage_offers,                name='manage_offers'),
    path('super-admin/offers/<int:pk>/approve/',      views.offer_approve,                name='offer_approve'),
    path('super-admin/offers/<int:pk>/delete/',       views.offer_delete,                 name='offer_delete'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
