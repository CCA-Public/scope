from modeltranslation.translator import TranslationOptions
from modeltranslation.translator import register

from .models import Content


@register(Content)
class ContentTranslationOptions(TranslationOptions):
    fields = ("content",)
