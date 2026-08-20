from django.urls import path
from patients.views import PatientAppointmentsView
from patients.views import PatientListView


urlpatterns = [
    path('patients/<int:id>/appointments', PatientAppointmentsView.as_view(), name='patient-appointments'),
    path('patients', PatientListView.as_view(), name='patient-list'),
]