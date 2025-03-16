from . import views
from django.urls import path


app_name = 'blog'

urlpatterns = [
    # public
    path("", views.mar_2025, name="mar_2025"),

]
