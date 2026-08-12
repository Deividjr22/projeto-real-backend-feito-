from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from .models import Appointment, User, APPOINTMENT_DURATION


class PatientSignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "phone", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.PATIENT
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        user.phone = self.cleaned_data.get("phone", "")
        if commit:
            user.save()
        return user


class BookAppointmentForm(forms.Form):
    start_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
    )
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"placeholder": "Briefly describe why you're booking (optional)"})
    )

    def __init__(self, *args, doctor=None, **kwargs):
        self.doctor = doctor
        super().__init__(*args, **kwargs)

    def clean_start_time(self):
        start = self.cleaned_data["start_time"]
        if start <= timezone.now():
            raise forms.ValidationError("Appointment time must be in the future.")

        end = start + APPOINTMENT_DURATION
        overlapping = Appointment.objects.filter(
            doctor=self.doctor,
            status__in=[Appointment.Status.SCHEDULED, Appointment.Status.RESCHEDULED],
            start_time__lt=end,
            end_time__gt=start,
        )
        if overlapping.exists():
            raise forms.ValidationError("This doctor is not available at that time. Please pick another slot.")
        return start


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

        end = start + APPOINTMENT_DURATION
        qs = Appointment.objects.filter(
            doctor=self.doctor,
            status__in=[Appointment.Status.SCHEDULED, Appointment.Status.RESCHEDULED],
            start_time__lt=end,
            end_time__gt=start,
        )
        if self.exclude_appointment:
            qs = qs.exclude(pk=self.exclude_appointment.pk)
        if qs.exists():
            raise forms.ValidationError("Doctor is not available at this time.")
        return start


class CancelForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea, required=False)