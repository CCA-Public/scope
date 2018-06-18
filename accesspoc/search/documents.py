from elasticsearch_dsl import DocType, Keyword, Long, MetaField, Object, Text


class CollectionDoc(DocType):
    identifier = Text(fields={'raw': Keyword()})
    title = Text()
    date = Text()
    description = Text()

    class Meta:
        index = 'accesspoc_collections'
        dynamic = MetaField('strict')


class DIPDoc(DocType):
    identifier = Text(fields={'raw': Keyword()})
    title = Text()
    date = Text()
    description = Text()
    ispartof = Object(properties={
        'identifier': Text(),
        'title': Text(),
    })

    class Meta:
        index = 'accesspoc_dips'
        dynamic = MetaField('strict')


class DigitalFileDoc(DocType):
    uuid = Text()
    filepath = Text(fields={'raw': Keyword()})
    fileformat = Text()
    size_bytes = Long()
    datemodified = Text()
    dip = Object(properties={
        'identifier': Text(),
        'title': Text(),
    })

    class Meta:
        index = 'accesspoc_digital_files'
        dynamic = MetaField('strict')
