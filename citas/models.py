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
    # categoría opcional
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


# =======================
# PAQUETES / PROMOCIONES
# =======================

class Promotion(models.Model):
    """
    Paquetes/promociones visibles en la web.
    - Algunas pueden ser solo VIP (vip_only=True)
    - show_price=False muestra el texto "Consultar precio con propietaria"
    """
    title = models.CharField("Título", max_length=120)
    description = models.TextField("Descripción", blank=True)
    image = models.ImageField(upload_to="promotions/", blank=True, null=True)
    price = models.DecimalField(
        "Precio",
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
    )
    show_price = models.BooleanField(
        "Mostrar precio al cliente",
        default=True,
        help_text="Si se desmarca, se mostrará 'Consultar precio con propietaria'.",
    )
    vip_only = models.BooleanField(
        "Solo Clientes VIP",
        default=False,
        help_text="Si se marca, este paquete solo se mostrará en la sección VIP.",
    )
    active = models.BooleanField("Activo", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Paquete"
        verbose_name_plural = "Paquetes"

    def __str__(self):
        return self.title

    def display_price(self):
        if not self.show_price or self.price is None:
            return "Consultar precio con propietaria"
        # Formato simple, lo puedes adaptar a colones/dólares
        return f"{self.price:.0f}"
    display_price.short_description = "Precio visible"


class VIPClientCode(models.Model):
    """
    Código VIP por clienta.
    """
    code = models.CharField(
        "Código VIP",
        max_length=10,
        unique=True,
        help_text="Puede ser numérico de 4 dígitos o cualquier texto único.",
    )
    note = models.CharField(
        "Nota / Nombre clienta",
        max_length=200,
        blank=True,
        help_text="Referencia interna (ej. nombre de la clienta).",
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Código VIP"
        verbose_name_plural = "Códigos VIP"

    def __str__(self):
        return self.code
