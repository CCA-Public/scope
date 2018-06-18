from django.apps import AppConfig
from django.conf import settings

from elasticsearch_dsl.connections import connections


class SearchConfig(AppConfig):
    name = 'search'

    def ready(self):
        """
        Create Elasticsearch connection on app ready to do it only once. It will
        create a persistent connection on the first request that will be used
        globally. The client is thread safe and can be used in a multi threaded
        environment allowing by default to open up to 10 connections per node
        with a 10 seconds timeout. To configure the client to use SSL or HTTP
        auth, RFC-1738 formatted URLs can be defined the hosts.
        E.g.:'https://user:secret@host:443/'.
        """
        connections.create_connection(
            hosts=settings.ES_HOSTS,
            timeout=settings.ES_TIMEOUT,
            maxsize=settings.ES_POOL_SIZE,
        )
