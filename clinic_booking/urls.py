from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('appointments.urls')),
    path('api/', include('doctors.urls')),
    path('api/', include('patients.urls')),
    path('', include('frontend.urls')),
]

# Serve static files even when DEBUG=False (via WhiteNoise)
if not settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)