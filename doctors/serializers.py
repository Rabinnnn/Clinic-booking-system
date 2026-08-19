from rest_framework import serializers
from doctors.models import Doctor

class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ['id', 'name', 'working_hours_start', 'working_hours_end']