from django.test import TestCase
from django.utils.translation import gettext_lazy as _

from dips.models import DublinCore, Setting


class DublinCoreSettingsTests(TestCase):
    def test_dc_optional_fields(self):
        optional_fields = {
            "title": _("title"),
            "creator": _("creator"),
            "subject": _("subject"),
            "description": _("description"),
            "publisher": _("publisher"),
            "contributor": _("contributor"),
            "date": _("date"),
            "type": _("type"),
            "format": _("format"),
            "source": _("source"),
            "language": _("language"),
            "coverage": _("coverage"),
            "rights": _("rights"),
        }
        self.assertEqual(DublinCore.get_optional_fields(), optional_fields)

    def test_dc_settings_default_values(self):
        enabled_fields = [
            "identifier",
            "title",
            "creator",
            "subject",
            "description",
            "publisher",
            "contributor",
            "date",
            "type",
            "format",
            "source",
            "language",
            "coverage",
            "rights",
        ]
        self.assertEqual(DublinCore.enabled_fields(), enabled_fields)
        self.assertTrue(DublinCore.hide_empty_fields())

    def test_dc_settings_change(self):
        enabled_optional_fields = [
            "title",
            "creator",
            "subject",
            "description",
            "contributor",
            "date",
            "type",
            "format",
        ]
        Setting.objects.filter(name="enabled_optional_dc_fields").update(
            value=enabled_optional_fields
        )
        self.assertEqual(
            DublinCore.enabled_fields(),
            DublinCore.REQUIRED_FIELDS + enabled_optional_fields,
        )
        Setting.objects.filter(name="hide_empty_dc_fields").update(value=False)
        self.assertFalse(DublinCore.hide_empty_fields())

    def test_dc_settings_errors(self):
        # Wrong `enabled_optional_dc_fields` value
        enabled = Setting.objects.get(name="enabled_optional_dc_fields")
        enabled.value = "wrong value type"
        enabled.save()
        self.assertRaises(TypeError, DublinCore.enabled_fields)
        # Missing settings
        enabled.delete()
        hide_empty = Setting.objects.get(name="hide_empty_dc_fields")
        hide_empty.delete()
        self.assertRaises(Setting.DoesNotExist, DublinCore.enabled_fields)
        self.assertRaises(Setting.DoesNotExist, DublinCore.hide_empty_fields)
