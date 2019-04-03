from django.contrib.auth.models import Group
from django.urls import reverse
from django.test import TestCase

from dips.models import User


class UserGroupsTests(TestCase):
    def setUp(self):
        User.objects.create_superuser("admin", "admin@example.com", "admin")
        self.manager, _ = Group.objects.get_or_create(name="Managers")
        self.editor, _ = Group.objects.get_or_create(name="Editors")
        self.group_a, _ = Group.objects.get_or_create(name="Group A")
        self.group_b, _ = Group.objects.get_or_create(name="Group B")
        self.group_c, _ = Group.objects.get_or_create(name="Group C")
        self.client.login(username="admin", password="admin")

    def test_user_groups_changes(self):
        # New user without groups
        url = reverse("new_user")
        data = {
            "username": "test",
            "password1": "test123test",
            "password2": "test123test",
        }
        self.client.post(url, data)
        created_user = User.objects.filter(username="test").get()
        self.assertFalse(created_user.is_editor())
        self.assertFalse(created_user.is_manager())
        self.assertEqual(created_user.group_names(), "")

        # New user with groups
        data = {
            "username": "test2",
            "password1": "test123test",
            "password2": "test123test",
            "groups": [self.editor.pk, self.manager.pk],
        }
        self.client.post(url, data)
        created_user_2 = User.objects.filter(username="test2").get()
        self.assertTrue(created_user_2.is_editor())
        self.assertTrue(created_user_2.is_manager())
        self.assertEqual(created_user_2.group_names(), "Editors, Managers")

        # Edit user adding groups
        url = reverse("edit_user", kwargs={"pk": created_user.pk})
        data = {"username": "test", "groups": [self.editor.pk, self.group_c.pk]}
        self.client.post(url, data)
        created_user = User.objects.filter(username="test").get()
        self.assertTrue(created_user.is_editor())
        self.assertEqual(created_user.group_names(), "Editors, Group C")

        # Edit user removing groups
        url = reverse("edit_user", kwargs={"pk": created_user_2.pk})
        data = {"username": "test2", "groups": []}
        self.client.post(url, data)
        created_user_2 = User.objects.filter(username="test2").get()
        self.assertFalse(created_user_2.is_editor())
        self.assertEqual(created_user_2.group_names(), "")

        # Edit user changing groups
        url = reverse("edit_user", kwargs={"pk": created_user.pk})
        data = {"username": "test", "groups": [self.group_a.pk, self.group_b.pk]}
        self.client.post(url, data)
        created_user = User.objects.filter(username="test").get()
        self.assertFalse(created_user.is_editor())
        self.assertEqual(created_user.group_names(), "Group A, Group B")

    def test_administrator_is_editor(self):
        admin_user = User.objects.filter(username="admin").get()
        self.assertEqual(admin_user.group_names(), "")
        self.assertTrue(admin_user.is_editor())
