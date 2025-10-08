# salon/citas/views.py
from datetime import time as dtime, datetime, timedelta
from django.http import JsonResponse
from django.shortcuts import render
from .forms import AppointmentForm
from .models import Appointment, BlockedSlot, Service

OPEN_HOUR = 8
CLOSE_HOUR = 20
BUSINESS_HOURS = range(OPEN_HOUR, CLOSE_HOUR + 1)

def _all_times():
    return [dtime(hour=h).strftime("%H:%M") for h in BUSINESS_HOURS]

def _time_in_range(t, start, end):
    return (start is not None and end is not None and start <= t < end)

def _available_times_for_date(date_str, service_duration=None):
    """
    Devuelve SOLO horas libres (strings 'HH:MM'), excluyendo:
    - citas existentes (considerando su duración)
    - bloqueos (día completo, por rango y puntuales)
    - y, si viene service_duration, horas que NO alcanzan a terminar antes del cierre
    """
    all_slots = _all_times()
    if not date_str:
        return []

    # Citas -> rangos ocupados
    appts = Appointment.objects.select_related("service").filter(date=date_str)
    busy_ranges = []
    for ap in appts:
        dur = getattr(ap.service, "duration_minutes", 60) if getattr(ap, "service", None) else 60
        start_dt = datetime.combine(ap.date, ap.time)
        end_dt = start_dt + timedelta(minutes=dur)
        busy_ranges.append((start_dt.time(), end_dt.time()))

    # Bloqueos
    blocked_qs = BlockedSlot.objects.filter(date=date_str)
    if any(not b.start_time and not b.end_time and not b.time for b in blocked_qs):
        return []  # día completo

    blocked_exact = {b.time.strftime("%H:%M") for b in blocked_qs if b.time}
    blocked_ranges = [(b.start_time, b.end_time) for b in blocked_qs if b.start_time and b.end_time]

    free = []
    close_dt = None  # solo si service_duration
    for s in all_slots:
        if s in blocked_exact:
            continue
        hh, mm = map(int, s.split(":"))
        t_obj = dtime(hh, mm)
        if any(_time_in_range(t_obj, st, et) for (st, et) in blocked_ranges):
            continue
        if any(_time_in_range(t_obj, st, et) for (st, et) in busy_ranges):
            continue
        if service_duration:
            if close_dt is None:
                close_dt = dtime(CLOSE_HOUR, 0)
            start_dt = datetime.combine(datetime.fromisoformat(date_str).date(), t_obj)
            if start_dt + timedelta(minutes=service_duration) > datetime.combine(start_dt.date(), close_dt):
                continue
        free.append(s)
    return free

def reservar_cita(request):
    """Formulario público. El <select> se actualiza por JS; backend mantiene validaciones."""
    success = None
    form = AppointmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        success = "¡Cita reservada con éxito!"
        form = AppointmentForm()
    return render(request, "citas/appointment_form.html", {"form": form, "success": success})

def calendar_view(request):
    return render(request, "citas/calendar.html")

def appointments_json(request):
    events = []
    for ap in Appointment.objects.select_related("service").all():
        dur = getattr(ap.service, "duration_minutes", 60) if getattr(ap, "service", None) else 60
        color = getattr(ap.service, "color", "#0d6efd") if getattr(ap, "service", None) else "#0d6efd"
        start_dt = datetime.combine(ap.date, ap.time)
        end_dt = start_dt + timedelta(minutes=dur)
        events.append({
            "title": f"{ap.customer_name} - {ap.service.name if getattr(ap, 'service', None) else ''}",
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "color": color,
        })
    for b in BlockedSlot.objects.all():
        if b.start_time and b.end_time:
            start_dt = datetime.combine(b.date, b.start_time)
            end_dt = datetime.combine(b.date, b.end_time)
        elif b.time:
            start_dt = datetime.combine(b.date, b.time)
            end_dt = start_dt + timedelta(minutes=60)
        else:
            start_dt = datetime.combine(b.date, dtime(0, 0))
            end_dt = datetime.combine(b.date, dtime(23, 59))
        events.append({
            "title": f"Bloqueo{f' - {b.reason}' if getattr(b, 'reason', '') else ''}",
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "display": "background",
            "color": "#adb5bd",
        })
    return JsonResponse(events, safe=False)

def available_times_json(request):
    """
    GET /api/available-times/?date=YYYY-MM-DD&service=<id>
    -> {"times": ["09:00","10:00",...]}
    Considera duración del servicio si viene 'service'.
    """
    date_str = request.GET.get("date")
    service_id = request.GET.get("service")
    service_duration = None
    if service_id:
        svc = Service.objects.filter(id=service_id).only("duration_minutes").first()
        if svc:
            service_duration = getattr(svc, "duration_minutes", 60)
    times = _available_times_for_date(date_str, service_duration=service_duration) if date_str else []
    return JsonResponse({"times": times})
