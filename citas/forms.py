# salon/citas/forms.py
from datetime import datetime, timedelta, time as dtime
from django import forms
from django.utils import timezone
from .models import Appointment, BlockedSlot, Service

OPEN_HOUR = 8
CLOSE_HOUR = 20
BUSINESS_HOURS = range(OPEN_HOUR, CLOSE_HOUR + 1)

class AppointmentForm(forms.ModelForm):
    """
    El <select> de horas se llena dinámicamente por JS con SOLO horas disponibles.
    El backend valida bloqueos, solapes y fin antes del cierre.
    """
    service = forms.ModelChoiceField(
        queryset=Service.objects.filter(active=True).order_by("name"),
        widget=forms.Select(attrs={'class': 'form-select'})  # id: "id_service"
    )
    time = forms.ChoiceField(
        choices=[("", "— Selecciona una fecha —")],
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'time-select'})
    )

    class Meta:
        model = Appointment
        fields = ['customer_name', 'customer_phone', 'service', 'date', 'time']
        widgets = {
            'customer_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Tu nombre'
            }),
            'customer_phone': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Tu teléfono'
            }),
            'date': forms.DateInput(attrs={
                'type': 'date', 'class': 'form-control', 'id': 'date-input',
                'min': timezone.now().date().isoformat()
            }),
        }

    def clean(self):
        cleaned = super().clean()
        date = cleaned.get('date')
        time_str = cleaned.get('time')
        service = cleaned.get('service')
        if not date or not time_str or not service:
            return cleaned

        # String -> time
        try:
            hh, mm = map(int, time_str.split(':'))
            start_time = dtime(hh, mm)
        except Exception:
            raise forms.ValidationError("Hora inválida.")

        # Día completo bloqueado
        if BlockedSlot.objects.filter(
            date=date, start_time__isnull=True, end_time__isnull=True, time__isnull=True
        ).exists():
            raise forms.ValidationError("Ese día está bloqueado. Elegí otra fecha.")

        # Bloqueo puntual
        if BlockedSlot.objects.filter(date=date, time=start_time).exists():
            raise forms.ValidationError("Ese horario está bloqueado. Elegí otra hora.")

        # Bloqueo por rango
        for b in BlockedSlot.objects.filter(date=date, start_time__isnull=False, end_time__isnull=False):
            if b.start_time <= start_time < b.end_time:
                raise forms.ValidationError("Ese horario cae dentro de un rango bloqueado. Elegí otra hora.")

        # En punto y dentro del horario
        if start_time.hour not in BUSINESS_HOURS or start_time.minute != 0:
            raise forms.ValidationError(
                f"El horario debe ser en horas en punto entre {OPEN_HOUR:02}:00 y {CLOSE_HOUR:02}:00."
            )

        # Debe terminar antes del cierre
        duration_min = getattr(service, 'duration_minutes', 60)
        start_dt = datetime.combine(date, start_time)
        end_dt = start_dt + timedelta(minutes=duration_min)
        if end_dt > datetime.combine(date, dtime(CLOSE_HOUR, 0)):
            raise forms.ValidationError("El servicio no termina antes del cierre. Elegí otra hora.")

        # No solapar con otras citas (según duración)
        for ap in Appointment.objects.select_related("service").filter(date=date):
            ap_dur = getattr(ap.service, 'duration_minutes', 60) if getattr(ap, "service", None) else 60
            ap_start = datetime.combine(date, ap.time)
            ap_end = ap_start + timedelta(minutes=ap_dur)
            if start_dt < ap_end and ap_start < end_dt:
                raise forms.ValidationError("Ese horario se solapa con otra cita. Elegí otra hora.")

        cleaned['time'] = start_time
        return cleaned
