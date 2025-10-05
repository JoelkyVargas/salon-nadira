# salon/citas/admin.py
from django.contrib import admin
from django import forms
from django.urls import path, reverse
from django.shortcuts import render, redirect
from datetime import datetime as dt
from .models import Service, Appointment, BlockedSlot

# ====== Branding del Admin ======
admin.site.site_header = "Nadira Fashion Salon"
admin.site.site_title = "Nadira Fashion Salon"
admin.site.index_title = "Panel de gestión"

# ====== Helpers horas ======
def _hour_choices():
    hours = range(8, 21)  # 08..20
    choices = [("", "— (sin hora) —")]
    choices += [(f"{h:02}:00", f"{h:02}:00") for h in hours]
    return choices

def _to_time(val):
    if not val:
        return None
    return dt.strptime(val, "%H:%M").time()

# ====== SERVICES ======
@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "duration_minutes", "color", "active")
    list_editable = ("duration_minutes", "color", "active")
    search_fields = ("name",)
    list_filter = ("active",)
    ordering = ("name",)
    class Media:
        css = {"all": ("admin/custom.css",)}  # tema rosado

# ====== APPOINTMENTS + TOGGLE CALENDARIO ======
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "service", "date", "time", "customer_phone")
    list_filter = ("service", "date")
    search_fields = ("customer_name", "customer_phone")
    ordering = ("-date", "time")
    autocomplete_fields = ("service",)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "calendar/",
                self.admin_site.admin_view(self.calendar_view),
                name="citas_appointment_calendar",
            ),
        ]
        return custom + urls

    def calendar_view(self, request):
        # Vista de calendario dentro del admin, con botón "Ver lista"
        ctx = {
            **self.admin_site.each_context(request),
            "title": "Calendario de Citas",
            "changelist_url": reverse("admin:citas_appointment_changelist"),
        }
        return render(request, "admin/citas/appointment_calendar.html", ctx)

    class Media:
        css = {"all": ("admin/custom.css",)}

admin.site.register(Appointment, AppointmentAdmin)

# ====== BLOCKED SLOTS (Auto bloqueos) con dropdowns ======
class BlockedSlotAdminForm(forms.ModelForm):
    start_time = forms.ChoiceField(choices=_hour_choices(), required=False, label="Inicio")
    end_time   = forms.ChoiceField(choices=_hour_choices(), required=False, label="Fin")
    time       = forms.ChoiceField(choices=_hour_choices(), required=False, label="Hora puntual (1h)")

    class Meta:
        model = BlockedSlot
        fields = ["date", "reason", "start_time", "end_time", "time"]

    def clean(self):
        cleaned = super().clean()
        s = cleaned.get("start_time")
        e = cleaned.get("end_time")
        t = cleaned.get("time")

        s_time = _to_time(s)
        e_time = _to_time(e)
        t_time = _to_time(t)

        if (s and not e) or (e and not s):
            raise forms.ValidationError("Para bloquear un rango, seleccioná hora de inicio y fin.")
        if s_time and e_time and s_time >= e_time:
            raise forms.ValidationError("La hora de fin debe ser mayor que la hora de inicio.")

        cleaned["start_time"] = s_time
        cleaned["end_time"] = e_time
        cleaned["time"] = t_time if not (s_time and e_time) else None  # rango manda
        return cleaned

@admin.register(BlockedSlot)
class BlockedSlotAdmin(admin.ModelAdmin):
    form = BlockedSlotAdminForm
    list_display = ("date", "start_time", "end_time", "time", "reason")
    list_filter = ("date",)
    search_fields = ("reason",)
    ordering = ("-date", "start_time", "time")
    fieldsets = (
        (None, {"fields": ("date", "reason")}),
        ("Rango (opcional)", {"fields": ("start_time", "end_time")}),
        ("Hora puntual (1h, opcional)", {"fields": ("time",)}),
    )
    class Media:
        css = {"all": ("admin/custom.css",)}
