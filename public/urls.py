from . import views
from django.urls import path


app_name = 'public'

urlpatterns = [
    path("", views.index, name="index"),
    path('reload_sleep/', views.reload_sleep, name='reload_sleep'),
]
