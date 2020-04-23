from django.contrib.auth.models import Group
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from scope.models import Content
from scope.models import Setting


class TestMigrations(TransactionTestCase):
    """Uses TransactionTestCase to perform rollbacks."""

    def setUp(self):
        self.executor = MigrationExecutor(connection)

    def test_rollbacks(self):
        """Checks that migration rollbacks run correctly.

        Perform all rollbacks in order in the same test to maintain DB status.
        """
        # Initial data counts
        self.assertEqual(Group.objects.count(), 3)
        self.assertEqual(Setting.objects.count(), 2)
        self.assertEqual(Content.objects.count(), 3)

        # Initial data removal
        self.executor.migrate([("scope", "0001_initial")])
        self.assertEqual(Group.objects.count(), 0)
        self.assertEqual(Setting.objects.count(), 0)
        self.assertEqual(Content.objects.count(), 0)
