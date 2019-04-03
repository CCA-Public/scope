from django.apps import AppConfig


class DipsConfig(AppConfig):
    name = "dips"

    def ready(self):
        import dips.handlers  # noqa F401
