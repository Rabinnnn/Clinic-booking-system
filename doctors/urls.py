from django.urls import path
from doctors.views import DoctorAvailabilityView

urlpatterns = [
    path('doctors/<int:id>/availability', DoctorAvailabilityView.as_view(), name='doctor-availability'),
]