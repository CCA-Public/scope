from elasticsearch_dsl import DocType, InnerDoc, Keyword, Long, \
    MetaField, Object, Text, Integer


class DublinCoreDoc(InnerDoc):
    identifier = Text(fields={'raw': Keyword()})
    title = Text(fields={'raw': Keyword()})
    date = Text()
    description = Text()


class CollectionDoc(DocType):
    dc = Object(DublinCoreDoc)

    class Meta:
        index = 'accesspoc_collections'
        dynamic = MetaField('strict')


class DIPDoc(DocType):
    dc = Object(DublinCoreDoc)
    collection = Object(properties={
        'id': Integer(),
        'identifier': Text(),
    })

    class Meta:
        index = 'accesspoc_dips'
        dynamic = MetaField('strict')


class DigitalFileDoc(DocType):
    uuid = Text()
    filepath = Text(fields={'raw': Keyword()})
    fileformat = Text(fields={'raw': Keyword()})
    size_bytes = Long()
    # TODO: Use date time field for datemodified, see #54
    datemodified = Text(fields={'raw': Keyword()})
    dip = Object(properties={
        'id': Integer(),
        'identifier': Text(),
    })

    class Meta:
        index = 'accesspoc_digital_files'
        dynamic = MetaField('strict')
