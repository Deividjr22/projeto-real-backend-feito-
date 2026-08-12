from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, FormView, CreateView

from .models import User, DoctorProfile, Appointment, AppointmentHistory, APPOINTMENT_DURATION
from .forms import PatientSignUpForm, BookAppointmentForm, RescheduleForm, CancelForm


class SignUpView(CreateView):
    form_class = PatientSignUpForm
    template_name = "agenda/signup.html"
    success_url = "/"

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, "Welcome! Your account has been created.")
        return response


class DashboardRedirectView(LoginRequiredMixin, View):
    """Sends each user to the right home screen after login."""
    def get(self, request):
        if request.user.role == User.Role.DOCTOR:
            return redirect("agenda:doctor_appointments")
        return redirect("agenda:my_appointments")


class MyAppointmentsView(LoginRequiredMixin, ListView):
    """Patient-facing view: their own appointments."""
    model = Appointment
    template_name = "agenda/my_appointments.html"
    context_object_name = "appointments"

    def get_queryset(self):
        return Appointment.objects.filter(patient=self.request.user).select_related("doctor__user")


class DoctorAppointmentsView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Doctor-facing view: their patient roster."""
    model = Appointment
    template_name = "agenda/doctor_appointments.html"
    context_object_name = "appointments"

    def test_func(self):
        return self.request.user.role == User.Role.DOCTOR

    def get_queryset(self):
        return Appointment.objects.filter(
            doctor__user=self.request.user
        ).select_related("patient").order_by("start_time")


class DoctorListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Patient-facing view: browse doctors to book with."""
    model = DoctorProfile
    template_name = "agenda/doctor_list.html"
    context_object_name = "doctors"

    def test_func(self):
        return self.request.user.role == User.Role.PATIENT

    def get_queryset(self):
        return DoctorProfile.objects.select_related("user").order_by("user__first_name")


class BookAppointmentView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """Patient-facing view: book a slot with a specific doctor."""
    template_name = "agenda/book_appointment.html"
    form_class = BookAppointmentForm

    def test_func(self):
        return self.request.user.role == User.Role.PATIENT

    def get_doctor(self):
        if not hasattr(self, "doctor"):
            self.doctor = get_object_or_404(DoctorProfile, pk=self.kwargs["pk"])
        return self.doctor

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["doctor"] = self.get_doctor()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["doctor"] = self.get_doctor()
        return context

    def form_valid(self, form):
        start = form.cleaned_data["start_time"]
        end = start + APPOINTMENT_DURATION
        appt = Appointment.objects.create(
            patient=self.request.user,
            doctor=self.get_doctor(),
            start_time=start,
            end_time=end,
            reason=form.cleaned_data.get("reason", ""),
            status=Appointment.Status.SCHEDULED,
        )
        AppointmentHistory.objects.create(
            appointment=appt,
            action="booked",
            new_start_time=start,
            changed_by=self.request.user,
        )
        messages.success(self.request, "Appointment booked.")
        return redirect("agenda:my_appointments")


class PatientOwnerMixin(UserPassesTestMixin):
    """Only the patient who owns the appointment may proceed (used for reschedule)."""
    def get_object(self):
        if not hasattr(self, "appointment"):
            self.appointment = get_object_or_404(Appointment, pk=self.kwargs["pk"])
        return self.appointment

    def test_func(self):
        return self.get_object().patient_id == self.request.user.id


class PatientOrDoctorMixin(UserPassesTestMixin):
    """Either the owning patient or the assigned doctor may proceed (used for cancel)."""
    def get_object(self):
        if not hasattr(self, "appointment"):
            self.appointment = get_object_or_404(Appointment, pk=self.kwargs["pk"])
        return self.appointment

    def test_func(self):
        appt = self.get_object()
        user = self.request.user
        return appt.patient_id == user.id or appt.doctor.user_id == user.id


class RescheduleAppointmentView(LoginRequiredMixin, PatientOwnerMixin, FormView):
    template_name = "agenda/reschedule.html"
    form_class = RescheduleForm

    def dispatch(self, request, *args, **kwargs):
        appt = self.get_object()
        if not appt.can_be_modified():
            messages.error(request, "This appointment can no longer be rescheduled.")
            return redirect("agenda:my_appointments")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        appt = self.get_object()
        kwargs["doctor"] = appt.doctor
        kwargs["exclude_appointment"] = appt
        return kwargs

    def form_valid(self, form):
        appt = self.get_object()
        old_start = appt.start_time
        new_start = form.cleaned_data["start_time"]
        duration = appt.end_time - appt.start_time

        appt.start_time = new_start
        appt.end_time = new_start + duration
        appt.status = Appointment.Status.RESCHEDULED
        appt.save()

        AppointmentHistory.objects.create(
            appointment=appt,
            action="rescheduled",
            old_start_time=old_start,
            new_start_time=new_start,
            changed_by=self.request.user,
        )
        messages.success(self.request, "Appointment rescheduled.")
        return redirect("agenda:my_appointments")


class CancelAppointmentView(LoginRequiredMixin, PatientOrDoctorMixin, FormView):
    template_name = "agenda/cancel.html"
    form_class = CancelForm

    def dispatch(self, request, *args, **kwargs):
        appt = self.get_object()
        if not appt.can_be_modified():
            messages.error(request, "This appointment can no longer be cancelled.")
            return self._redirect_home()
        return super().dispatch(request, *args, **kwargs)

    def _redirect_home(self):
        if self.request.user.role == User.Role.DOCTOR:
            return redirect("agenda:doctor_appointments")
        return redirect("agenda:my_appointments")

    def form_valid(self, form):
        appt = self.get_object()
        appt.status = Appointment.Status.CANCELLED
        appt.cancellation_reason = form.cleaned_data["reason"]
        appt.save()

        AppointmentHistory.objects.create(
            appointment=appt,
            action="cancelled",
            old_start_time=appt.start_time,
            changed_by=self.request.user,
            note=form.cleaned_data["reason"],
        )
        messages.success(self.request, "Appointment cancelled.")
        return self._redirect_home()


class MarkCompleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Doctor-only: mark a past/current appointment as completed."""
    def get_object(self):
        return get_object_or_404(Appointment, pk=self.kwargs["pk"])

    def test_func(self):
        return self.get_object().doctor.user_id == self.request.user.id

    def post(self, request, pk):
        appt = self.get_object()
        appt.status = Appointment.Status.COMPLETED
        appt.save()
        AppointmentHistory.objects.create(
            appointment=appt, action="completed", changed_by=request.user
        )
        messages.success(request, "Appointment marked as completed.")
        return redirect("agenda:doctor_appointments")