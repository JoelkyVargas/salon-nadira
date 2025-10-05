# salon/citas/models.py (fragmento: añade Meta a cada modelo)
from django.db import models

class Service(models.Model):
    name = models.CharField(max_length=100, unique=True)
    duration_minutes = models.PositiveIntegerField(default=60)
    color = models.CharField(max_length=7, default="#0d6efd")
    active = models.BooleanField(default=True)
    def __str__(self): return self.name
    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"

class Appointment(models.Model):
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=20)
    service = models.ForeignKey(Service, null=True, blank=True, on_delete=models.SET_NULL)
    date = models.DateField()
    time = models.TimeField()
    def __str__(self):
        return f"{self.customer_name} - {self.service} ({self.date} {self.time})"
    class Meta:
        verbose_name = "Cita"
        verbose_name_plural = "Citas"

class BlockedSlot(models.Model):
    date = models.DateField()
    time = models.TimeField(blank=True, null=True)
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    reason = models.CharField(max_length=200, blank=True)
    def __str__(self):
        if self.start_time and self.end_time:
            return f"Bloqueo {self.date} {self.start_time}-{self.end_time} - {self.reason}"
        if self.time:
            return f"Bloqueo {self.date} {self.time} - {self.reason}"
        return f"Bloqueo {self.date} (todo el día) - {self.reason}"
    class Meta:
        verbose_name = "Auto bloqueo"
        verbose_name_plural = "Auto bloqueos"
