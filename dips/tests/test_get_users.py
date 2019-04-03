from django.contrib.auth.models import Group
from django.test import TestCase

from dips.models import User


class GetUsersTests(TestCase):
    USERS = [
        {
            "username": "JohnDoe",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "groups": ["Viewers"],
        },
        {
            "username": "JaneDoe",
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.com",
            "groups": ["Editors", "Managers"],
        },
        {
            "username": "JuanPerez",
            "first_name": "Juan",
            "last_name": "Perez",
            "email": "juan@test.com",
            "groups": ["Editors"],
        },
        {
            "username": "MariaPerez",
            "first_name": "Maria",
            "last_name": "Perez",
            "email": "maria@test.com",
            "groups": ["Managers", "Editors", "Viewers"],
        },
    ]

    @classmethod
    def setUpTestData(cls):
        for user in cls.USERS:
            groups = user.pop("groups", None)
            user = User.objects.create(**user)
            if groups:
                for group_name in groups:
                    group = Group.objects.filter(name=group_name).get()
                    user.groups.add(group)

    def test_get_users_no_params(self):
        """Get all users without filtering, sorted by default (username)."""
        users = User.get_users()
        self.assertEqual(users.count(), 4)
        first_user = users[0]
        last_user = users[3]
        self.assertEqual(first_user.username, "JaneDoe")
        self.assertEqual(last_user.username, "MariaPerez")

    def test_get_users_sort_by_group(self):
        """Get all users, sorted by group names concatenation."""
        users = User.get_users(sort_field="group_names")
        self.assertEqual(users.count(), 4)
        first_user = users[0]
        last_user = users[3]
        self.assertEqual(first_user.username, "JuanPerez")
        self.assertEqual(last_user.username, "JohnDoe")

    def test_get_users_with_query(self):
        """Filter users by query"""
        # Filter by query
        users = User.get_users(query="Doe")
        self.assertEqual(users.count(), 2)
        # Should be case insensitive
        users = User.get_users(query="doe")
        self.assertEqual(users.count(), 2)
        # Should query 'first_name'
        users = User.get_users(query="Jane")
        self.assertEqual(users.count(), 1)
        # Should query 'last_name'
        users = User.get_users(query="Perez")
        self.assertEqual(users.count(), 2)
        # Should query 'email'
        users = User.get_users(query="example")
        self.assertEqual(users.count(), 2)
        # Should query group names concatenation
        users = User.get_users(query="editors, managers")
        self.assertEqual(users.count(), 2)
