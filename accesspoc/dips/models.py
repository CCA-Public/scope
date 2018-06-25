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
from .helpers import add_if_not_empty


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


class DublinCore(models.Model):
    identifier = models.CharField(max_length=50)
    title = models.CharField(max_length=200, blank=True)
    creator = models.CharField(max_length=200, blank=True)
    subject = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    publisher = models.CharField(max_length=200, blank=True)
    contributor = models.CharField(max_length=200, blank=True)
    date = models.CharField(max_length=21, blank=True)
    type = models.CharField(max_length=200, blank=True)
    format = models.TextField(blank=True)
    source = models.CharField(max_length=200, blank=True)
    language = models.CharField(max_length=20, blank=True)
    coverage = models.CharField(max_length=200, blank=True)
    rights = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.identifier

    def get_es_inner_data(self):
        data = {'identifier': self.identifier}
        add_if_not_empty(data, 'title', self.title)
        add_if_not_empty(data, 'date', self.date)
        add_if_not_empty(data, 'description', self.description)

        return data


class Collection(AbstractEsModel):
    link = models.URLField(blank=True)
    dc = models.OneToOneField(DublinCore, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return str(self.dc) or str(self.pk)

    es_doc = CollectionDoc

    def get_es_data(self):
        data = {
            '_id': self.pk,
        }

        if self.dc:
            data['dc'] = self.dc.get_es_inner_data()

        return data


class DIP(AbstractEsModel):
    objectszip = models.FileField()
    uploaded = models.DateTimeField(auto_now_add=True)
    collection = models.ForeignKey(Collection, related_name='dips')
    dc = models.OneToOneField(DublinCore, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return str(self.dc) or str(self.pk)

    es_doc = DIPDoc

    def get_es_data(self):
        data = {
            '_id': self.pk,
        }

        if self.dc:
            data['dc'] = self.dc.get_es_inner_data()

        if self.collection.dc:
            data['collection'] = {
                'id': self.collection.pk,
                'identifier': self.collection.dc.identifier,
            }

        return data


class DigitalFile(AbstractEsModel):
    uuid = models.CharField(max_length=36, primary_key=True)
    filepath = models.TextField()
    fileformat = models.CharField(max_length=200)
    formatversion = models.CharField(max_length=200, blank=True, null=True)
    size_bytes = models.BigIntegerField()
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
        data = {
            '_id': self.pk,
            'uuid': self.uuid,
            'filepath': self.filepath,
            'fileformat': self.fileformat,
            'size_bytes': self.size_bytes,
        }
        add_if_not_empty(data, 'datemodified', self.datemodified)

        if self.dip.dc:
            data['dip'] = {
                'id': self.dip.pk,
                'identifier': self.dip.dc.identifier,
            }

        return data


class PREMISEvent(models.Model):
    uuid = models.CharField(max_length=36, primary_key=True)
    eventtype = models.CharField(max_length=200, blank=True)
    datetime = models.CharField(max_length=50, blank=True)
    detail = models.TextField(blank=True, null=True)
    outcome = models.TextField(blank=True, null=True)
    detailnote = models.TextField(blank=True, null=True)
    digitalfile = models.ForeignKey(DigitalFile, related_name='premis_events')

    def __str__(self):
        return self.uuid
