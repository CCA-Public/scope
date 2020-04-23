from __future__ import unicode_literals

from django.contrib.auth.management import create_permissions
from django.db import migrations

from scope.models import Content
from scope.models import DublinCore
from scope.models import Setting


def migrate_permissions(apps, schema_editor):
    """Create permissions in migrations.

    Needed before they are created in a post_migrate signal handler to create
    the user groups. The signal handler won't create duplicated permissions.
    This must be executed after the auth and scope apps are migrated.
    """
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None


def add_user_groups(apps, schema_editor):
    """Create user groups with permissions."""
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    editor_group, created = Group.objects.get_or_create(name="Editors")
    if created:
        permissions = Permission.objects.filter(
            codename__in=(
                "add_collection",
                "change_collection",
                "add_dip",
                "change_dip",
            )
        )
        for permision in permissions:
            editor_group.permissions.add(permision)
        editor_group.save()
    managers_group, created = Group.objects.get_or_create(name="Managers")
    if created:
        permissions = Permission.objects.filter(
            codename__in=("add_user", "change_user", "delete_user")
        )
        for permission in permissions:
            managers_group.permissions.add(permission)
        managers_group.save()
    # Viewers group is only for display purposes
    # and has no special permissions.
    Group.objects.create(name="Viewers")


def add_settings(apps, schema_editor):
    """Create initial settings to manage DC fields."""
    Setting.objects.create(
        name="enabled_optional_dc_fields",
        value=list(DublinCore.get_optional_fields().keys()),
    )
    Setting.objects.create(name="hide_empty_dc_fields", value=True)


def add_contents(apps, schema_editor):
    home_en = (
        "## Digital Archives Access Interface\n\n"
        "You can search digital files by using the search "
        "bar below or you can browse our collections.  \n"
        "If you need help, please use our FAQ page in the menu above."
    )
    home_fr = (
        "## Interface d'accès aux archives numériques\n\n"
        "Pour effectuer une recherche dans les fichiers, utiliser la barre de "
        "recherche ci-dessous ou naviguer dans nos collections.  \n"
        "Consulter la FAQ si vous avez besoin d'aide."
    )
    data = [
        ("01_home", {"en": home_en, "fr": home_fr}),
        ("02_login", {"en": "", "fr": ""}),
        ("03_faq", {"en": "", "fr": ""}),
    ]
    for key, content in data:
        Content.objects.create(
            key=key, content_en=content["en"], content_fr=content["fr"]
        )


def remove_user_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.all().delete()


def remove_settings(apps, schema_editor):
    Setting.objects.all().delete()


def remove_contents(apps, schema_editor):
    Content.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [("scope", "0001_initial")]

    operations = [
        migrations.RunPython(migrate_permissions, migrations.RunPython.noop),
        migrations.RunPython(add_user_groups, remove_user_groups),
        migrations.RunPython(add_settings, remove_settings),
        migrations.RunPython(add_contents, remove_contents),
    ]
