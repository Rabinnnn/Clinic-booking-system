from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from appointments.models import Appointment
from appointments.serializers import AppointmentSerializer

from rest_framework import generics
from datetime import datetime

from appointments.services import get_available_slots
from appointments.serializers import AvailabilitySlotSerializer
from doctors.models import Doctor
from doctors.serializers import DoctorSerializer


class DoctorAvailabilityView(APIView):
    def get(self, request, id):
        date_str = request.query_params.get('date')
        if not date_str:
            return Response(
                {'error': 'Missing date parameter. Use ?date=YYYY-MM-DD'},
                status=400
            )
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=400
            )

        slots = get_available_slots(id, date)
        serializer = AvailabilitySlotSerializer(slots, many=True)
        return Response({'slots': serializer.data})

class DoctorListView(generics.ListAPIView):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer

class DoctorAppointmentsView(APIView):
    def get(self, request, id):
        doctor = get_object_or_404(Doctor, id=id)
        now = timezone.now()
        appointments = Appointment.objects.filter(
            doctor=doctor,
            status='scheduled',
            start_time__gte=now
        ).order_by('start_time')
        serializer = AppointmentSerializer(appointments, many=True)

        return Response(serializer.data)