from django.contrib import admin
from django.utils.html import format_html

# Register your models here.
from . import models

# ========== LEGACY ADMIN REGISTRATIONS ==========
admin.site.register(models.HostingPlan)
admin.site.register(models.Addon)
admin.site.register(models.Subscription)
admin.site.register(models.Invoice)
admin.site.register(models.SubscriptionHistory)
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
admin.site.register(models.Roadmap)
admin.site.register(models.RoadmapItem)
admin.site.register(models.Moneyexpected)