# scheduling/services.py
from datetime import datetime, timedelta
from .models import Availability, Appointment


def get_available_slots(doctor, date):
    weekday = date.weekday()
    availabilities = Availability.objects.filter(doctor=doctor, weekday=weekday)
    booked = Appointment.objects.filter(
        doctor=doctor, date=date, status__in=["scheduled", "confirmed"]
    ).values_list("start_time", flat=True)

    slots = []
    duration = timedelta(minutes=doctor.consultation_duration)

    for window in availabilities:
        current = datetime.combine(date, window.start_time)
        end = datetime.combine(date, window.end_time)
        while current + duration <= end:
            slot_time = current.time()
            if slot_time not in booked:
                slots.append(slot_time)
            current += duration

    return slots
