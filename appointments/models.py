from django.db import models
from django.db.models import Q
from doctors.models import Doctor
from patients.models import Patient

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('cancelled', 'Cancelled'),
    ]

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    cancellation_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # Prevents double-booking for active appointments
            models.UniqueConstraint(
                fields=['doctor', 'start_time'],
                condition=Q(status='scheduled'),
                name='unique_active_appointment'
            )
        ]
        indexes = [
            models.Index(fields=['doctor', 'start_time']),
            models.Index(fields=['patient']),
        ]
        ordering = ['start_time']

    def __str__(self):
        return f"{self.patient.name} with Dr. {self.doctor.name} at {self.start_time}"