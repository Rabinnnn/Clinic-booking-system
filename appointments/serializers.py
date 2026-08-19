from rest_framework import serializers
from appointments.models import Appointment
from doctors.models import Doctor
from patients.models import Patient

class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ['id', 'doctor', 'patient', 'start_time', 'end_time', 'status', 'cancellation_reason', 'created_at']
        read_only_fields = ['id', 'end_time', 'status', 'cancellation_reason', 'created_at']


class BookAppointmentSerializer(serializers.Serializer):
    doctor_id = serializers.IntegerField()
    patient_id = serializers.IntegerField()
    start_time = serializers.DateTimeField()


class CancelAppointmentSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, allow_blank=False)


class RescheduleAppointmentSerializer(serializers.Serializer):
    new_start_time = serializers.DateTimeField()


class AvailabilitySlotSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()