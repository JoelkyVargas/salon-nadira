# salon/citas/views.py
from datetime import time as dtime, datetime, timedelta
from django.http import JsonResponse
from django.shortcuts import render

from .forms import AppointmentForm
from .models import Appointment, BlockedSlot

# -------------------------------
# Configuración de horario
# -------------------------------
BUSINESS_HOURS = range(8, 21)  # 08:00..20:00

# -------------------------------
# Utils internas
# -------------------------------
def _all_times():
    return [dtime(hour=h).strftime("%H:%M") for h in BUSINESS_HOURS]

def _time_in_range(t, start, end):
    return (start is not None and end is not None and start <= t < end)

def _strike(text: str) -> str:
    # Convierte "12:00" en "1̶2̶:̶0̶0̶"
    return "".join(ch + "\u0336" for ch in text)

def _times_and_unavailable(date_str):
    """
    Devuelve (todas_las_horas, set_no_disponibles) para una fecha YYYY-MM-DD
    considerando citas (con su duración) y bloqueos (día completo, rango, puntual).
    """
    all_slots = _all_times()
    if not date_str:
        return all_slots, set()

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
        return all_slots, set(all_slots)  # día completo -> todo no disponible

    blocked_exact = {b.time.strftime("%H:%M") for b in blocked_qs if b.time}
    blocked_ranges = [(b.start_time, b.end_time) for b in blocked_qs if b.start_time and b.end_time]

    unavailable = set()
    for s in all_slots:
        hh, mm = map(int, s.split(":"))
        t_obj = dtime(hh, mm)
        if s in blocked_exact:
            unavailable.add(s); continue
        if any(_time_in_range(t_obj, st, et) for (st, et) in blocked_ranges):
            unavailable.add(s); continue
        if any(_time_in_range(t_obj, st, et) for (st, et) in busy_ranges):
            unavailable.add(s); continue

    return all_slots, unavailable

# -------------------------------
# Formulario público
# -------------------------------
def reservar_cita(request):
    success = None
    selected_date = request.POST.get("date") if request.method == "POST" else None
    all_times, unavailable = _times_and_unavailable(selected_date) if selected_date else (_all_times(), set())

    # Opciones para el <select> (texto tachado y disabled)
    time_options = [
        {"value": t, "label": (_strike(t) if t in unavailable else t), "disabled": (t in unavailable)}
        for t in all_times
    ]

    form = AppointmentForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        success = "¡Cita reservada con éxito!"
        form = AppointmentForm()

    return render(request, "citas/appointment_form.html", {
        "form": form,
        "success": success,
        "selected_date": selected_date,
        "time_options": time_options,
    })

# -------------------------------
# Calendario público (FullCalendar)
# -------------------------------
def calendar_view(request):
    return render(request, "citas/calendar.html")

# -------------------------------
# API: eventos para FullCalendar
# -------------------------------
def appointments_json(request):
    events = []

    # Citas
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

    # Bloqueos como fondo
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

# -------------------------------
# API: horas libres (compatibilidad)
# -------------------------------
def available_times_json(request):
    date_str = request.GET.get("date")
    all_times, unavailable = _times_and_unavailable(date_str) if date_str else (_all_times(), set())
    free = [t for t in all_times if t not in unavailable]
    return JsonResponse({"times": free})

# -------------------------------
# Listado simple
# -------------------------------
def appointments_list(request):
    qs = Appointment.objects.select_related("service").order_by("date", "time")
    return render(request, "citas/appointments_list.html", {"appointments": qs})
