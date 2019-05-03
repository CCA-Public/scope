from django.contrib.auth.models import Group
from django.urls import reverse
from django.test import TestCase
from unittest.mock import patch

from dips.models import User, Collection, DIP, DigitalFile, DublinCore


class UserAccessTests(TestCase):
    GET_PAGES = {
        "faq": [
            ("unauth", 200),
            ("admin", 200),
            ("manager", 200),
            ("editor", 200),
            ("basic", 200),
            ("viewer", 200),
        ],
        "home": [
            ("unauth", 302),
            ("admin", 200),
            ("manager", 200),
            ("editor", 200),
            ("basic", 200),
            ("viewer", 200),
        ],
        "search": [
            ("unauth", 302),
            ("admin", 200),
            ("manager", 200),
            ("editor", 200),
            ("basic", 200),
            ("viewer", 200),
        ],
        "users": [
            ("unauth", 302),
            ("admin", 200),
            ("manager", 200),
            ("editor", 302),
            ("basic", 302),
            ("viewer", 302),
        ],
        "new_user": [
            ("unauth", 302),
            ("admin", 200),
            ("manager", 200),
            ("editor", 302),
            ("basic", 302),
            ("viewer", 302),
        ],
        "edit_user": [
            ("unauth", 302),
            ("admin", 200),
            ("manager", 200),
            ("editor", 302),
            ("basic", 302),
            ("viewer", 302),
        ],
        "collection": [
            ("unauth", 302),
            ("admin", 200),
            ("manager", 200),
            ("editor", 200),
            ("basic", 200),
            ("viewer", 200),
        ],
        "collections": [
            ("unauth", 302),
            ("admin", 200),
            ("manager", 200),
            ("editor", 200),
            ("basic", 200),
            ("viewer", 200),
        ],
        "new_collection": [
            ("unauth", 302),
            ("admin", 200),
            ("manager", 302),
            ("editor", 200),
            ("basic", 302),
            ("viewer", 302),
        ],
        "edit_collection": [
            ("unauth", 302),
            ("admin", 200),
            ("manager", 302),
            ("editor", 200),
            ("basic", 302),
            ("viewer", 302),
        ],
        "delete_collection": [
            ("unauth", 302),
            ("admin", 200),
            ("manager", 302),
            ("editor", 302),
            ("basic", 302),
            ("viewer", 302),
        ],
        "dip": [
            ("unauth", 302),
            ("admin", 200),
            ("manager", 200),
            ("editor", 200),
            ("basic", 200),
            ("viewer", 200),
        ],
        "new_dip": [
            ("unauth", 302),
            ("admin", 200),
            ("manager", 302),
            ("editor", 200),
            ("basic", 302),
            ("viewer", 302),
        ],
        "edit_dip": [
            ("unauth", 302),
            ("admin", 200),
            ("manager", 302),
            ("editor", 200),
            ("basic", 302),
            ("viewer", 302),
        ],
        "delete_dip": [
            ("unauth", 302),
            ("admin", 200),
            ("manager", 302),
            ("editor", 302),
            ("basic", 302),
            ("viewer", 302),
        ],
        "orphan_dips": [
            ("unauth", 302),
            ("admin", 200),
            ("manager", 302),
            ("editor", 200),
            ("basic", 302),
            ("viewer", 302),
        ],
        "download_dip": [
            ("unauth", 302),
            ("admin", 404),
            ("manager", 404),
            ("editor", 404),
            ("basic", 404),
            ("viewer", 404),
        ],
        "digital_file": [
            ("unauth", 302),
            ("admin", 200),
            ("manager", 200),
            ("editor", 200),
            ("basic", 200),
            ("viewer", 200),
        ],
        "settings": [
            ("unauth", 302),
            ("admin", 200),
            ("manager", 302),
            ("editor", 302),
            ("basic", 302),
            ("viewer", 302),
        ],
    }

    @patch("elasticsearch_dsl.DocType.save")
    def setUp(self, mock_es_save):
        # Create test users
        User.objects.create_superuser("admin", "admin@example.com", "admin")
        User.objects.create_user("basic", "basic@example.com", "basic")
        manager_user = User.objects.create_user(
            "manager", "manager@example.com", "manager"
        )
        group = Group.objects.get(name="Managers")
        manager_user.groups.add(group)
        editor_user = User.objects.create_user("editor", "editor@example.com", "editor")
        group = Group.objects.get(name="Editors")
        editor_user.groups.add(group)
        viewer_user = User.objects.create_user("viewer", "viewer@example.com", "viewer")
        group = Group.objects.get(name="Viewers")
        viewer_user.groups.add(group)

        # Create editable resources
        self.user = User.objects.create_user("test", "test@example.com", "test")
        self.collection = Collection.objects.create(
            dc=DublinCore.objects.create(identifier="1")
        )
        self.dip = DIP.objects.create(
            dc=DublinCore.objects.create(identifier="A"),
            collection=self.collection,
            objectszip="fake.zip",
        )
        self.digital_file = DigitalFile.objects.create(
            uuid="e75c7789-7ebf-41b3-a233-39d4003e42ec", dip=self.dip, size_bytes=1
        )

    @patch("elasticsearch_dsl.Search.execute")
    @patch("elasticsearch_dsl.Search.count", return_value=0)
    def test_get_pages(self, mock_es_count, mock_es_exec):
        """Get pages test.

        Makes get requests to pages with different user types logged in
        and verifies if the user can see the page or gets redirected.
        """
        for page, responses in self.GET_PAGES.items():
            if page in ["edit_user"]:
                url = reverse(page, kwargs={"pk": self.user.pk})
            elif page in ["collection", "edit_collection", "delete_collection"]:
                url = reverse(page, kwargs={"pk": self.collection.pk})
            elif page in ["dip", "edit_dip", "delete_dip", "download_dip"]:
                url = reverse(page, kwargs={"pk": self.dip.pk})
            elif page in ["digital_file"]:
                url = reverse(page, kwargs={"pk": self.digital_file.pk})
            else:
                url = reverse(page)

            for user, code in responses:
                if user != "unauth":
                    self.client.login(username=user, password=user)
                response = self.client.get(url)
                self.assertEqual(response.status_code, code)
                self.client.logout()

    def test_post_user(self):
        """Post user test.

        Makes post requests to create and edit user pages with different
        user types logged in and verifies the results.
        """
        new_url = reverse("new_user")
        new_data = {
            "username": "test2",
            "password1": "test123test",
            "password2": "test123test",
        }
        new_data_2 = {
            "username": "test3",
            "password1": "test123test",
            "password2": "test123test",
        }
        edit_url = reverse("edit_user", kwargs={"pk": self.user.pk})
        edit_data = {"username": "test_changed"}
        edit_data_2 = {"username": "test_changed_2"}

        # Unauthenticated, create
        before_count = len(User.objects.all())
        response = self.client.post(new_url, new_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/login/?next=/new_user/")
        after_count = len(User.objects.all())
        self.assertEqual(before_count, after_count)
        # Unauthenticated, edit
        response = self.client.post(edit_url, edit_data)
        self.assertEqual(response.status_code, 302)
        next_url = "/login/?next=/user/%s/edit" % self.user.pk
        self.assertEqual(response.url, next_url)
        self.assertFalse(User.objects.filter(username="test_changed").exists())

        # Basic and Viewer
        for user in ["basic", "viewer"]:
            # Create
            self.client.login(username=user, password=user)
            before_count = len(User.objects.all())
            response = self.client.post(new_url, new_data)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, "/")
            after_count = len(User.objects.all())
            self.assertEqual(before_count, after_count)
            # Edit
            response = self.client.post(edit_url, edit_data)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, "/")
            self.assertFalse(User.objects.filter(username="test_changed").exists())
            self.client.logout()

        # Editor, create
        self.client.login(username="editor", password="editor")
        before_count = len(User.objects.all())
        response = self.client.post(new_url, new_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")
        after_count = len(User.objects.all())
        self.assertEqual(before_count, after_count)
        # Editor, edit
        response = self.client.post(edit_url, edit_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")
        self.assertFalse(User.objects.filter(username="test_changed").exists())
        self.client.logout()

        # Manager, create
        self.client.login(username="manager", password="manager")
        before_count = len(User.objects.all())
        response = self.client.post(new_url, new_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/users/")
        after_count = len(User.objects.all())
        self.assertEqual(before_count + 1, after_count)
        # Manager, edit
        response = self.client.post(edit_url, edit_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/users/")
        self.assertTrue(User.objects.filter(username="test_changed").exists())
        self.client.logout()

        # Admin, create
        self.client.login(username="admin", password="admin")
        before_count = len(User.objects.all())
        response = self.client.post(new_url, new_data_2)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/users/")
        after_count = len(User.objects.all())
        self.assertEqual(before_count + 1, after_count)
        # Admin, edit
        response = self.client.post(edit_url, edit_data_2)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/users/")
        self.assertTrue(User.objects.filter(username="test_changed_2").exists())
        self.client.logout()

    @patch("elasticsearch_dsl.DocType.save")
    @patch("dips.models.celery_app.send_task")
    def test_post_collection(self, mock_send_task, mock_es_save):
        """Post collection test.

        Makes post requests to create and edit collection pages with different
        user types logged in and verifies the results.
        """
        new_url = reverse("new_collection")
        new_data = {"identifier": "2"}
        new_data_2 = {"identifier": "3"}
        edit_url = reverse("edit_collection", kwargs={"pk": self.collection.pk})
        edit_data = {"identifier": "1", "title": "test_collection_2"}
        edit_data_2 = {"identifier": "1", "title": "test_collection_3"}

        # Unauthenticated, create
        before_count = len(Collection.objects.all())
        response = self.client.post(new_url, new_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/login/?next=/new_collection/")
        after_count = len(Collection.objects.all())
        self.assertEqual(before_count, after_count)
        # Unauthenticated, edit
        response = self.client.post(edit_url, edit_data)
        self.assertEqual(response.status_code, 302)
        next_url = "/login/?next=/collection/%s/edit/" % self.collection.pk
        self.assertEqual(response.url, next_url)
        self.assertFalse(
            Collection.objects.filter(dc__title="test_collection_2").exists()
        )

        # Basic and Viewer
        for user in ["basic", "viewer"]:
            # Create
            self.client.login(username=user, password=user)
            before_count = len(Collection.objects.all())
            response = self.client.post(new_url, new_data)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, "/")
            after_count = len(Collection.objects.all())
            self.assertEqual(before_count, after_count)
            # Edit
            response = self.client.post(edit_url, edit_data)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, "/collection/%s/" % self.collection.pk)
            self.assertFalse(
                Collection.objects.filter(dc__title="test_collection_2").exists()
            )
            self.client.logout()

        # Editor, create
        self.client.login(username="editor", password="editor")
        before_count = len(Collection.objects.all())
        response = self.client.post(new_url, new_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/collections/")
        after_count = len(Collection.objects.all())
        self.assertEqual(before_count + 1, after_count)
        # Editor, edit
        response = self.client.post(edit_url, edit_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/collection/%s/" % self.collection.pk)
        self.assertTrue(
            Collection.objects.filter(dc__title="test_collection_2").exists()
        )
        self.client.logout()

        # Manager, create
        self.client.login(username="manager", password="manager")
        before_count = len(Collection.objects.all())
        response = self.client.post(new_url, new_data_2)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")
        after_count = len(Collection.objects.all())
        self.assertEqual(before_count, after_count)
        # Manager, edit
        response = self.client.post(edit_url, edit_data_2)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/collection/%s/" % self.collection.pk)
        self.assertFalse(
            Collection.objects.filter(dc__title="test_collection_3").exists()
        )
        self.client.logout()

        # Admin, create
        self.client.login(username="admin", password="admin")
        before_count = len(Collection.objects.all())
        response = self.client.post(new_url, new_data_2)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/collections/")
        after_count = len(Collection.objects.all())
        self.assertEqual(before_count + 1, after_count)
        # Admin, edit
        response = self.client.post(edit_url, edit_data_2)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/collection/%s/" % self.collection.pk)
        self.assertTrue(
            Collection.objects.filter(dc__title="test_collection_3").exists()
        )
        self.client.logout()

    @patch("elasticsearch_dsl.DocType.save")
    @patch("dips.models.celery_app.send_task")
    def test_post_dip(self, mock_send_task, mock_es_save):
        """Post DIP test.

        Makes post requests to create and edit DIP pages with different
        user types logged in and verifies the results.
        """
        new_url = reverse("new_dip")
        new_data = {"identifier": "B", "collection": self.collection.pk}
        edit_url = reverse("edit_dip", kwargs={"pk": self.dip.pk})
        edit_data = {"identifier": "A", "title": "test_dip_2"}
        edit_data_2 = {"identifier": "A", "title": "test_dip_3"}

        # Unauthenticated, create
        before_count = len(DIP.objects.all())
        response = self.client.post(new_url, new_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/login/?next=/new_folder/")
        after_count = len(DIP.objects.all())
        self.assertEqual(before_count, after_count)
        # Unauthenticated, edit
        response = self.client.post(edit_url, edit_data)
        self.assertEqual(response.status_code, 302)
        next_url = "/login/?next=/folder/%s/edit/" % self.dip.pk
        self.assertEqual(response.url, next_url)
        self.assertFalse(DIP.objects.filter(dc__title="test_dip_2").exists())

        # Basic and Viewer
        for user in ["basic", "viewer"]:
            # Create
            self.client.login(username=user, password=user)
            before_count = len(DIP.objects.all())
            response = self.client.post(new_url, new_data)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, "/")
            after_count = len(DIP.objects.all())
            self.assertEqual(before_count, after_count)
            # Edit
            response = self.client.post(edit_url, edit_data)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, "/folder/%s/" % self.dip.pk)
            self.assertFalse(DIP.objects.filter(dc__title="test_dip_2").exists())
            self.client.logout()

        # Editor, create
        self.client.login(username="editor", password="editor")
        # To avoid testing the file upload in here, the form validation
        # should fail, returnnig a 200 status code with errors in the form.
        response = self.client.post(new_url, new_data)
        form = response.context.get("dip_form")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(form.fields["objectszip"].error_messages)
        # Editor, edit
        response = self.client.post(edit_url, edit_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/folder/%s/" % self.dip.pk)
        self.assertTrue(DIP.objects.filter(dc__title="test_dip_2").exists())
        self.client.logout()

        # Manager, create
        self.client.login(username="manager", password="manager")
        before_count = len(DIP.objects.all())
        response = self.client.post(new_url, new_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")
        after_count = len(DIP.objects.all())
        self.assertEqual(before_count, after_count)
        # Manager, edit
        response = self.client.post(edit_url, edit_data_2)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/folder/%s/" % self.dip.pk)
        self.assertFalse(DIP.objects.filter(dc__title="test_dip_3").exists())
        self.client.logout()

        # Admin, create
        self.client.login(username="admin", password="admin")
        # To avoid testing the file upload in here, the form validation
        # should fail, returnnig a 200 status code with errors in the form.
        response = self.client.post(new_url, new_data)
        form = response.context.get("dip_form")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(form.fields["objectszip"].error_messages)
        # Admin, edit
        response = self.client.post(edit_url, edit_data_2)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/folder/%s/" % self.dip.pk)
        self.assertTrue(DIP.objects.filter(dc__title="test_dip_3").exists())
        self.client.logout()

    @patch("dips.models.delete_document")
    @patch("dips.models.celery_app.send_task")
    def test_delete_dip(self, mock_send_task, mock_es_delete):
        """Delete DIP test.

        Makes post request to delete a DIP with different
        user types logged in and verifies the results.
        """
        url = reverse("delete_dip", kwargs={"pk": self.dip.pk})
        data = {"identifier": "A"}

        # Unauthenticated
        before_count = len(DIP.objects.all())
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        next_url = "/login/?next=/folder/%s/delete/" % self.dip.pk
        self.assertEqual(response.url, next_url)
        after_count = len(DIP.objects.all())
        self.assertEqual(before_count, after_count)

        # Basic and Viewer
        for user in ["basic", "viewer"]:
            self.client.login(username=user, password=user)
            before_count = len(DIP.objects.all())
            response = self.client.post(url, data)
            self.assertEqual(response.status_code, 302)
            next_url = "/folder/%s/" % self.dip.pk
            self.assertEqual(response.url, next_url)
            after_count = len(DIP.objects.all())
            self.assertEqual(before_count, after_count)

        # Editor
        self.client.login(username="editor", password="editor")
        before_count = len(DIP.objects.all())
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        next_url = "/folder/%s/" % self.dip.pk
        self.assertEqual(response.url, next_url)
        after_count = len(DIP.objects.all())
        self.assertEqual(before_count, after_count)

        # Manager
        self.client.login(username="manager", password="manager")
        before_count = len(DIP.objects.all())
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        next_url = "/folder/%s/" % self.dip.pk
        self.assertEqual(response.url, next_url)
        after_count = len(DIP.objects.all())
        self.assertEqual(before_count, after_count)

        # Admin
        self.client.login(username="admin", password="admin")
        before_count = len(DIP.objects.all())
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/collection/%s/" % self.collection.pk)
        after_count = len(DIP.objects.all())
        self.assertEqual(before_count, after_count + 1)

    @patch("dips.models.delete_document")
    @patch("dips.models.celery_app.send_task")
    def test_delete_collection(self, mock_send_task, mock_es_delete):
        """Delete collection test.

        Makes post request to delete a collection with different
        user types logged in and verifies the results.
        """
        url = reverse("delete_collection", kwargs={"pk": self.collection.pk})
        data = {"identifier": "1"}

        # Unauthenticated
        before_count = len(Collection.objects.all())
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        next_url = "/login/?next=/collection/%s/delete/" % self.collection.pk
        self.assertEqual(response.url, next_url)
        after_count = len(Collection.objects.all())
        self.assertEqual(before_count, after_count)

        # Basic and Viewer
        for user in ["basic", "viewer"]:
            self.client.login(username=user, password=user)
            before_count = len(Collection.objects.all())
            response = self.client.post(url, data)
            self.assertEqual(response.status_code, 302)
            next_url = "/collection/%s/" % self.collection.pk
            self.assertEqual(response.url, next_url)
            after_count = len(Collection.objects.all())
            self.assertEqual(before_count, after_count)

        # Editor
        self.client.login(username="editor", password="editor")
        before_count = len(Collection.objects.all())
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        next_url = "/collection/%s/" % self.collection.pk
        self.assertEqual(response.url, next_url)
        after_count = len(Collection.objects.all())
        self.assertEqual(before_count, after_count)

        # Manager
        self.client.login(username="manager", password="manager")
        before_count = len(Collection.objects.all())
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        next_url = "/collection/%s/" % self.collection.pk
        self.assertEqual(response.url, next_url)
        after_count = len(Collection.objects.all())
        self.assertEqual(before_count, after_count)

        # Admin
        self.client.login(username="admin", password="admin")
        before_count = len(Collection.objects.all())
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/collections/")
        after_count = len(Collection.objects.all())
        self.assertEqual(before_count, after_count + 1)
