# -*- coding: utf-8 -*-
"""
Created on Tue Oct 28 21:31:45 2025

@author: jvz16
"""

# salon/citas/models.py
from django.db import models


class ServiceCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Categoria de servicio"
        verbose_name_plural = "Categorias de servicio"

    def __str__(self):
        return self.name


class Service(models.Model):
    name = models.CharField(max_length=100, unique=True)
    # NUEVO: categoría opcional
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="services",
    )
    duration_minutes = models.PositiveIntegerField(default=60)
    color = models.CharField(max_length=7, default="#0d6efd")
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"


class Appointment(models.Model):
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=20)
    service = models.ForeignKey(
        Service,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
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


class Testimonial(models.Model):
    name = models.CharField(max_length=100)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name}"


class BeforeAfter(models.Model):
    testimonial = models.ForeignKey(
        Testimonial,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    before_image = models.ImageField(upload_to="before_after/")
    after_image = models.ImageField(upload_to="before_after/")
    caption = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Before/After de {self.testimonial.name}"


class HomeBackground(models.Model):
    """
    Imagen de fondo para la página principal (home).
    Solo necesitarás 1 registro activo normalmente.
    """
    image = models.ImageField(upload_to="home_backgrounds/")
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Fondo de inicio"
        verbose_name_plural = "Fondos de inicio"

    def __str__(self):
        return f"Fondo {self.pk}"


class Promotion(models.Model):
    """
    Promociones visibles en la web.
    Algunas pueden ser solo para clientes VIP.
    """
    title = models.CharField("Título", max_length=150)
    description = models.TextField("Descripción", blank=True)
    image = models.ImageField(upload_to="promotions/", blank=True, null=True)
    price = models.DecimalField(
        "Precio",
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
    )
    consult_price_with_owner = models.BooleanField(
        "Mostrar 'Consultar precio con propietaria'",
        default=False,
    )
    is_vip_only = models.BooleanField(
        "Solo clientes VIP",
        default=False,
        help_text="Si está marcado, la promo solo se mostrará en la sección VIP.",
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Promoción"
        verbose_name_plural = "Promociones"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class VipCode(models.Model):
    """
    Código VIP de 4 dígitos.
    - Puede ser definido manualmente por tu esposa.
    - Si se deja en blanco en el admin, se genera automáticamente.
    """
    code = models.CharField(
        "Código (4 dígitos)",
        max_length=4,
        unique=True,
        blank=True,
        help_text="Si lo dejas en blanco, se generará automáticamente.",
    )
    client_name = models.CharField(
        "Nombre de la clienta",
        max_length=100,
        blank=True,
    )
    notes = models.CharField("Notas", max_length=200, blank=True)
    active = models.BooleanField("Activo", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Código VIP"
        verbose_name_plural = "Códigos VIP"
        ordering = ["-created_at"]

    def __str__(self):
        if self.client_name:
            return f"{self.code or '----'} - {self.client_name}"
        return self.code or "Código VIP sin definir"

