from elasticsearch_dsl.connections import connections


def delete_document(index, doc_type, id):
    """
    Delete ES documents directly with the low level client to avoid building
    the documents. Use refresh to reflect the changes in the same request.
    """
    es = connections.get_connection()
    es.delete(index=index, doc_type=doc_type, id=id, refresh=True)


def add_query_to_search(search, query, fields):
    """
    Check if a query is not whitespace and add a `simple_query_string`
    to the search over a given list of fields.
    """
    if query.strip():
        search = search.query(
            'simple_query_string',
            query=query,
            default_operator='and',
            fields=fields,
        )

    return search


def add_digital_file_aggs(search, collections=True):
    """Add aggregations to DigitalFile search.

    Set aggregations size to 10000 to get "all" buckets. Ideally, the aggs.
    should allow pagination and filtering. That will require to:
    - Use `composite` aggregations with `after_key`.
    - Add JSON endpoint to get subsequent pages and filter query.
    - Add Javascript/Typescript code to request new pages and query.
    """
    search.aggs.bucket('formats', 'terms', field='fileformat.raw', size=10000)
    # The collections agg. is made directly over the title to avoid hitting
    # the ORM to get the title with the id or to use a composite agg. with
    # multiple sources. The biggest downside is that the titles are used as
    # value in the request parameters, which can create long URLs as multiple
    # selection is allowed. This agg. is optional and not added in DIP pages.
    if collections:
        search.aggs.bucket(
            'collections', 'terms', field='collection.title.raw', size=10000)

    return search


def add_digital_file_filters(search, filters):
    """
    Forms boolean query with must clauses for digital file filters dict.
    Filters dict. must be already validated:
    - formats: list of strings.
    - collections: list of strings.
    - start_date: string with `yyyy-MM-dd` date format.
    - end_date: string with `yyyy-MM-dd` date format.
    """
    if 'formats' in filters and filters['formats']:
        search = search.query('terms', **{'fileformat.raw': filters['formats']})
    if 'collections' in filters and filters['collections']:
        search = search.query(
            'terms', **{'collection.title.raw': filters['collections']})
    if 'start_date' in filters and filters['start_date']:
        search = search.query(
            'range', **{'datemodified': {
                'gte': filters['start_date'],
                'format': 'yyyy-MM-dd'
            }})
    if 'end_date' in filters and filters['end_date']:
        search = search.query(
            'range', **{'datemodified': {
                'lte': filters['end_date'],
                'format': 'yyyy-MM-dd'
            }})

    return search
