from django.core.management.base import BaseCommand

from scope.models import User


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        """Create super user without interaction.

        Remove this command after upgrading to Django 3.x and use
        the default createsuperuser command with env. variables.
        """
        User.objects.create_superuser("ci_admin", "ci_admin@example.com", "ci_admin")
