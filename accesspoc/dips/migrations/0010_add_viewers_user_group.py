# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def add_viewers_user_group(apps, schema_editor):
    """
    Create 'Viewers' user group with no special permissions,
    only for display purposes.
    """
    Group = apps.get_model('auth', 'Group')
    Group.objects.create(name='Viewers')


class Migration(migrations.Migration):

    dependencies = [
        ('dips', '0009_auto_20180721_1926'),
    ]

    operations = [
        migrations.RunPython(add_viewers_user_group),
    ]
