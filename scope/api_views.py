from celery import chain
from django.conf import settings
from rest_framework import authentication
from rest_framework import permissions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from scope.models import DIP
from scope.models import DublinCore
from scope.tasks import download_mets
from scope.tasks import parse_mets
from scope.tasks import save_import_error


class DIPStoredWebhook(APIView):
    """Webhook called when a new DIP is stored."""

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAdminUser,)

    def post(self, request, dip_uuid, format=None):
        # Check origin header
        origin = request.META.get("HTTP_ORIGIN")
        if not origin:
            return Response(
                {"detail": "Origin not set in the request headers."},
                status=status.HTTP_403_FORBIDDEN,
            )
        # Find SS configuration based on origin
        if origin not in settings.SS_HOSTS.keys():
            return Response(
                {"detail": "SS host not configured for Origin: %s" % origin},
                status=status.HTTP_403_FORBIDDEN,
            )
        # Get download URL from request content
        download_url = request.data.get("download_url")
        if not download_url:
            # Otherwise, build SS API v2 URL
            download_url = "%s/api/v2/file/%s/download/" % (origin, dip_uuid)
        # Create DIP or fail if already exists
        dip, created = DIP.objects.get_or_create(
            ss_uuid=dip_uuid,
            defaults=dict(
                ss_uuid=dip_uuid,
                ss_host_url=origin,
                ss_download_url=download_url,
                dc=DublinCore.objects.create(identifier=dip_uuid),
                import_status=DIP.IMPORT_PENDING,
            ),
        )
        if not created:
            return Response(
                {"detail": "A DIP already exists with the same UUID: %s" % dip_uuid},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        # Download and parse METS file asynchronously
        chain(download_mets.s(dip.pk), parse_mets.s(dip.pk)).on_error(
            save_import_error.s(dip_id=dip.pk)
        ).delay()
        return Response(
            {"message": "DIP stored event accepted: %s" % dip_uuid},
            status=status.HTTP_202_ACCEPTED,
        )
