# -*- coding: utf-8 -*-
"""
Created on Wed Oct  8 17:29:55 2025

@author: jvz16
"""

# salon/citas/whatsapp.py
import os
import re
from datetime import datetime, timedelta
from twilio.rest import Client
from django.utils.timezone import get_current_timezone

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
WA_FROM = os.getenv("TWILIO_WHATSAPP_FROM")        # ej. "whatsapp:+14155238886"
OWNER_WA = os.getenv("OWNER_WHATSAPP")             # ej. "whatsapp:+50685742863"
SALON_NAME = os.getenv("SALON_NAME", "Nadira Fashion Salon")

_client = Client(ACCOUNT_SID, AUTH_TOKEN) if ACCOUNT_SID and AUTH_TOKEN else None
_tz = get_current_timezone()

def _to_wa(number: str, default_cc="+506"):
    """Normaliza a formato 'whatsapp:+#########'. Si falla, devuelve None."""
    if not number:
        return None
    digits = re.sub(r"\D", "", number)
    if not digits:
        return None
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("+"):
        pass
    if digits.startswith("506") and len(digits) == 11:
        wa = f"whatsapp:+{digits}"
    elif len(digits) == 8:  # CR sin prefijo
        wa = f"whatsapp:{default_cc}{digits}"
    elif digits.startswith("506") and len(digits) == 11:
        wa = f"whatsapp:+{digits}"
    elif digits.startswith("1") and len(digits) >= 10:
        wa = f"whatsapp:+{digits}"
    else:
        wa = f"whatsapp:+{digits}"
    return wa

def _send(to_wa: str, body: str):
    """Envía mensaje WhatsApp; silencioso si no hay credenciales."""
    if not _client or not WA_FROM or not to_wa:
        return False
    try:
        _client.messages.create(from_=WA_FROM, to=to_wa, body=body)
        return True
    except Exception as e:
        # En producción puedes loggear con logging.getLogger(__name__).exception(e)
        print("TWILIO ERROR:", e)
        return False

def _fmt_date(date_obj):
    return date_obj.strftime("%d/%m/%Y")

def _fmt_time(time_obj):
    return time_obj.strftime("%H:%M")

def send_booking_notifications(appointment):
    """
    Enviar confirmación inmediata a propietaria y cliente al crear la cita.
    """
    svc = getattr(appointment, "service", None)
    service_name = getattr(svc, "name", "Servicio")
    dstr = _fmt_date(appointment.date)
    tstr = _fmt_time(appointment.time)

    # Cliente
    to_client = _to_wa(getattr(appointment, "customer_phone", ""))
    if to_client:
        body_client = (
            f"¡Hola {appointment.customer_name}! Tu cita en {SALON_NAME} fue confirmada.\n"
            f"• Servicio: {service_name}\n"
            f"• Fecha: {dstr} a las {tstr}\n\n"
            f"Si necesitás cambiarla, respondé a este WhatsApp."
        )
        _send(to_client, body_client)

    # Propietaria
    if OWNER_WA:
        body_owner = (
            f"📥 Nueva reserva en {SALON_NAME}\n"
            f"Cliente: {appointment.customer_name} ({appointment.customer_phone})\n"
            f"Servicio: {service_name}\n"
            f"Fecha: {dstr} {tstr}"
        )
        _send(OWNER_WA, body_owner)

def send_reminder_now(appointment):
    """
    Enviar recordatorio en el momento de llamarse (usado por comando diario).
    """
    svc = getattr(appointment, "service", None)
    service_name = getattr(svc, "name", "Servicio")
    dstr = _fmt_date(appointment.date)
    tstr = _fmt_time(appointment.time)

    # Cliente
    to_client = _to_wa(getattr(appointment, "customer_phone", ""))
    if to_client:
        body_client = (
            f"⏰ Recordatorio de cita para mañana en {SALON_NAME}\n"
            f"• {service_name}\n"
            f"• {dstr} a las {tstr}\n\n"
            f"Si necesitás reprogramar, respondé a este WhatsApp."
        )
        _send(to_client, body_client)

    # Propietaria
    if OWNER_WA:
        body_owner = (
            f"📅 Recordatorio: Mañana {dstr} {tstr}\n"
            f"{appointment.customer_name} ({appointment.customer_phone}) – {service_name}"
        )
        _send(OWNER_WA, body_owner)
