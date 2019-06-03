from django.contrib.auth.models import Group
from django.db.migrations.executor import MigrationExecutor
from django.db import connection
from django.test import TransactionTestCase

from dips.models import Content


class TestMigrations(TransactionTestCase):
    """Uses TransactionTestCase to perform rollbacks."""

    def setUp(self):
        self.executor = MigrationExecutor(connection)

    def test_rollbacks(self):
        """Checks that migration rollbacks run correctly.

        Perform all rollbacks in order in the same test to maintain DB status.
        """
        # Initial counts
        self.assertEqual(Group.objects.count(), 3)
        self.assertEqual(Content.objects.count(), 3)

        # Content removal
        self.executor.migrate([("dips", "0009_content")])
        self.assertEqual(Content.objects.count(), 0)

        # Groups removal
        self.executor.migrate([("dips", "0001_initial")])
        self.assertEqual(Group.objects.count(), 0)
