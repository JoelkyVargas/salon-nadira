# salon/citas/views.py
from datetime import time as dtime, datetime, timedelta

from django.http import JsonResponse
from django.shortcuts import render

from .forms import AppointmentForm
from .models import Appointment, BlockedSlot

# ---------------------------------------
# 🕘 Configuración de horario laboral
# ---------------------------------------
BUSINESS_HOURS = range(8, 21)  # 08:00..20:00 (21 es exclusivo)


# ---------------------------------------
# 🔧 Utilidades internas
# ---------------------------------------
def _all_times():
    """Devuelve ['09:00','10:00',...,'17:00'] en horas exactas."""
    return [dtime(hour=h).strftime("%H:%M") for h in BUSINESS_HOURS]


def _time_in_range(t, start, end):
    """True si t está en [start, end) (fin abierto)."""
    return (start is not None and end is not None and start <= t < end)


def _available_times_for_date(date_str):
    """
    Calcula los horarios libres (strings 'HH:MM') para una fecha YYYY-MM-DD,
    respetando:
      - Citas existentes (exactas por hora)
      - Bloqueos por día completo, por rango (start_time/end_time) y puntuales (time)
    """
    all_slots = _all_times()
    if not date_str:
        return []

    # Citas existentes
    booked_times = Appointment.objects.filter(date=date_str).values_list("time", flat=True)
    booked_as_str = {bt.strftime("%H:%M") for bt in booked_times}

    # Bloqueos
    blocked_qs = BlockedSlot.objects.filter(date=date_str)
    block_entire_day = False
    blocked_exact = set()   # {'09:00', ...}
    blocked_ranges = []     # [(start_time, end_time), ...]

    for b in blocked_qs:
        if b.start_time and b.end_time:
            blocked_ranges.append((b.start_time, b.end_time))
        elif b.time:
            blocked_exact.add(b.time.strftime("%H:%M"))
        else:
            # sin horas => bloqueo de día completo
            block_entire_day = True

    if block_entire_day:
        return []

    free = []
    for s in all_slots:
        # descartamos las ocupadas por cita o bloqueo puntual
        if s in booked_as_str or s in blocked_exact:
            continue
        # descartamos las que caen dentro de un rango bloqueado
        hh, mm = map(int, s.split(":"))
        t_obj = dtime(hh, mm)
        if any(_time_in_range(t_obj, st, et) for (st, et) in blocked_ranges):
            continue
        free.append(s)

    return free


# ---------------------------------------
# 💼 Formulario de reservas (público)
# ---------------------------------------
def reservar_cita(request):
    """
    Renderiza el formulario y guarda si es válido.
    - Rellena el <select> de 'time' con solo horas disponibles (según la fecha elegida).
    - Si el POST se guarda OK, muestra mensaje de éxito y limpia el formulario.
    """
    success = None

    selected_date = request.POST.get("date") if request.method == "POST" else None
    available_times = _available_times_for_date(selected_date) if selected_date else None

    form = AppointmentForm(request.POST or None, available_times=available_times)

    if request.method == "POST" and form.is_valid():
        form.save()
        success = "¡Cita reservada con éxito!"
        # Reset del form: sin fecha -> el select de horas queda en placeholder
        form = AppointmentForm(available_times=None)

    return render(
        request,
        "citas/appointment_form.html",
        {
            "form": form,
            "success": success,
        },
    )


# ---------------------------------------
# 🗓️ Vista HTML del calendario (público)
# ---------------------------------------
def calendar_view(request):
    return render(request, "citas/calendar.html")


# ---------------------------------------
# 🔌 API: eventos para FullCalendar
#    - Citas como eventos (usa duración/color del servicio si existen)
#    - Bloqueos (día completo, puntual y rango) como "background"
# ---------------------------------------
def appointments_json(request):
    events = []

    # Citas
    for ap in Appointment.objects.select_related("service").all():
        # Si el modelo Service tiene duration_minutes/color, se toman; si no, defaults.
        duration_min = getattr(ap.service, "duration_minutes", 60) if getattr(ap, "service", None) else 60
        color = getattr(ap.service, "color", "#0d6efd") if getattr(ap, "service", None) else "#0d6efd"

        start_dt = datetime.combine(ap.date, ap.time)
        end_dt = start_dt + timedelta(minutes=duration_min)

        events.append(
            {
                "title": f"{ap.customer_name} - {ap.service.name if getattr(ap, 'service', None) else ''}",
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "color": color,
            }
        )

    # Bloqueos como fondo
    for b in BlockedSlot.objects.all():
        if b.start_time and b.end_time:
            # Rango
            start_dt = datetime.combine(b.date, b.start_time)
            end_dt = datetime.combine(b.date, b.end_time)
        elif b.time:
            # Puntual (1 hora)
            start_dt = datetime.combine(b.date, b.time)
            end_dt = start_dt + timedelta(minutes=60)
        else:
            # Día completo
            start_dt = datetime.combine(b.date, dtime(0, 0))
            end_dt = datetime.combine(b.date, dtime(23, 59))

        events.append(
            {
                "title": f"Bloqueo{f' - {b.reason}' if b.reason else ''}",
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "display": "background",
                "color": "#adb5bd",
            }
        )

    return JsonResponse(events, safe=False)


# ---------------------------------------
# 🔌 API: horas disponibles para una fecha
#    GET /api/available-times/?date=YYYY-MM-DD
#    -> {"times": ["09:00", "10:00", ...]}
# ---------------------------------------
def available_times_json(request):
    date_str = request.GET.get("date")
    times = _available_times_for_date(date_str) if date_str else []
    return JsonResponse({"times": times})


# ---------------------------------------
# 📋 Listado simple de citas (opcional)
# ---------------------------------------
def appointments_list(request):
    qs = Appointment.objects.select_related("service").order_by("date", "time")
    return render(request, "citas/appointments_list.html", {"appointments": qs})
