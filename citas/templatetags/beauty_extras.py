# -*- coding: utf-8 -*-
"""
Created on Tue Nov 25 17:16:39 2025

@author: jvz16
"""

# citas/templatetags/beauty_extras.py
from django import template

register = template.Library()


@register.filter
def price_dots(value):
    """
    Formatea un número como entero con separador de miles usando punto.
    Ej: 15000 -> "15.000"
    Si no es número, se devuelve tal cual.
    """
    try:
        value_int = int(value)
    except (TypeError, ValueError):
        return value

    # Primero formateamos con comas: 15000 -> "15,000"
    formatted = f"{value_int:,}"
    # Reemplazamos coma por punto: "15.000"
    return formatted.replace(",", ".")
