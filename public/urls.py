from . import views
from django.urls import path


app_name = 'public'

urlpatterns = [
    # public
    path("", views.index, name="index"),
    path("fetch_fitbit/", views.fetch_fitbit, name="fetch_fitbit"),


    # PRIVATE views
    path("abel/", views.abel, name="abel"),
    path(r'myajaxformview', views.myajaxformview, name='myajaxformview'),
    path("dot/", views.dot, name="dot"),

]
