from django.urls import path
from . import local_ride

urlpatterns = [
    path('', local_ride.feed, name='ride_feed'),
    path('post/', local_ride.create, name='ride_create'),
    path('mine/', local_ride.mine, name='ride_mine'),
    path('<int:pk>/', local_ride.detail, name='ride_detail'),
    path('<int:pk>/join/', local_ride.join, name='ride_join'),
    path('<int:pk>/withdraw/', local_ride.withdraw, name='ride_withdraw'),
    path('<int:pk>/status/', local_ride.change_status, name='ride_status'),
    path('<int:pk>/requests/<int:request_id>/review/', local_ride.review, name='ride_review'),
    path('<int:pk>/requests/<int:request_id>/chat/', local_ride.chat, name='ride_chat'),
]
