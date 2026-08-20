from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.db import IntegrityError
from django.shortcuts import get_object_or_404

from doctors.models import Doctor
from patients.models import Patient
from appointments.models import Appointment
from appointments.exceptions import SlotUnavailableError, InvalidOperationError

SLOT_DURATION = 30  # minutes
MIN_ADVANCE = 60    # minutes (1 hour buffer)


def generate_slots(doctor, date):
    """
    Generate all available 30-min slots for a doctor on a given date.
    Returns a list of (start_time, end_time) tuples (naive, but with date).
    """
    start_dt = datetime.combine(date, doctor.working_hours_start)
    end_dt = datetime.combine(date, doctor.working_hours_end)

    # Make timezone-aware if USE_TZ=True
    if timezone.is_aware(start_dt):
        start_dt = timezone.make_aware(start_dt)
        end_dt = timezone.make_aware(end_dt)
    else:
        # If they're naive, make them aware using the default timezone
        start_dt = timezone.make_aware(start_dt)
        end_dt = timezone.make_aware(end_dt)

    slots = []
    current = start_dt
    while current < end_dt:
        slots.append((current, current + timedelta(minutes=SLOT_DURATION)))
        current += timedelta(minutes=SLOT_DURATION)
    return slots


def get_available_slots(doctor_id, date):
    """
    Return list of free slots for a given doctor on a given date.
    Each slot: {'start': ISO datetime, 'end': ISO datetime}
    """
    doctor = get_object_or_404(Doctor, id=doctor_id)
    all_slots = generate_slots(doctor, date)

    # Fetch already booked slots for that doctor and day
    day_start = datetime.combine(date, datetime.min.time())
    day_end = datetime.combine(date, datetime.max.time())

    day_start = timezone.make_aware(day_start)
    day_end = timezone.make_aware(day_end)

    booked = Appointment.objects.filter(
        doctor=doctor,
        status='scheduled',
        start_time__gte=day_start,
        start_time__lt=day_end
    ).values_list('start_time', flat=True)

    booked_set = set(booked)

    available = []
    for start, end in all_slots:
        if start not in booked_set:
            available.append({
                'start': start.isoformat(),
                'end': end.isoformat()
            })
    return available


def validate_slot(doctor, start_time, patient=None, check_advance=True):
    """
    Validate a slot for booking:
    - Must be on 30-min boundary.
    - Must be within working hours.
    - Must not be in the past.
    - Must respect 1-hour advance buffer (if check_advance).
    - Must not be already booked.
    """
    # 1. Boundary check (minute must be 0 or 30)
    if start_time.minute not in (0, 30):
        raise InvalidOperationError("Slot must start on the hour or half-hour.")

    # 2. Within working hours
    work_start = datetime.combine(start_time.date(), doctor.working_hours_start)
    work_end = datetime.combine(start_time.date(), doctor.working_hours_end)
    if timezone.is_aware(start_time):
        work_start = timezone.make_aware(work_start)
        work_end = timezone.make_aware(work_end)

    if start_time < work_start or start_time >= work_end:
        raise InvalidOperationError("Slot outside doctor's working hours.")

    end_time = start_time + timedelta(minutes=SLOT_DURATION)
    if end_time > work_end:
        raise InvalidOperationError("Slot exceeds working hours.")

    # 3. Not in the past
    now = timezone.now()
    if start_time < now:
        raise InvalidOperationError("Cannot book a slot in the past.")

    # 4. 1-hour advance buffer (bonus)
    if check_advance and (start_time - now).total_seconds() < MIN_ADVANCE * 60:
        raise InvalidOperationError(
            f"Bookings must be at least {MIN_ADVANCE} minutes in advance."
        )

    # 5. Not already booked (by an active appointment)
    if Appointment.objects.filter(
        doctor=doctor,
        start_time=start_time,
        status='scheduled'
    ).exists():
        raise SlotUnavailableError("This slot is already taken.")

    return end_time


@transaction.atomic
def book_appointment(doctor_id, patient_id, start_time):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    patient = get_object_or_404(Patient, id=patient_id)

    end_time = validate_slot(doctor, start_time)

    try:
        appointment = Appointment.objects.create(
            doctor=doctor,
            patient=patient,
            start_time=start_time,
            end_time=end_time,
            status='scheduled'
        )
        return appointment
    except IntegrityError:
        # In case of race condition (unique constraint violation)
        raise SlotUnavailableError("Slot was just taken by another request.")


@transaction.atomic
def cancel_appointment(appointment_id, reason):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if appointment.status == 'cancelled':
        raise InvalidOperationError("Appointment is already cancelled.")

    appointment.status = 'cancelled'
    appointment.cancellation_reason = reason
    appointment.save()
    return appointment


@transaction.atomic
def reschedule_appointment(appointment_id, new_start_time):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if appointment.status == 'cancelled':
        raise InvalidOperationError("Cannot reschedule a cancelled appointment.")

    # Validate the new slot (same doctor)
    doctor = appointment.doctor
    end_time = validate_slot(doctor, new_start_time)

    # Cancel original (soft delete)
    appointment.status = 'cancelled'
    appointment.cancellation_reason = f"Rescheduled to {new_start_time.isoformat()}"
    appointment.save()

    # Create new appointment
    try:
        new_appointment = Appointment.objects.create(
            doctor=doctor,
            patient=appointment.patient,
            start_time=new_start_time,
            end_time=end_time,
            status='scheduled'
        )
        return new_appointment
    except IntegrityError:
        # Rollback will happen automatically due to @transaction.atomic
        raise SlotUnavailableError("New slot was just taken by another request.")


def get_patient_upcoming_appointments(patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    now = timezone.now()
    return Appointment.objects.filter(
        patient=patient,
        status='scheduled',
        start_time__gte=now
    ).order_by('start_time')