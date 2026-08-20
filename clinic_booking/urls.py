from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('appointments.urls')),
    path('api/', include('doctors.urls')),
    path('api/', include('patients.urls')),
    path('', include('frontend.urls')),
]