from rest_framework import authentication, permissions
from rest_framework.response import Response
from rest_framework.views import APIView


class DIPStoredWebhook(APIView):
    """Webhook called when a new DIP is stored."""

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAdminUser,)

    def post(self, request, dip_uuid, format=None):
        return Response({"message": f"DIP stored event: {dip_uuid}"})
