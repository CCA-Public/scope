"""
Model classes declaration for dips app:

To connect Django models to elasticsearch-dsl documents declared in
search.documents, an AbstractEsModel has been created with the ABC and
Django model metas. The models extending AbstractEsModel must implement
an `es_doc` attribute with the related DocType class from search.documents
and a `get_es_data` method to transform to a dictionary representation of
the ES document.
"""
from abc import ABCMeta, abstractmethod
from django.db import models
from django.contrib.auth.models import AbstractUser

from search.documents import CollectionDoc, DIPDoc, DigitalFileDoc
from search.functions import delete_document


class User(AbstractUser):
    def group_names(self):
        return ', '.join(list(self.groups.values_list('name', flat=True)))

    def is_editor(self):
        return (
            self.is_superuser or
            self.groups.filter(name='Editors').exists()
        )

    def is_manager(self):
        return (
            self.is_superuser or
            self.groups.filter(name='Managers').exists()
        )


class AbstractModelMeta(ABCMeta, type(models.Model)):
    """Meta merged from ABC and Django models to use in AbstractEsModel."""


class AbstractEsModel(models.Model, metaclass=AbstractModelMeta):
    """Abstract base model for models related to ES DocTypes."""
    class Meta:
        abstract = True

    # Declaration in abstract class must be as property to allow decorators.
    # Implementation in descendats must be as attribute to avoid setter/getter.
    @property
    @abstractmethod
    def es_doc(self):
        """Related ES DocType from search.documents."""

    @abstractmethod
    def get_es_data(self):
        """Model transformation to ES metadata dict."""

    def to_es_doc(self):
        """Model transformation to related DocType."""
        data = self.get_es_data()
        return self.es_doc(meta={'id': data.pop('_id')}, **data)

    def delete_es_doc(self):
        """Call to remove related document from the ES index."""
        delete_document(
            index=self.es_doc._doc_type.index,
            doc_type=self.es_doc._doc_type.name,
            id=self.pk,
        )


class Collection(AbstractEsModel):
    identifier = models.CharField(max_length=50, primary_key=True)
    title = models.CharField(max_length=200, blank=True)
    creator = models.CharField(max_length=200, blank=True)
    subject = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True, null=True)
    publisher = models.CharField(max_length=200, blank=True)
    contributor = models.CharField(max_length=200, blank=True)
    date = models.CharField(max_length=21, blank=True)
    dctype = models.CharField(max_length=200, blank=True)
    dcformat = models.TextField(blank=True, null=True)
    source = models.CharField(max_length=200, blank=True)
    language = models.CharField(max_length=20, blank=True)
    coverage = models.CharField(max_length=200, blank=True)
    rights = models.CharField(max_length=200, blank=True)
    link = models.URLField(blank=True)

    def __str__(self):
        return self.identifier

    es_doc = CollectionDoc

    def get_es_data(self):
        return {
            '_id': self.pk,
            'identifier': self.identifier,
            'title': self.title,
            'date': self.date,
            'description': self.description,
        }


class DIP(AbstractEsModel):
    identifier = models.CharField(max_length=50, primary_key=True)
    ispartof = models.ForeignKey(Collection, related_name='dips')
    title = models.CharField(max_length=200, blank=True)
    creator = models.CharField(max_length=200, blank=True)
    subject = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True, null=True)
    publisher = models.CharField(max_length=200, blank=True)
    contributor = models.CharField(max_length=200, blank=True)
    date = models.CharField(max_length=21, blank=True)
    dctype = models.CharField(max_length=200, blank=True)
    dcformat = models.TextField(blank=True, null=True)
    source = models.CharField(max_length=200, blank=True)
    language = models.CharField(max_length=20, blank=True)
    coverage = models.CharField(max_length=200, blank=True)
    rights = models.CharField(max_length=200, blank=True)
    objectszip = models.FileField()
    uploaded = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.identifier

    es_doc = DIPDoc

    def get_es_data(self):
        return {
            '_id': self.pk,
            'identifier': self.identifier,
            'title': self.title,
            'date': self.date,
            'description': self.description,
            'ispartof': {
                'identifier': self.ispartof.identifier,
                'title': self.ispartof.title,
            }
        }


class DigitalFile(AbstractEsModel):
    uuid = models.CharField(max_length=32, primary_key=True)
    filepath = models.TextField()
    fileformat = models.CharField(max_length=200)
    formatversion = models.CharField(max_length=200, blank=True, null=True)
    size_bytes = models.IntegerField()
    size_human = models.CharField(max_length=10, blank=True)
    datemodified = models.CharField(max_length=30, blank=True)
    puid = models.CharField(max_length=11, blank=True)
    amdsec = models.CharField(max_length=12)
    hashtype = models.CharField(max_length=7)
    hashvalue = models.CharField(max_length=128)
    dip = models.ForeignKey(DIP, related_name='digital_files')

    def __str__(self):
        return self.uuid

    es_doc = DigitalFileDoc

    def get_es_data(self):
        return {
            '_id': self.pk,
            'uuid': self.uuid,
            'filepath': self.filepath,
            'fileformat': self.fileformat,
            'size_bytes': self.size_bytes,
            'datemodified': self.datemodified,
            'dip': {
                'identifier': self.dip.identifier,
                'title': self.dip.title,
            }
        }


class PREMISEvent(models.Model):
    uuid = models.CharField(max_length=32, primary_key=True)
    eventtype = models.CharField(max_length=200, blank=True)
    datetime = models.CharField(max_length=50, blank=True)
    detail = models.TextField(blank=True, null=True)
    outcome = models.TextField(blank=True, null=True)
    detailnote = models.TextField(blank=True, null=True)
    digitalfile = models.ForeignKey(DigitalFile, related_name='premis_events')

    def __str__(self):
        return self.uuid
