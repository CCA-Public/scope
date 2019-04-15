from django.urls import path

from . import api_views


urlpatterns = [
    path(
        "dip/<uuid:dip_uuid>/stored",
        api_views.DIPStoredWebhook().as_view(),
        name="dip_stored_webhook",
    )
]
