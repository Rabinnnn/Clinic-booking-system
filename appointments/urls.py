from django.urls import path
from appointments.views import (
    BookAppointmentView,
    CancelAppointmentView,
    RescheduleAppointmentView,
)

urlpatterns = [
    path('appointments', BookAppointmentView.as_view(), name='book-appointment'),
    path('appointments/<int:id>/cancel', CancelAppointmentView.as_view(), name='cancel-appointment'),
    path('appointments/<int:id>/reschedule', RescheduleAppointmentView.as_view(), name='reschedule-appointment'),
]