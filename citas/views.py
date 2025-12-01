# -*- coding: utf-8 -*-
"""
Created on Tue Oct 28 21:31:45 2025

@author: jvz16
"""

# salon/citas/views.py
from datetime import time as dtime, datetime, timedelta

from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.db import models  # 👈 NUEVO: para usar Q en filtros

from .forms import AppointmentForm
from .models import (
    ServiceCategory,
    Service,
    Appointment,
    BlockedSlot,
    Testimonial,
    BeforeAfter,
    HomeBackground,
    VipCode,
    Package,
)
from .whatsapp import send_booking_notifications  # WhatsApp notificaciones

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
      - Y, si viene service_duration, horas que no caben antes del cierre.
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


# ---------- Vistas independientes (reservas, calendario, JSON, servicios, testimonios) ----------

def reservar_cita(request):
    """
    Vista independiente solo para reservas (URL /reservar/).
    Renderiza el formulario y guarda si es válido.
    Tras guardar, envía WhatsApp a propietaria y cliente.
    """
    success = None

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
        try:
            send_booking_notifications(ap)
        except Exception as e:
            print("WHATSAPP send error:", e)
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


def servicios(request):
    """
    Página independiente /servicios/ con servicios agrupados por categoría (hasta 3)
    y “Otros” para los servicios sin categoría.
    (Esta vista no la estamos usando en la home unificada, pero se mantiene.)
    """
    categorias = list(ServiceCategory.objects.order_by("name")[:3])
    grupos = []

    for cat in categorias:
        qs = Service.objects.filter(active=True, category=cat).order_by("name")
        grupos.append((cat.name, qs))

    sin_cat = Service.objects.filter(active=True, category__isnull=True).order_by("name")
    if sin_cat.exists():
        grupos.append(("Otros", sin_cat))

    return render(request, "citas/servicios.html", {"grupos": grupos})


def testimonios(request):
    items = (
        Testimonial.objects.filter(active=True)
        .prefetch_related("photos")
        .order_by("-created_at")
    )
    return render(request, "citas/testimonios.html", {"items": items})


# ---------- HOME unificada (Reservar + Servicios + Testimonios + Paquetes + VIP) ----------

def home(request):
    """
    Página principal con:
      - Bloque de 5 “botones” (Reservas, Servicios, Testimonios, Paquetes, Clientes VIP)
      - Secciones ocultas que se muestran al hacer clic
      - Formulario de reservas (con WhatsApp)
      - Paquetes públicos y Paquetes VIP
      - Código VIP que muestra directamente la sección VIP al enviar.
    """
    # Qué sección debe quedar visible tras un POST
    initial_section = None

    # --- Variables comunes ---
    success = None
    available_times = None

    # Para VIP
    vip_owner_name = None
    vip_packages = None
    vip_error = None

    # --- Lógica POST (puede ser reserva o VIP) ---
    if request.method == "POST":
        # Detectamos formulario VIP por presencia de vip_code
        if "vip_code" in request.POST:
            code_str = request.POST.get("vip_code", "").strip()
            if code_str:
                vip = VipCode.objects.filter(code=code_str, active=True).first()
                if vip:
                    vip_owner_name = vip.name  # usamos este nombre en el template
                    vip_packages = Package.objects.filter(active=True, vip_only=True).order_by("title")

                    for pkg in vip_packages:
                        if pkg.price is not None:
                            try:
                                value = int(pkg.price)
                                pkg.formatted_price = f"{value:,}".replace(",", ".")
                            except (TypeError, ValueError):
                                pkg.formatted_price = ""

                else:
                    vip_error = "Código VIP inválido o inactivo."
            else:
                vip_error = "Por favor ingresá tu código VIP."

            # Después de enviar código VIP, mostramos la sección VIP
            initial_section = "vip"
            # El formulario de reserva se muestra vacío
            form = AppointmentForm()

        else:
            # --------- Formulario de RESERVA ----------
            selected_date = request.POST.get("date")
            selected_service_id = request.POST.get("service")
            service_duration = None

            if selected_service_id:
                svc = Service.objects.filter(
                    id=selected_service_id
                ).only("duration_minutes").first()
                if svc:
                    service_duration = getattr(svc, "duration_minutes", 60)

            available_times = _available_times_for_date(
                selected_date,
                service_duration
            ) if selected_date else None

            form = AppointmentForm(
                request.POST or None,
                available_times=available_times
            )

            if form.is_valid():
                ap = form.save()
                success = "¡Cita reservada con éxito!"
                try:
                    send_booking_notifications(ap)
                except Exception as e:
                    print("WHATSAPP send error:", e)

                # Limpiamos el formulario tras guardar
                form = AppointmentForm()
            # Tras reservar, dejamos visible la sección de reservas
            initial_section = "reservar"

    else:
        # GET: formulario de reserva vacío,
        # el dropdown de horas se llenará vía JS /api/available-times/
        form = AppointmentForm()

    # --- Paquetes públicos ---
    public_packages = Package.objects.filter(active=True, vip_only=False).order_by("title")

    # Formateo de precios con miles separados por punto
    for pkg in public_packages:
        if pkg.price is not None:
            try:
                value = int(pkg.price)
                pkg.formatted_price = f"{value:,}".replace(",", ".")
            except (TypeError, ValueError):
                pkg.formatted_price = ""

    # --- Servicios para la vista unificada, AGRUPADOS POR CATEGORÍA ---
    service_groups = []

    # 1) Categorías distintas de "Otros" (en orden alfabético)
    categorias = ServiceCategory.objects.order_by("name")
    for cat in categorias:
        if cat.name.strip().lower() == "otros":
            continue
        qs = Service.objects.filter(active=True, category=cat).order_by("name")
        if qs.exists():
            service_groups.append({
                "label": cat.name,
                "services": qs,
            })

    # 2) Grupo "Otros" al final:
    #    servicios cuya categoría se llama "Otros" + servicios sin categoría.
    otros_qs = Service.objects.filter(
        active=True
    ).filter(
        models.Q(category__name__iexact="Otros") | models.Q(category__isnull=True)
    ).order_by("name")

    if otros_qs.exists():
        service_groups.append({
            "label": "Otros",
            "services": otros_qs,
        })

    # --- Testimonios para la vista unificada ---
    testimonios = (
        Testimonial.objects.filter(active=True)
        .prefetch_related("photos")
        .order_by("-created_at")[:12]
    )

    # --- Fondo configurable desde el admin ---
    background = HomeBackground.objects.filter(active=True).first()

    # Año actual para el footer (si lo querés usar)
    now = timezone.now()

    return render(request, "citas/home.html", {
        "form": form,
        "success": success,
        "available_times": available_times,
        "service_groups": service_groups,  # 👈 agrupados y con Otros al final
        "testimonios": testimonios,
        "background": background,
        "public_packages": public_packages,
        "vip_owner_name": vip_owner_name,
        "vip_packages": vip_packages,
        "vip_error": vip_error,
        "initial_section": initial_section,
        "now": now,
    })
