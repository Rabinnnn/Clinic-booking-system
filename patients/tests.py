from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from patients.models import Patient


class PatientModelTest(TestCase):
    def test_create_patient(self):
        patient = Patient.objects.create(
            name="Alice",
            email="alice@example.com",
            phone="123456"
        )
        self.assertEqual(patient.name, "Alice")
        self.assertEqual(str(patient), "Alice")


class PatientAPITest(APITestCase):
    def setUp(self):
        self.patient = Patient.objects.create(
            name="Bob",
            email="bob@example.com"
        )

    def test_patient_list_get(self):
        url = reverse('patient-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_patient_list_post_creates_new(self):
        url = reverse('patient-list')
        data = {
            'name': 'Charlie',
            'email': 'charlie@example.com',
            'phone': '555-1234'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Patient.objects.count(), 2)
        self.assertEqual(response.data['name'], 'Charlie')

    def test_patient_appointments_endpoint(self):
        # We'll test with appointment data in appointments tests
        pass  # covered in appointments/tests.py