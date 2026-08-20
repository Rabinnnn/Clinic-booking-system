from django.test import TestCase
from django.utils import timezone
from datetime import datetime, time
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from doctors.models import Doctor
from patients.models import Patient
from appointments.models import Appointment


class DoctorModelTest(TestCase):
    def test_create_doctor(self):
        doctor = Doctor.objects.create(
            name="Smith",
            working_hours_start=time(9, 0),
            working_hours_end=time(17, 0)
        )
        self.assertEqual(doctor.name, "Smith")
        self.assertEqual(str(doctor), "Dr. Smith")


class DoctorAvailabilityAPITest(APITestCase):
    def setUp(self):
        self.doctor = Doctor.objects.create(
            name="Johnson",
            working_hours_start=time(9, 0),
            working_hours_end=time(17, 0)
        )
        self.patient = Patient.objects.create(
            name="John Doe",
            email="john@example.com"
        )
        # Book one slot to make it unavailable
        self.booked_time = timezone.make_aware(
            datetime.combine(
                timezone.now().date() + timezone.timedelta(days=1),
                time(10, 0)
            )
        )
        Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.booked_time,
            end_time=self.booked_time + timezone.timedelta(minutes=30),
            status='scheduled'
        )

    def test_availability_returns_available_slots(self):
        date = (timezone.now() + timezone.timedelta(days=1)).date()
        url = reverse('doctor-availability', kwargs={'id': self.doctor.id})
        response = self.client.get(url, {'date': date.isoformat()})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        slots = response.data['slots']
        # Should not include the booked slot at 10:00
        times = [slot['start'] for slot in slots]
        self.assertNotIn(self.booked_time.isoformat(), times)
        # Should include other slots (e.g., 9:00, 9:30, etc.)
        # We can check that at least one slot exists
        self.assertTrue(len(slots) > 0)

    def test_availability_missing_date_returns_error(self):
        url = reverse('doctor-availability', kwargs={'id': self.doctor.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_doctor_appointments_endpoint(self):
        url = reverse('doctor-appointments', kwargs={'id': self.doctor.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return the booked appointment
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['doctor'], self.doctor.id)

    def test_doctor_list(self):
        url = reverse('doctor-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)