from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from doctors.models import Doctor
from patients.models import Patient
from appointments.models import Appointment


class Command(BaseCommand):
    help = 'Populate the database with sample doctors, patients, and appointments'

    def handle(self, *args, **options):
        self.stdout.write('🌱 Populating database...')

        # ----- 1. Create Doctors -----
        doctors_data = [
            {'name': 'Smith', 'working_hours_start': '09:00', 'working_hours_end': '17:00'},
            {'name': 'Johnson', 'working_hours_start': '08:00', 'working_hours_end': '16:00'},
            {'name': 'Williams', 'working_hours_start': '10:00', 'working_hours_end': '18:00'},
            {'name': 'Brown', 'working_hours_start': '09:00', 'working_hours_end': '13:00'},
            {'name': 'Jones', 'working_hours_start': '13:00', 'working_hours_end': '17:00'},
        ]

        doctors = []
        for data in doctors_data:
            doctor, created = Doctor.objects.get_or_create(
                name=data['name'],
                defaults={
                    'working_hours_start': data['working_hours_start'],
                    'working_hours_end': data['working_hours_end'],
                }
            )
            doctors.append(doctor)
            status = '✅ Created' if created else '⏭️ Already exists'
            self.stdout.write(f'  {status}: Dr. {doctor.name} ({doctor.working_hours_start}–{doctor.working_hours_end})')

        # ----- 2. Create Patients -----
        patients_data = [
            {'name': 'John Doe', 'email': 'john@example.com', 'phone': '555-0101'},
            {'name': 'Jane Smith', 'email': 'jane@example.com', 'phone': '555-0102'},
            {'name': 'Bob Johnson', 'email': 'bob@example.com', 'phone': '555-0103'},
            {'name': 'Alice Williams', 'email': 'alice@example.com', 'phone': '555-0104'},
            {'name': 'Charlie Brown', 'email': 'charlie@example.com', 'phone': '555-0105'},
            {'name': 'Diana Jones', 'email': 'diana@example.com', 'phone': '555-0106'},
            {'name': 'Eve Davis', 'email': 'eve@example.com', 'phone': '555-0107'},
            {'name': 'Frank Wilson', 'email': 'frank@example.com', 'phone': '555-0108'},
        ]

        patients = []
        for data in patients_data:
            patient, created = Patient.objects.get_or_create(
                email=data['email'],
                defaults={
                    'name': data['name'],
                    'phone': data['phone'],
                }
            )
            patients.append(patient)
            status = '✅ Created' if created else '⏭️ Already exists'
            self.stdout.write(f'  {status}: {patient.name} ({patient.email})')

        # ----- 3. Create Appointments (in the future) -----
        now = timezone.now()
        # Clear existing appointments to avoid duplicates? Let's just create new ones
        # but we'll check if they exist to avoid duplicates.

        # We'll create appointments for the next 3 days, at various times
        base_date = now.date()
        appointments_to_create = []

        # Some appointments for today (if not already passed)
        for i, doctor in enumerate(doctors[:3]):
            # Pick a patient (cycle through patients)
            patient = patients[i % len(patients)]
            # Start at 10:00, 11:00, 14:00
            hour = 10 + i
            if hour >= 18:
                hour = 10  # fallback
            start_time = timezone.make_aware(
                datetime(base_date.year, base_date.month, base_date.day, hour, 0)
            )
            # Skip if in the past (we'll skip if less than now+1 hour)
            if start_time < now + timedelta(hours=1):
                start_time = now + timedelta(hours=1 + i)  # shift to future
                # Ensure it's on a half-hour boundary
                if start_time.minute > 30:
                    start_time = start_time.replace(minute=0) + timedelta(hours=1)
                elif start_time.minute > 0:
                    start_time = start_time.replace(minute=30)

            end_time = start_time + timedelta(minutes=30)

            # Check if it already exists
            exists = Appointment.objects.filter(
                doctor=doctor,
                start_time=start_time,
                status='scheduled'
            ).exists()
            if not exists:
                appointments_to_create.append(
                    Appointment(
                        doctor=doctor,
                        patient=patient,
                        start_time=start_time,
                        end_time=end_time,
                        status='scheduled'
                    )
                )

        # Create appointments for tomorrow and the day after
        for day_offset in [1, 2]:
            day_date = base_date + timedelta(days=day_offset)
            for i, doctor in enumerate(doctors):
                patient = patients[(i + 2) % len(patients)]
                hour = 9 + (i * 2) % 8  # spread across working hours
                if hour >= 17:
                    hour = 9
                start_time = timezone.make_aware(
                    datetime(day_date.year, day_date.month, day_date.day, hour, 0)
                )
                # Ensure on half-hour
                if start_time.minute not in (0, 30):
                    start_time = start_time.replace(minute=30)

                end_time = start_time + timedelta(minutes=30)

                # Check if it already exists
                exists = Appointment.objects.filter(
                    doctor=doctor,
                    start_time=start_time,
                    status='scheduled'
                ).exists()
                if not exists and start_time > now + timedelta(hours=1):
                    appointments_to_create.append(
                        Appointment(
                            doctor=doctor,
                            patient=patient,
                            start_time=start_time,
                            end_time=end_time,
                            status='scheduled'
                        )
                    )

        # Bulk create appointments
        if appointments_to_create:
            Appointment.objects.bulk_create(appointments_to_create)
            self.stdout.write(f'  ✅ Created {len(appointments_to_create)} new appointments')
        else:
            self.stdout.write('  ⏭️ No new appointments created (all exist already)')

        # ----- 4. Summary -----
        total_doctors = Doctor.objects.count()
        total_patients = Patient.objects.count()
        total_appointments = Appointment.objects.filter(status='scheduled').count()
        self.stdout.write(self.style.SUCCESS(
            f'\n🎉 Done! '
            f'{total_doctors} doctors, '
            f'{total_patients} patients, '
            f'{total_appointments} upcoming appointments.'
        ))