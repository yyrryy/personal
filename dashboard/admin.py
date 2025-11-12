from django.contrib import admin

# Register your models here.
from . import models

admin.site.register(models.Outraisons)
admin.site.register(models.Inraisons)
admin.site.register(models.Profile)
admin.site.register(models.Inbalance)
admin.site.register(models.Outbalance)
admin.site.register(models.Activity)
admin.site.register(models.Depense)
admin.site.register(models.Essance)
admin.site.register(models.Connection)
admin.site.register(models.Node)
# admin.site.register(models.Profile)