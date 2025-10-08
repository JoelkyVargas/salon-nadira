# salon/citas/forms.py
from datetime import datetime, timedelta, time as dtime
from django import forms
from django.utils import timezone
from .models import Appointment, BlockedSlot, Service

# Horario laboral
OPEN_HOUR = 8     # 08:00
CLOSE_HOUR = 20   # 20:00
BUSINESS_HOURS = range(OPEN_HOUR, CLOSE_HOUR + 1)  # 08..20

class AppointmentForm(forms.ModelForm):
    """
    Muestra todas las horas en el <select> (se tachan/deshabilitan en el template).
    Valida:
    - Bloqueos (día completo / rango / puntual)
    - Choque con otra cita (usando duración del servicio)
    - Horario laboral (horas enteras)
    - Que el servicio termine antes del cierre
    """
    service = forms.ModelChoiceField(
        queryset=Service.objects.filter(active=True).order_by("name"),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    time = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'time-select'})
    )

    class Meta:
        model = Appointment
        fields = ['customer_name', 'customer_phone', 'service', 'date', 'time']
        widgets = {
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu nombre'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu teléfono'}),
            'date': forms.DateInput(attrs={
                'type': 'date', 'class': 'form-control', 'id': 'date-input',
                'min': timezone.now().date().isoformat()
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Todas las horas (08..20) como opciones del select
        all_hours = [f"{h:02}:00" for h in BUSINESS_HOURS]
        self.fields['time'].choices = [(t, t) for t in all_hours]

    def clean(self):
        cleaned = super().clean()
        date = cleaned.get('date')
        time_str = cleaned.get('time')  # 'HH:MM'
        service = cleaned.get('service')

        if not date or not time_str or not service:
            return cleaned

        # String -> time
        try:
            hh, mm = map(int, time_str.split(':'))
            start_time = dtime(hh, mm)
        except Exception:
            raise forms.ValidationError("Hora inválida.")

        # 1) Día bloqueado (sin horas)
        if BlockedSlot.objects.filter(date=date, start_time__isnull=True, end_time__isnull=True, time__isnull=True).exists():
            raise forms.ValidationError("Ese día está bloqueado. Elegí otra fecha.")

        # 2) Bloqueo puntual
        if BlockedSlot.objects.filter(date=date, time=start_time).exists():
            raise forms.ValidationError("Ese horario está bloqueado. Elegí otra hora.")

        # 3) Bloqueo por rango
        for b in BlockedSlot.objects.filter(date=date, start_time__isnull=False, end_time__isnull=False):
            if b.start_time <= start_time < b.end_time:
                raise forms.ValidationError("Ese horario cae dentro de un rango bloqueado. Elegí otra hora.")

        # 4) Dentro de horario laboral exacto (en punto)
        if start_time.hour not in BUSINESS_HOURS or start_time.minute != 0:
            raise forms.ValidationError(f"El horario debe ser en horas en punto entre {OPEN_HOUR:02}:00 y {CLOSE_HOUR:02}:00.")

        # 5) Debe terminar antes del cierre
        duration_min = getattr(service, 'duration_minutes', 60)
        start_dt = datetime.combine(date, start_time)
        end_dt = start_dt + timedelta(minutes=duration_min)
        close_dt = datetime.combine(date, dtime(CLOSE_HOUR, 0))
        if end_dt > close_dt:
            raise forms.ValidationError(
                f"No es posible reservar {service.name} a las {start_time.strftime('%H:%M')} "
                f"porque no termina antes del cierre ({CLOSE_HOUR:02}:00). "
                f"Contacta al 8574-2863 para coordinar."
            )

        # 6) No traslapar con citas existentes (usando su duración)
        for ap in Appointment.objects.select_related("service").filter(date=date):
            ap_dur = getattr(ap.service, 'duration_minutes', 60) if getattr(ap, "service", None) else 60
            ap_start = datetime.combine(date, ap.time)
            ap_end = ap_start + timedelta(minutes=ap_dur)
            # traslape si [start_dt, end_dt) ∩ [ap_start, ap_end) ≠ ∅
            if start_dt < ap_end and ap_start < end_dt:
                raise forms.ValidationError("Ese horario se solapa con otra cita existente. Elegí otra hora.")

        # Guardar time como objeto time
        cleaned['time'] = start_time
        return cleaned
