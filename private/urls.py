from . import views
from django.urls import path


app_name = 'private'

urlpatterns = [
    path("", views.index, name="index"),
    path("/ingestion", views.ingestion, name="ingestion"),
]
