from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, DoctorProfile, Appointment, AppointmentHistory


class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (None, {"fields": ("role", "phone")}),
    )


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "start_time", "status")
    list_filter = ("status", "doctor")
    search_fields = ("patient__username", "doctor__user__username")


admin.site.register(User, CustomUserAdmin)
admin.site.register(DoctorProfile)
admin.site.register(AppointmentHistory)