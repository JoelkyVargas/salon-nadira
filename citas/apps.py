# salon/citas/apps.py
from django.apps import AppConfig

class CitasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "salon.citas"
    label = "citas"                 # app_label usado por el admin
    verbose_name = "Agenda"         # ← nombre en el sidebar del admin
