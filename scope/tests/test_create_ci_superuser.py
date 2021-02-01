from django.core.management import call_command
from django.test import TestCase

from scope.models import User


class CreateCiSuperuserTests(TestCase):
    def test_superuser_creation(self):
        call_command("create_ci_superuser")
        self.assertTrue(User.objects.filter(username="ci_admin").exists())
