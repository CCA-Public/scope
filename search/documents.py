from elasticsearch_dsl import Date
from elasticsearch_dsl import DocType
from elasticsearch_dsl import InnerDoc
from elasticsearch_dsl import Integer
from elasticsearch_dsl import Keyword
from elasticsearch_dsl import Long
from elasticsearch_dsl import MetaField
from elasticsearch_dsl import Object
from elasticsearch_dsl import Text
from elasticsearch_dsl import analyzer


class BaseDoc(DocType):
    class Meta:
        all = MetaField(enabled=False)
        dynamic = MetaField("strict")


class DublinCoreDoc(InnerDoc):
    identifier = Text(fields={"raw": Keyword()})
    title = Text(fields={"raw": Keyword()})
    date = Text()
    description = Text()


class CollectionDoc(BaseDoc):
    dc = Object(DublinCoreDoc)

    class Index:
        name = "scope_collections"


class DIPDoc(BaseDoc):
    dc = Object(DublinCoreDoc)
    collection = Object(properties={"id": Integer()})
    import_status = Keyword()

    class Index:
        name = "scope_dips"


class DigitalFileDoc(BaseDoc):
    uuid = Text()
    # To split file extensions, the pattern tokenizer is used,
    # which defaults to the "\W+" pattern.
    filepath = Text(
        fields={"raw": Keyword()},
        analyzer=analyzer("filepath", tokenizer="pattern", filter=["lowercase"]),
    )
    fileformat = Text(fields={"raw": Keyword()})
    size_bytes = Long()
    # Always saved as UTC, not just the default.
    datemodified = Date(default_timezone="UTC")
    dip = Object(
        properties={
            "id": Integer(),
            "identifier": Text(),
            "title": Text(),
            "import_status": Keyword(),
        }
    )
    collection = Object(
        properties={
            "id": Integer(),
            "identifier": Text(),
            "title": Text(fields={"raw": Keyword()}),
        }
    )

    class Index:
        name = "scope_digital_files"
