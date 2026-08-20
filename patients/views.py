from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics


from appointments.services import get_patient_upcoming_appointments
from appointments.serializers import AppointmentSerializer
from patients.models import Patient
from patients.serializers import PatientSerializer


class PatientAppointmentsView(APIView):
    def get(self, request, id):
        appointments = get_patient_upcoming_appointments(id)
        serializer = AppointmentSerializer(appointments, many=True)
        return Response(serializer.data)

class PatientListView(generics.ListCreateAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer