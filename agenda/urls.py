from django.urls import path
from . import views

app_name = "agenda"

urlpatterns = [
    path("", views.DashboardRedirectView.as_view(), name="dashboard"),
    path("signup/", views.SignUpView.as_view(), name="signup"),
    path("mine/", views.MyAppointmentsView.as_view(), name="my_appointments"),
    path("doctor/", views.DoctorAppointmentsView.as_view(), name="doctor_appointments"),
    path("doctors/", views.DoctorListView.as_view(), name="doctor_list"),
    path("doctors/<int:pk>/book/", views.BookAppointmentView.as_view(), name="book_appointment"),
    path("<int:pk>/reschedule/", views.RescheduleAppointmentView.as_view(), name="reschedule"),
    path("<int:pk>/cancel/", views.CancelAppointmentView.as_view(), name="cancel"),
    path("<int:pk>/complete/", views.MarkCompleteView.as_view(), name="mark_complete"),
]