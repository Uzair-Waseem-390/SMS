
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static



def index(request):
    return render(request, 'index.html')

# Apps scoped to a specific school and branch
scoped_patterns = [
    path('academics/', include('academics.urls')),
    path('students/', include('students.urls')),
    path('staff/', include('staff.urls')),
    path('attendance/', include('attendance.urls')),
    path('exams/', include('exams.urls')),
    path('notifications/', include('notification.urls')),
    path('finance/', include('finance.urls')),
    path('certificate/', include('certificate.urls')),
]

urlpatterns = [
    path('', TemplateView.as_view(template_name='index.html'), name='index'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('tenants/', include('tenants.urls')),

    # All branch-specific apps are under /school/<id>/branch/<id>/
    path('school/<int:school_id>/branch/<int:branch_id>/', include(scoped_patterns)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
