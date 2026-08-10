from django import forms
from django.utils import timezone
from .models import Appointment


class RescheduleForm(forms.Form):
    start_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
    )

    def __init__(self, *args, doctor=None, exclude_appointment=None, **kwargs):
        self.doctor = doctor
        self.exclude_appointment = exclude_appointment
        super().__init__(*args, **kwargs)

    def clean_start_time(self):
        start = self.cleaned_data["start_time"]
        if start <= timezone.now():
            raise forms.ValidationError("New time must be in the future.")

        qs = Appointment.objects.filter(
            doctor=self.doctor,
            status__in=[Appointment.Status.SCHEDULED, Appointment.Status.RESCHEDULED],
        )
        if self.exclude_appointment:
            qs = qs.exclude(pk=self.exclude_appointment.pk)
        if qs.filter(start_time=start).exists():  # replace with real overlap check
            raise forms.ValidationError("Doctor is not available at this time.")
        return start


class CancelForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea, required=False)