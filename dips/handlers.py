from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .models import Collection, DIP, DigitalFile


@receiver(post_save, sender=Collection, dispatch_uid='collection_post_save')
@receiver(post_save, sender=DIP, dispatch_uid='dip_post_save')
@receiver(post_save, sender=DigitalFile, dispatch_uid='digital_file_post_save')
def update_search_doc(instance, **kwargs):
    # Disable when loading fixture data
    if kwargs['raw']:
        return
    # Use refresh to reflect the changes in the index in the same request
    instance.to_es_doc().save(refresh=True)

    # TODO: Partial update of related resources:
    # - When saving Collection, update collection.identifier of related DIPs
    # - When saving DIP, update dip.identifier of related DigitalFiles


@receiver(pre_delete, sender=Collection, dispatch_uid='collection_pre_delete')
@receiver(pre_delete, sender=DIP, dispatch_uid='dip_pre_delete')
@receiver(pre_delete, sender=DigitalFile, dispatch_uid='digital_file_pre_delete')
def delete_search_doc(instance, **kwargs):
    # Delete DublinCore one to one relation
    if type(instance) in [Collection, DIP] and instance.dc:
        instance.dc.delete()
    instance.delete_es_doc()
