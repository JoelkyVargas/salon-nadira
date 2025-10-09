# -*- coding: utf-8 -*-
"""
Created on Wed Oct  8 17:26:58 2025

@author: jvz16
"""

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from citas.models import Appointment
from citas.whatsapp import send_reminder_now

class Command(BaseCommand):
    help = "Envía recordatorios de WhatsApp para las citas de mañana (cliente y propietaria)."

    def handle(self, *args, **options):
        target = date.today() + timedelta(days=1)
        qs = Appointment.objects.select_related("service").filter(date=target)
        count = 0
        for ap in qs:
            try:
                send_reminder_now(ap)
                count += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error con {ap.id}: {e}"))
        self.stdout.write(self.style.SUCCESS(f"Recordatorios enviados: {count}"))
