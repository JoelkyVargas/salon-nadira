from datetime import time as dtime, datetime, timedelta

from django.http import JsonResponse
from django.shortcuts import render
from .models import Testimonial
from .forms import AppointmentForm
from .models import Appointment, BlockedSlot, Service
from .whatsapp import send_booking_notifications  # ← NUEVO

# 🕘 Configuración de horario laboral
OPEN_HOUR = 8
CLOSE_HOUR = 20
BUSINESS_HOURS = range(OPEN_HOUR, CLOSE_HOUR + 1)  # 08..20

# ---------- Utilidades ----------
def _all_times():
    """['08:00','09:00',...,'20:00'] (horas en punto)."""
    return [dtime(hour=h).strftime("%H:%M") for h in BUSINESS_HOURS]

def _time_in_range(t, start, end):
    """True si t está en [start, end) (fin abierto)."""
    return (start is not None and end is not None and start <= t < end)

def _available_times_for_date(date_str, service_duration=None):
    """
    Devuelve SOLO horas libres (strings 'HH:MM') para una fecha YYYY-MM-DD,
    excluyendo:
      - Citas existentes (considerando su duración)
      - Bloqueos por día completo, rango y puntuales
      - Y, si viene service_duration, horas que no caben antes del cierre
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
    # Día completo
    if any(not b.start_time and not b.end_time and not b.time for b in blocked_qs):
        return []

    blocked_exact = {b.time.strftime("%H:%M") for b in blocked_qs if b.time}
    blocked_ranges = [(b.start_time, b.end_time) for b in blocked_qs if b.start_time and b.end_time]

    free = []
    close_t = dtime(CLOSE_HOUR, 0)
    date_obj = datetime.fromisoformat(date_str).date()

    for s in all_slots:
        if s in blocked_exact:
            continue

        hh, mm = map(int, s.split(":"))
        t_obj = dtime(hh, mm)

        # Dentro de bloqueos por rango
        if any(_time_in_range(t_obj, st, et) for (st, et) in blocked_ranges):
            continue

        # Dentro de rangos ocupados por citas existentes (duración real)
        if any(_time_in_range(t_obj, st, et) for (st, et) in busy_ranges):
            continue

        # Debe caber antes del cierre si sabemos la duración del servicio elegido
        if service_duration:
            start_dt = datetime.combine(date_obj, t_obj)
            end_dt = start_dt + timedelta(minutes=service_duration)
            if end_dt > datetime.combine(date_obj, close_t):
                continue

        free.append(s)

    return free

# ---------- Vistas ----------
def reservar_cita(request):
    """
    Renderiza el formulario y guarda si es válido.
    - El <select> de 'time' se llena por JS consultando /api/available-times/
      (y en POST conservamos compatibilidad server-side).
    - Tras guardar, enviamos WhatsApp a propietaria y cliente.
    """
    success = None

    # Compatibilidad server-side para re-render con selección previa:
    selected_date = request.POST.get("date") if request.method == "POST" else None
    selected_service_id = request.POST.get("service") if request.method == "POST" else None
    service_duration = None
    if selected_service_id:
        svc = Service.objects.filter(id=selected_service_id).only("duration_minutes").first()
        if svc:
            service_duration = getattr(svc, "duration_minutes", 60)

    available_times = _available_times_for_date(selected_date, service_duration) if selected_date else None
    form = AppointmentForm(request.POST or None, available_times=available_times)

    if request.method == "POST" and form.is_valid():
        ap = form.save()
        success = "¡Cita reservada con éxito!"
        # === ENVÍO WHATSAPP INMEDIATO ===
        try:
            send_booking_notifications(ap)
        except Exception as e:
            print("WHATSAPP send error:", e)
        # Reset del form
        form = AppointmentForm(available_times=None)

    return render(
        request,
        "citas/appointment_form.html",
        {
            "form": form,
            "success": success,
        },
    )

def calendar_view(request):
    return render(request, "citas/calendar.html")

def appointments_json(request):
    events = []
    # Citas
    for ap in Appointment.objects.select_related("service").all():
        duration_min = getattr(ap.service, "duration_minutes", 60) if getattr(ap, "service", None) else 60
        color = getattr(ap.service, "color", "#0d6efd") if getattr(ap, "service", None) else "#0d6efd"
        start_dt = datetime.combine(ap.date, ap.time)
        end_dt = start_dt + timedelta(minutes=duration_min)
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

def available_times_json(request):
    """
    GET /api/available-times/?date=YYYY-MM-DD&service=<id>
    -> {"times": ["09:00", "10:00", ...]}
    Considera duración del servicio seleccionado para no ofrecer horas que no caben antes del cierre.
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

def appointments_list(request):
    qs = Appointment.objects.select_related("service").order_by("date", "time")
    return render(request, "citas/appointments_list.html", {"appointments": qs})





def testimonios(request):
    items = Testimonial.objects.filter(active=True).prefetch_related("photos").order_by("-created_at")
    return render(request, "citas/testimonios.html", {"items": items})