from elasticsearch_dsl import analyzer, DocType, InnerDoc, Keyword, Long, \
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
    import_task_id = Keyword()
    import_status = Keyword()

    class Meta:
        index = 'accesspoc_dips'
        dynamic = MetaField('strict')


class DigitalFileDoc(DocType):
    uuid = Text()
    # To split file extensions, the pattern tokenizer is used,
    # which defaults to the "\W+" pattern.
    filepath = Text(
        fields={'raw': Keyword()},
        analyzer=analyzer(
            'filepath',
            tokenizer='pattern',
            filter=['lowercase'],
        ),
    )
    fileformat = Text(fields={'raw': Keyword()})
    size_bytes = Long()
    # TODO: Use date time field for datemodified, see #54
    datemodified = Text(fields={'raw': Keyword()})
    dip = Object(properties={
        'id': Integer(),
        'identifier': Text(),
        'import_status': Keyword(),
    })

    class Meta:
        index = 'accesspoc_digital_files'
        dynamic = MetaField('strict')
