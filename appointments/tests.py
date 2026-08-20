from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta, time
from rest_framework.test import APITestCase
from rest_framework import status

from doctors.models import Doctor
from patients.models import Patient
from appointments.models import Appointment
from appointments.services import (
    generate_slots,
    get_available_slots,
    validate_slot,
    book_appointment,
    cancel_appointment,
    reschedule_appointment,
    get_patient_upcoming_appointments,
    SLOT_DURATION,
    MIN_ADVANCE
)
from appointments.exceptions import SlotUnavailableError, InvalidOperationError


# -------- Helper to create a future date --------
def future_date(days_ahead=1):
    return (timezone.now() + timedelta(days=days_ahead)).date()


# -------- Model Tests --------
class AppointmentModelTest(TestCase):
    def setUp(self):
        self.doctor = Doctor.objects.create(
            name="Smith",
            working_hours_start=time(9, 0),
            working_hours_end=time(17, 0)
        )
        self.patient = Patient.objects.create(
            name="John",
            email="john@example.com"
        )

    def test_create_appointment(self):
        start = timezone.make_aware(
            datetime.combine(future_date(), time(10, 0))
        )
        end = start + timedelta(minutes=30)
        appt = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=start,
            end_time=end,
            status='scheduled'
        )
        self.assertEqual(appt.status, 'scheduled')
        self.assertEqual(str(appt), f"John with Dr. Smith at {start}")


# -------- Service Tests --------
class ServiceTests(TestCase):
    def setUp(self):
        self.doctor = Doctor.objects.create(
            name="Williams",
            working_hours_start=time(9, 0),
            working_hours_end=time(17, 0)
        )
        self.patient = Patient.objects.create(
            name="Jane",
            email="jane@example.com"
        )

    def test_generate_slots_within_global_cap(self):
        # Doctor works 9-17, global is 8-17, so slots 9-17
        date = future_date()
        slots = generate_slots(self.doctor, date)
        # Should start at 9:00
        self.assertEqual(slots[0][0].hour, 9)
        self.assertEqual(slots[0][0].minute, 0)
        # Should end at 16:30 (last slot starts 16:30, ends 17:00)
        self.assertEqual(slots[-1][1].hour, 17)
        self.assertEqual(slots[-1][1].minute, 0)
        # Number of slots: 8 hours * 2 = 16 slots (9-17 = 8 hours = 16 slots of 30min)
        self.assertEqual(len(slots), 16)

    def test_generate_slots_respects_global_8_5(self):
        # Doctor works 7-19, but global caps 8-17
        doctor = Doctor.objects.create(
            name="LongHours",
            working_hours_start=time(7, 0),
            working_hours_end=time(19, 0)
        )
        date = future_date()
        slots = generate_slots(doctor, date)
        self.assertEqual(slots[0][0].hour, 8)   # starts at 8:00
        self.assertEqual(slots[-1][1].hour, 17) # ends at 17:00
        self.assertEqual(len(slots), 18)  # 9 hours * 2 = 18 slots

    def test_validate_slot_happy_path(self):
        start = timezone.make_aware(
            datetime.combine(future_date(2), time(10, 0))
        )
        end = validate_slot(self.doctor, start)
        self.assertEqual(end, start + timedelta(minutes=30))

    def test_validate_slot_invalid_minute(self):
        start = timezone.make_aware(
            datetime.combine(future_date(2), time(10, 15))
        )
        with self.assertRaises(InvalidOperationError):
            validate_slot(self.doctor, start)

    def test_validate_slot_outside_working_hours(self):
        start = timezone.make_aware(
            datetime.combine(future_date(2), time(18, 0))
        )
        with self.assertRaises(InvalidOperationError):
            validate_slot(self.doctor, start)

    def test_validate_slot_past(self):
        past = timezone.now() - timedelta(days=1)
        with self.assertRaises(InvalidOperationError):
            validate_slot(self.doctor, past)

    def test_validate_slot_advance_buffer(self):
        # less than MIN_ADVANCE from now
        close = timezone.now() + timedelta(minutes=30)
        with self.assertRaises(InvalidOperationError):
            validate_slot(self.doctor, close)

    def test_book_appointment_success(self):
        start = timezone.make_aware(
            datetime.combine(future_date(3), time(11, 0))
        )
        appt = book_appointment(self.doctor.id, self.patient.id, start)
        self.assertEqual(appt.status, 'scheduled')
        self.assertEqual(appt.doctor, self.doctor)
        self.assertEqual(appt.patient, self.patient)

    def test_book_appointment_duplicate_fails(self):
        start = timezone.make_aware(
            datetime.combine(future_date(3), time(14, 0))
        )
        book_appointment(self.doctor.id, self.patient.id, start)
        with self.assertRaises(SlotUnavailableError):
            book_appointment(self.doctor.id, self.patient.id, start)

    def test_cancel_appointment(self):
        start = timezone.make_aware(
            datetime.combine(future_date(3), time(15, 0))
        )
        appt = book_appointment(self.doctor.id, self.patient.id, start)
        cancelled = cancel_appointment(appt.id, "Too busy")
        self.assertEqual(cancelled.status, 'cancelled')
        self.assertEqual(cancelled.cancellation_reason, "Too busy")

    def test_cancel_already_cancelled_fails(self):
        start = timezone.make_aware(
            datetime.combine(future_date(3), time(16, 0))
        )
        appt = book_appointment(self.doctor.id, self.patient.id, start)
        cancel_appointment(appt.id, "First")
        with self.assertRaises(InvalidOperationError):
            cancel_appointment(appt.id, "Second")

    def test_reschedule_appointment(self):
        original = timezone.make_aware(
            datetime.combine(future_date(3), time(9, 0))
        )
        new = timezone.make_aware(
            datetime.combine(future_date(3), time(14, 0))
        )
        appt = book_appointment(self.doctor.id, self.patient.id, original)
        new_appt = reschedule_appointment(appt.id, new)
        # Original should be cancelled
        appt.refresh_from_db()
        self.assertEqual(appt.status, 'cancelled')
        self.assertIsNotNone(appt.cancellation_reason)
        # New appointment exists
        self.assertEqual(new_appt.start_time, new)
        self.assertEqual(new_appt.status, 'scheduled')


# -------- API Endpoint Tests --------
class AppointmentAPITest(APITestCase):
    def setUp(self):
        self.doctor = Doctor.objects.create(
            name="Brown",
            working_hours_start=time(9, 0),
            working_hours_end=time(17, 0)
        )
        self.patient = Patient.objects.create(
            name="Alice",
            email="alice@example.com"
        )
        self.valid_start = timezone.make_aware(
            datetime.combine(future_date(2), time(10, 0))
        )
        self.book_url = reverse('book-appointment')
        self.cancel_url_base = '/api/appointments/{}/cancel'
        self.reschedule_url_base = '/api/appointments/{}/reschedule'

    def test_book_appointment_success(self):
        data = {
            'doctor_id': self.doctor.id,
            'patient_id': self.patient.id,
            'start_time': self.valid_start.isoformat()
        }
        response = self.client.post(self.book_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'scheduled')
        self.assertEqual(Appointment.objects.count(), 1)

    def test_book_appointment_conflict(self):
        # Book a slot
        data = {
            'doctor_id': self.doctor.id,
            'patient_id': self.patient.id,
            'start_time': self.valid_start.isoformat()
        }
        self.client.post(self.book_url, data, format='json')
        # Try to book same slot again
        response = self.client.post(self.book_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('error', response.data)

    def test_book_appointment_past_date_fails(self):
        past = (timezone.now() - timedelta(days=1)).isoformat()
        data = {
            'doctor_id': self.doctor.id,
            'patient_id': self.patient.id,
            'start_time': past
        }
        response = self.client.post(self.book_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_cancel_appointment_success(self):
        appt = book_appointment(
            self.doctor.id,
            self.patient.id,
            self.valid_start
        )
        url = self.cancel_url_base.format(appt.id)
        response = self.client.patch(url, {'reason': 'Changed mind'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'cancelled')
        self.assertEqual(response.data['cancellation_reason'], 'Changed mind')

    def test_cancel_already_cancelled_fails(self):
        appt = book_appointment(
            self.doctor.id,
            self.patient.id,
            self.valid_start
        )
        cancel_appointment(appt.id, "First")
        url = self.cancel_url_base.format(appt.id)
        response = self.client.patch(url, {'reason': 'Second'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


    def test_reschedule_cancelled_fails(self):
        appt = book_appointment(self.doctor.id, self.patient.id, self.valid_start)
        cancel_appointment(appt.id, "Cancel")
        new = timezone.make_aware(
            datetime.combine(future_date(3), time(14, 0))
        )
        url = self.reschedule_url_base.format(appt.id)
        response = self.client.patch(url, {'new_start_time': new.isoformat()}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_patient_appointments_sorted(self):
        # Create two appointments on different days
        day1 = timezone.make_aware(
            datetime.combine(future_date(5), time(10, 0))
        )
        day2 = timezone.make_aware(
            datetime.combine(future_date(5), time(12, 0))
        )
        appt1 = book_appointment(self.doctor.id, self.patient.id, day1)
        appt2 = book_appointment(self.doctor.id, self.patient.id, day2)
        url = reverse('patient-appointments', kwargs={'id': self.patient.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        # Check order (earliest first)
        self.assertEqual(response.data[0]['id'], appt1.id)
        self.assertEqual(response.data[1]['id'], appt2.id)