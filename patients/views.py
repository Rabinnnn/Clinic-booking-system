from rest_framework.views import APIView
from rest_framework.response import Response

from appointments.services import get_patient_upcoming_appointments
from appointments.serializers import AppointmentSerializer


class PatientAppointmentsView(APIView):
    def get(self, request, id):
        appointments = get_patient_upcoming_appointments(id)
        serializer = AppointmentSerializer(appointments, many=True)
        return Response(serializer.data)