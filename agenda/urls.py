from django.urls import path
from . import views

app_name = "agenda"

urlpatterns = [
    path("", views.MyAppointmentsView.as_view(), name="my_appointments"),
    path("<int:pk>/reschedule/", views.RescheduleAppointmentView.as_view(), name="reschedule"),
    path("<int:pk>/cancel/", views.CancelAppointmentView.as_view(), name="cancel"),
]