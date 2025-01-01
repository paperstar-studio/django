from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),

    path("", include('public.urls', namespace="public")),

    path('django_plotly_dash/', include('django_plotly_dash.urls')),

    path('accounts/', include('django.contrib.auth.urls')),

    #path('sitemap.xml', sitemap),
]
