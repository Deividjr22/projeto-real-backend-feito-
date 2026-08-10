from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, FormView

from .models import Appointment, AppointmentHistory
from .forms import RescheduleForm, CancelForm


class MyAppointmentsView(LoginRequiredMixin, ListView):
    model = Appointment
    template_name = "agenda/my_appointments.html"
    context_object_name = "appointments"

    def get_queryset(self):
        return Appointment.objects.filter(patient=self.request.user).select_related("doctor__user")


class AppointmentOwnerMixin(UserPassesTestMixin):
    def get_object(self):
        if not hasattr(self, "appointment"):
            self.appointment = get_object_or_404(Appointment, pk=self.kwargs["pk"])
        return self.appointment

    def test_func(self):
        return self.get_object().patient_id == self.request.user.id


class RescheduleAppointmentView(LoginRequiredMixin, AppointmentOwnerMixin, FormView):
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
        kwargs["doctor"] = self.get_object().doctor
        kwargs["exclude_appointment"] = self.get_object()
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


class CancelAppointmentView(LoginRequiredMixin, AppointmentOwnerMixin, FormView):
    template_name = "agenda/cancel.html"
    form_class = CancelForm

    def dispatch(self, request, *args, **kwargs):
        appt = self.get_object()
        if not appt.can_be_modified():
            messages.error(request, "This appointment can no longer be cancelled.")
            return redirect("agenda:my_appointments")
        return super().dispatch(request, *args, **kwargs)

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
        return redirect("agenda:my_appointments")