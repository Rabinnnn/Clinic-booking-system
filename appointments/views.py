from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from appointments.models import Appointment
from appointments.serializers import (
    AppointmentSerializer,
    BookAppointmentSerializer,
    CancelAppointmentSerializer,
    RescheduleAppointmentSerializer,
)
from appointments import services


class BookAppointmentView(APIView):
    def post(self, request):
        serializer = BookAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        appointment = services.book_appointment(
            doctor_id=serializer.validated_data['doctor_id'],
            patient_id=serializer.validated_data['patient_id'],
            start_time=serializer.validated_data['start_time'],
        )
        return Response(
            AppointmentSerializer(appointment).data,
            status=status.HTTP_201_CREATED
        )


class CancelAppointmentView(APIView):
    def patch(self, request, id):
        serializer = CancelAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        appointment = services.cancel_appointment(
            appointment_id=id,
            reason=serializer.validated_data['reason']
        )
        return Response(AppointmentSerializer(appointment).data)


class RescheduleAppointmentView(APIView):
    def patch(self, request, id):
        serializer = RescheduleAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_appointment = services.reschedule_appointment(
            appointment_id=id,
            new_start_time=serializer.validated_data['new_start_time']
        )
        return Response(AppointmentSerializer(new_appointment).data)