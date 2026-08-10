from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        PATIENT = "patient", "Patient"
        DOCTOR = "doctor", "Doctor"

    role = models.CharField(max_length=10, choices=Role.choices)
    phone = models.CharField(max_length=20, blank=True)


class DoctorProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        limit_choices_to={"role": "doctor"},
        related_name="doctor_profile",
    )
    specialty = models.CharField(max_length=100)
    bio = models.TextField(blank=True)

    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.username}"


class Appointment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        RESCHEDULED = "rescheduled", "Rescheduled"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="appointments"
    )
    doctor = models.ForeignKey(
        DoctorProfile, on_delete=models.CASCADE, related_name="appointments"
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SCHEDULED)
    reason = models.CharField(max_length=255, blank=True)
    cancellation_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_time"]
        constraints = [
            models.CheckConstraint(condition=models.Q(end_time__gt=models.F("start_time")), name="end_after_start"),
        ]

    def __str__(self):
        return f"{self.patient} with {self.doctor} at {self.start_time}"

    def is_upcoming(self):
        return self.start_time > timezone.now() and self.status in (
            self.Status.SCHEDULED, self.Status.RESCHEDULED
        )

    def can_be_modified(self):
        return self.is_upcoming() and (self.start_time - timezone.now()).total_seconds() > 86400


class AppointmentHistory(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name="history")
    action = models.CharField(max_length=20)  # "rescheduled", "cancelled"
    old_start_time = models.DateTimeField(null=True, blank=True)
    new_start_time = models.DateTimeField(null=True, blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-changed_at"]