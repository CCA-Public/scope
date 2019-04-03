from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .models import Collection, DIP


@receiver(pre_delete, sender=Collection, dispatch_uid="collection_pre_delete")
@receiver(pre_delete, sender=DIP, dispatch_uid="dip_pre_delete")
def delete_related_dc(instance, **kwargs):
    # When cascade deleting related models the custom delete method from
    # the model classes is not called. The DublinCore models are not deleted
    # in the cascade process because they're related to both Collection and DIP
    # models from their respective tables due to the lack of a base model,
    # where the relation could be made from the DublinCore model to the base
    # model and use on delete cascade for that one to one relation.
    if instance.dc:
        instance.dc.delete()
