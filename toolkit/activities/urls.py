from django.urls import path

from . import views

app_name = 'activities'

urlpatterns = [
    path('install/', views.install, name='install'),
    path('uninstall/', views.uninstall, name='uninstall'),
    path('operator-add/', views.operator_add, name='operator_add'),
    path('pause/', views.pause, name='pause'),
    path('field-update/', views.field_update, name='field_update'),
]
