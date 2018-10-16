from elasticsearch_dsl.connections import connections


def delete_document(index, doc_type, id):
    """
    Delete ES documents directly with the low level client to avoid building
    the documents. Use refresh to reflect the changes in the same request.
    """
    es = connections.get_connection()
    es.delete(index=index, doc_type=doc_type, id=id, refresh=True)
