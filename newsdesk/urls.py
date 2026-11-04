from django.urls import path
from . import views
from . import public_views

app_name = 'newsdesk'
urlpatterns = [
    path('', views.feed, name='feed'),
    path('share/', public_views.share, name='share'),
    path('share/otp/send/', public_views.send_otp, name='share_send_otp'),
    path('share/otp/verify/', public_views.verify_otp, name='share_verify_otp'),
    path('share/finish/', public_views.finish, name='share_finish'),
    path('share/status/<uuid:pk>/', public_views.submission_status, name='submission_status'),
    path('share/identity/<uuid:pk>/<str:kind>/', public_views.identity_file, name='identity_file'),
    path('desk/submissions/', public_views.submission_queue, name='submissions'),
    path('desk/submissions/<uuid:pk>/', public_views.review, name='review_submission'),
    path('stories/<int:pk>/', views.detail, name='detail'),
    path('stories/<int:pk>/comment/', views.comment, name='comment'),
    path('stories/<int:pk>/rate/', views.rate, name='rate'),
    path('comments/<int:pk>/report/', views.report, name='report'),
    path('media/<int:pk>/<str:kind>/', views.media, name='media'),
    path('desk/', views.manage, name='manage'),
    path('desk/new/', views.edit, name='create'),
    path('desk/<int:pk>/edit/', views.edit, name='edit'),
    path('desk/comments/<int:pk>/', views.moderate, name='moderate'),
    path('desk/agents/', views.agents, name='agents'),
    path('desk/agents/<int:pk>/', views.agents, name='agent_edit'),
    path('api/stories/', views.feed, name='api_feed'),
    path('api/pincodes/', views.pincodes, name='api_pincodes'),
    path('api/stories/<int:pk>/', views.detail, name='api_detail'),
    path('api/stories/<int:pk>/comments/', views.comment, name='api_comment'),
    path('api/stories/<int:pk>/rating/', views.rate, name='api_rate'),
    path('api/comments/<int:pk>/report/', views.report, name='api_report'),
    path('api/desk/', views.manage, name='api_manage'),
    path('api/desk/new/', views.edit, name='api_create'),
    path('api/desk/<int:pk>/', views.edit, name='api_edit'),
    path('api/desk/comments/<int:pk>/', views.moderate, name='api_moderate'),
    path('api/agents/', views.agents, name='api_agents'),
    path('api/agents/<int:pk>/', views.agents, name='api_agent_edit'),
]
