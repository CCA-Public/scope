from django.apps import AppConfig


class ScopeConfig(AppConfig):
    name = "scope"

    def ready(self):
        import scope.handlers  # noqa F401
