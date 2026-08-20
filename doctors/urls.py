from django.urls import path
from doctors.views import DoctorAvailabilityView
from doctors.views import DoctorListView


urlpatterns = [
    path('doctors/<int:id>/availability', DoctorAvailabilityView.as_view(), name='doctor-availability'),
    path('doctors', DoctorListView.as_view(), name='doctor-list'), 
]