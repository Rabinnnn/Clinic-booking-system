from django.db import models

class Doctor(models.Model):
    name = models.CharField(max_length=100)
    working_hours_start = models.TimeField()   # e.g., 09:00:00
    working_hours_end = models.TimeField()     # e.g., 17:00:00

    def __str__(self):
        return f"Dr. {self.name}"