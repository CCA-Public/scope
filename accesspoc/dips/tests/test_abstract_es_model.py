from django.test import TestCase

from dips.models import AbstractEsModel


class AemNoMethod(AbstractEsModel):
    # Set to abstract to avoid 'no such table error'
    class Meta:
        abstract = True

    es_doc = None


class AemNoProperty(AbstractEsModel):
    # Set to abstract to avoid 'no such table error'
    class Meta:
        abstract = True

    def get_es_data(self):
        return {}


class AemOkay(AbstractEsModel):
    # Set to abstract to avoid 'no such table error'
    class Meta:
        abstract = True

    es_doc = None

    def get_es_data(self):
        return {}


class AbstratEsModelTests(TestCase):
    def test_descendants_creation(self):
        self.assertRaises(TypeError, AemNoMethod)
        self.assertRaises(TypeError, AemNoProperty)
        model = AemOkay()
        self.assertIsNone(model.es_doc)
        self.assertEqual(model.get_es_data(), {})
