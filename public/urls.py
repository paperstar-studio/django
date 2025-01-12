from . import views, consumers
from django.urls import path


app_name = 'public'

urlpatterns = [
    # public
    path("", views.index, name="index"),
    path("fetch_fitbit/", views.fetch_fitbit, name="fetch_fitbit"),


    # PRIVATE views
    path("abel/", views.abel, name="abel"),
    #path("home/", views.home, name="home"),
    #path("week_52/", views.week_52, name="week_52"),

    #path("ws/presence", consumers.PresenceConsumer.as_asgi()),





]
