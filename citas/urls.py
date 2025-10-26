from django.urls import path
from . import views

urlpatterns = [
    path('',views.home, name="home"), 
    path('reservar/', views.reservar_cita, name='reservar_cita'),
    path('agenda/', views.calendar_view, name='calendar_view'),
    path('api/appointments/', views.appointments_json, name='appointments_json'),
    path('api/available-times/', views.available_times_json, name='available_times_json'),  # ← NUEVO
    path('listar/', views.appointments_list, name='appointments_list'),
    path('servicios/', views.servicios, name='servicios'),
    path('testimonios/', views.testimonios, name='testimonios'),
]
