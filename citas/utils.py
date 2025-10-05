# -*- coding: utf-8 -*-
"""
Created on Sat Aug 23 20:40:56 2025

@author: jvz16
"""

import datetime
from .models import Appointment, BlockedSlot

def get_available_slots(date):
    start_time = datetime.time(9, 0)   # inicio jornada
    end_time = datetime.time(18, 0)    # fin jornada
    step = datetime.timedelta(minutes=30)

    slots = []
    current = datetime.datetime.combine(date, start_time)
    end = datetime.datetime.combine(date, end_time)

    reserved = Appointment.objects.filter(date=date).values_list("time", flat=True)
    blocked = BlockedSlot.objects.filter(date=date).values_list("time", flat=True)
    full_day_blocked = BlockedSlot.objects.filter(date=date, time__isnull=True).exists()

    if full_day_blocked:
        return []

    while current <= end:
        if current.time() not in reserved and current.time() not in blocked:
            slots.append(current.time())
        current += step
    return slots
