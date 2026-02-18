
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static



def index(request):
    return render(request, 'index.html')

urlpatterns = [
    path('', TemplateView.as_view(template_name='index.html'), name='index'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('tenants/', include('tenants.urls')),
    path('academics/', include('academics.urls')),
    path('students/', include('students.urls')),
    path('staff/', include('staff.urls')),
    path('attendance/', include('attendance.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)