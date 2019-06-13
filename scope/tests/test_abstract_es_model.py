from django.test import TestCase

from scope.models import AbstractEsModel


class AemNoMethod(AbstractEsModel):
    """Model missing one or more abstract methods."""

    # Set to abstract to avoid 'no such table error'
    class Meta:
        abstract = True

    es_doc = None

    def get_es_data(self):
        pass


class AemNoProperty(AbstractEsModel):
    """Model missing one or more abstract properties."""

    # Set to abstract to avoid 'no such table error'
    class Meta:
        abstract = True

    def get_es_data(self):
        pass

    def requires_es_descendants_update(self):
        pass

    def requires_es_descendants_delete(self):
        pass


class AemOkay(AbstractEsModel):
    """Model with all the abstract models and properties."""

    # Set to abstract to avoid 'no such table error'
    class Meta:
        abstract = True

    es_doc = None

    def get_es_data(self):
        pass

    def requires_es_descendants_update(self):
        pass

    def requires_es_descendants_delete(self):
        pass


class AbstratEsModelTests(TestCase):
    def test_descendants_creation(self):
        # Missing abstract method or property should raise
        self.assertRaises(TypeError, AemNoMethod)
        self.assertRaises(TypeError, AemNoProperty)
        # All required abstract methods and properties should not raise
        AemOkay()
