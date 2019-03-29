from django.contrib.staticfiles.apps import StaticFilesConfig


class Config(StaticFilesConfig):
    """
    The static files matching the following patterns are needed in the static
    folders to access them in development mode and by `django-compress` but
    they are not needed by `collectstatic`, where the compressed bundles should
    be already created by `django-compress` in the static root folder.
    """
    ignore_patterns = ['*.js', '*.scss', '*.css', '*.map']
