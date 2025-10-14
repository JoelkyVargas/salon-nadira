# citas/whatsapp.py
import os, re, json
from twilio.rest import Client

# ====== ENV obligatorias ======
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")
MS_SID      = os.getenv("TWILIO_MESSAGING_SERVICE_SID")  # MGxxxxxxxxxxxx
CONF_SID    = os.getenv("TWILIO_CONFIRMATION_CONTENT_SID")  # Hxxxxxxxxxxxx
REM_SID     = os.getenv("TWILIO_REMINDER_CONTENT_SID")      # Hxxxxxxxxxxxx
OWNER_WA    = os.getenv("OWNER_WHATSAPP")  # whatsapp:+50685742863
SALON_NAME  = os.getenv("SALON_NAME", "Nadira Fashion Salon")

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# ====== Utils ======
def _to_wa(num: str, cc="+506"):
    """
    Convierte un número crudo a formato WhatsApp E.164:
    - "85742863" -> "whatsapp:+50685742863"
    - "+50685742863" -> "whatsapp:+50685742863"
    """
    if not num:
        return None
    digits = re.sub(r"\D", "", str(num))
    if not digits:
        return None
    if len(digits) == 8:  # CR sin prefijo
        digits = cc + digits
    if not digits.startswith("+"):
        digits = "+" + digits
    return f"whatsapp:{digits}"

def _send_template(to_wa: str, content_sid: str, vars_dict: dict) -> bool:
    """Envía usando Messaging Service + Content Template (WhatsApp)."""
    if not (to_wa and MS_SID and content_sid):
        return False
    try:
        client.messages.create(
            messaging_service_sid=MS_SID,
            to=to_wa,
            content_sid=content_sid,
            content_variables=json.dumps(vars_dict or {})
        )
        return True
    except Exception as e:
        print("TWILIO ERROR:", e)
        return False

def _fmt_date(d): return d.strftime("%d/%m/%Y")
def _fmt_time(t): return t.strftime("%H:%M")

# ====== Públicos ======
def send_booking_notifications(appointment):
    """
    Confirmación inmediata:
    - Cliente: template de confirmación (CONF_SID)
    - Dueña:   template de confirmación (CONF_SID)
    """
    svc_name = getattr(getattr(appointment, "service", None), "name", "Servicio")
    d = _fmt_date(appointment.date)
    t = _fmt_time(appointment.time)

    vars_payload = {
        "1": appointment.customer_name,  # {{1}} Nombre
        "2": svc_name,                   # {{2}} Servicio
        "3": d,                          # {{3}} Fecha
        "4": t,                          # {{4}} Hora
        "5": SALON_NAME                  # {{5}} Salón
    }

    to_client = _to_wa(getattr(appointment, "customer_phone", ""))
    if to_client and CONF_SID:
        _send_template(to_client, CONF_SID, vars_payload)

    if OWNER_WA and CONF_SID:
        _send_template(OWNER_WA, CONF_SID, vars_payload)

def send_reminder_now(appointment):
    """
    Recordatorio (p. ej., por cron diario):
    - Cliente: template de recordatorio (REM_SID)
    - Dueña:   template de recordatorio (REM_SID)
    """
    svc_name = getattr(getattr(appointment, "service", None), "name", "Servicio")
    d = _fmt_date(appointment.date)
    t = _fmt_time(appointment.time)

    vars_payload = {
        "1": appointment.customer_name,
        "2": svc_name,
        "3": d,
        "4": t,
        "5": SALON_NAME
    }

    to_client = _to_wa(getattr(appointment, "customer_phone", ""))
    if to_client and REM_SID:
        _send_template(to_client, REM_SID, vars_payload)

    if OWNER_WA and REM_SID:
        _send_template(OWNER_WA, REM_SID, vars_payload)
