from django.contrib import admin
from .models import Collection, DIP, DigitalFile, PREMISEvent

admin.site.register(Collection)
admin.site.register(DIP)
admin.site.register(DigitalFile)
admin.site.register(PREMISEvent)
