# citas/whatsapp.py
import os, re
from datetime import datetime
from django.utils.timezone import get_current_timezone

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
WA_FROM = os.getenv("TWILIO_WHATSAPP_FROM")
OWNER_WA = os.getenv("OWNER_WHATSAPP")
SALON_NAME = os.getenv("SALON_NAME", "Nadira Fashion Salon")
_tz = get_current_timezone()

def _safe_client():
    """Crea el cliente Twilio solo si hay credenciales y librería instalada."""
    if not (ACCOUNT_SID and AUTH_TOKEN and WA_FROM):
        return None
    try:
        from twilio.rest import Client  # import perezoso
        return Client(ACCOUNT_SID, AUTH_TOKEN)
    except Exception:
        return None

def _to_wa(number: str, default_cc="+506"):
    if not number:
        return None
    digits = re.sub(r"\D", "", number)
    if not digits:
        return None
    if digits.startswith("00"):
        digits = digits[2:]
    if not digits.startswith("+"):
        if len(digits) == 8:
            digits = f"{default_cc}{digits}"
        else:
            digits = f"+{digits}"
    return f"whatsapp:{digits}"

def _send(to_wa: str, body: str):
    client = _safe_client()
    if not (client and to_wa):
        return False
    try:
        client.messages.create(from_=WA_FROM, to=to_wa, body=body)
        return True
    except Exception:
        return False

def _fmt_date(d): return d.strftime("%d/%m/%Y")
def _fmt_time(t): return t.strftime("%H:%M")

def send_booking_notifications(appointment):
    svc = getattr(appointment, "service", None)
    service_name = getattr(svc, "name", "Servicio")
    dstr = _fmt_date(appointment.date)
    tstr = _fmt_time(appointment.time)

    to_client = _to_wa(getattr(appointment, "customer_phone", ""))
    if to_client:
        _send(to_client,
              f"¡Hola {appointment.customer_name}! Tu cita en {SALON_NAME} fue confirmada.\n"
              f"• {service_name}\n• {dstr} a las {tstr}\n\n"
              f"Si necesitás cambiarla, respondé a este WhatsApp.")

    if OWNER_WA:
        _send(OWNER_WA,
              f"📥 Nueva reserva en {SALON_NAME}\n"
              f"{appointment.customer_name} ({appointment.customer_phone})\n"
              f"{service_name} – {dstr} {tstr}")

def send_reminder_now(appointment):
    svc = getattr(appointment, "service", None)
    service_name = getattr(svc, "name", "Servicio")
    dstr = _fmt_date(appointment.date)
    tstr = _fmt_time(appointment.time)

    to_client = _to_wa(getattr(appointment, "customer_phone", ""))
    if to_client:
        _send(to_client,
              f"⏰ Recordatorio de cita para mañana en {SALON_NAME}\n"
              f"• {service_name}\n• {dstr} a las {tstr}\n\n"
              f"Si necesitás reprogramar, respondé a este WhatsApp.")

    if OWNER_WA:
        _send(OWNER_WA,
              f"📅 Recordatorio: Mañana {dstr} {tstr}\n"
              f"{appointment.customer_name} ({appointment.customer_phone}) – {service_name}")
