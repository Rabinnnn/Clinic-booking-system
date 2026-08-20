from django.urls import path
from doctors.views import DoctorAvailabilityView
from doctors.views import DoctorListView
from doctors.views import DoctorAppointmentsView



urlpatterns = [
    path('doctors/<int:id>/availability', DoctorAvailabilityView.as_view(), name='doctor-availability'),
    path('doctors', DoctorListView.as_view(), name='doctor-list'), 
    path('doctors/<int:id>/appointments', DoctorAppointmentsView.as_view(), name='doctor-appointments'),
]