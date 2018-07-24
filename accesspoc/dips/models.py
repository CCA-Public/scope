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
from django.contrib.auth.models import Group, AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

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

    @classmethod
    def get_users(cls, query=None, sort_field='username'):
        """
        Get users based on a query string, querying over 'username',
        'first_name', 'last_name', 'email' and a concatenation of related
        group names separated by ', '. The group name concatenation
        can be used to sort and display in the 'group_names' field and the
        output will be the same as the equally called function from this model.
        The resulting users will be ordered by a given 'sort_field'. Returns
        all users if no query is given and sorts by 'username' by default.
        """
        class GroupsSQ(models.Subquery):
            """Subquery to concatenate group names, requires MySQL or SQLite"""
            template = "(SELECT GROUP_CONCAT(name, ', ') FROM (%(subquery)s))"
            output_field = models.CharField()

        subquery = GroupsSQ(Group.objects.filter(user=models.OuterRef('pk')))
        users = cls.objects.annotate(group_names=subquery).order_by(sort_field)
        if not query:
            return users.all()
        return users.filter(
            models.Q(username__icontains=query) |
            models.Q(first_name__icontains=query) |
            models.Q(last_name__icontains=query) |
            models.Q(email__icontains=query) |
            models.Q(group_names__icontains=query)
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
    identifier = models.CharField(_('identifier'), max_length=50)
    title = models.CharField(_('title'), max_length=200, blank=True)
    creator = models.CharField(_('creator'), max_length=200, blank=True)
    subject = models.CharField(_('subject'), max_length=200, blank=True)
    description = models.TextField(_('description'), blank=True)
    publisher = models.CharField(_('publisher'), max_length=200, blank=True)
    contributor = models.CharField(_('contributor'), max_length=200, blank=True)
    date = models.CharField(_('date'), max_length=21, blank=True)
    type = models.CharField(_('type'), max_length=200, blank=True)
    format = models.TextField(_('format'), blank=True)
    source = models.CharField(_('source'), max_length=200, blank=True)
    language = models.CharField(_('language'), max_length=20, blank=True)
    coverage = models.CharField(_('coverage'), max_length=200, blank=True)
    rights = models.CharField(_('rights'), max_length=200, blank=True)

    def __str__(self):
        return self.identifier

    def get_es_inner_data(self):
        data = {'identifier': self.identifier}
        add_if_not_empty(data, 'title', self.title)
        add_if_not_empty(data, 'date', self.date)
        add_if_not_empty(data, 'description', self.description)

        return data


class Collection(AbstractEsModel):
    link = models.URLField(_('finding aid'), blank=True)
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
    objectszip = models.FileField(_('objects zip file'))
    uploaded = models.DateTimeField(auto_now_add=True)
    collection = models.ForeignKey(
        Collection,
        related_name='dips',
        verbose_name=_('collection'),
    )
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
