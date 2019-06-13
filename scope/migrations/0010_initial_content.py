from django.db import migrations

from scope.models import Content


def add(apps, schema_editor):
    home_en = (
        "## Digital Archives Access Interface\n\n"
        "You can search digital files by using the search "
        "bar below or you can browse our collections.  \n"
        "If you need help, please use our FAQ page in the menu above."
    )
    home_fr = (
        "## Interface d'accès aux archives numériques\n\n"
        "Pour effectuer une recherche dans les fichiers, utiliser la barre de "
        "recherche ci-dessous ou naviguer dans nos collections.  \n"
        "Consulter la FAQ si vous avez besoin d'aide."
    )
    data = [
        ("01_home", {"en": home_en, "fr": home_fr}),
        ("02_login", {"en": "", "fr": ""}),
        ("03_faq", {"en": "", "fr": ""}),
    ]
    for key, content in data:
        Content.objects.create(
            key=key, content_en=content["en"], content_fr=content["fr"]
        )


def remove(apps, schema_editor):
    Content.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [("scope", "0009_content")]

    operations = [migrations.RunPython(add, remove)]
