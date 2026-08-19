from django.urls import path
from patients.views import PatientAppointmentsView

urlpatterns = [
    path('patients/<int:id>/appointments', PatientAppointmentsView.as_view(), name='patient-appointments'),
]