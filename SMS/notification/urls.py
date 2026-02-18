from django.urls import path
from . import views

app_name = 'notification'

urlpatterns = [
    # Notifications
    path('', views.notification_list, name='notification_list'),
    path('create/', views.create_notification, name='create_notification'),
    path('<int:notif_id>/', views.notification_detail, name='notification_detail'),
    path('<int:notif_id>/edit/', views.edit_notification, name='edit_notification'),
    path('<int:notif_id>/delete/', views.delete_notification, name='delete_notification'),

    # Timetables
    path('timetables/', views.timetable_list, name='timetable_list'),
    path('timetables/create/', views.create_timetable, name='create_timetable'),
    path('timetables/<int:tt_id>/edit/', views.edit_timetable, name='edit_timetable'),
    path('timetables/<int:tt_id>/delete/', views.delete_timetable, name='delete_timetable'),
]
