from . import views, consumers
from django.urls import path


app_name = 'public'

urlpatterns = [
    path("", views.index, name="index"),

    path("home/", views.home, name="home"),
    path("week_52/", views.week_52, name="week_52"),

    path("sleep/", views.sleep, name="sleep"),

    path("ws/presence", consumers.PresenceConsumer.as_asgi()),



    path("fetch_fitbit/", views.fetch_fitbit, name="fetch_fitbit"),

]
