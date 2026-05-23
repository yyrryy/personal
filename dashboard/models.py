from django.db import models
from django.utils import timezone

from dateutil.relativedelta import relativedelta
class Supervisor(models.Model):
    name=models.CharField(max_length=500)

# Create your models here.
class Village(models.Model):
    lat=models.CharField(max_length=500)
    long=models.CharField(max_length=500)
    ishelped=models.BooleanField(default=False)
    isaccissible=models.BooleanField(default=False)
    habitat=models.FloatField()
    

class Essance(models.Model):
    price=models.FloatField()
    # this will record the kilmotrage
    km=models.FloatField()
    # amount of essance en dh
    amount=models.FloatField()
    qty=models.FloatField()
    empty=models.BooleanField(default=False)
    

class Profile(models.Model):
    balance=models.FloatField()
    birthday=models.DateTimeField()
    name=models.CharField(default=None, max_length=500, null=True, blank=True)
    idnumber=models.CharField(default=None, max_length=500, null=True, blank=True)
    idimage1=models.CharField(default=None, max_length=500, null=True, blank=True)
    idimage2=models.CharField(default=None, max_length=500, null=True, blank=True)
    def age(self):
        now = timezone.now()
        delta = relativedelta(now, self.birthday)
        age = delta.years
        return age
    def age_in_days(self):
        now = timezone.now()
        delta = now - self.birthday
        return delta.days
# raisons of out of balance
class Outraisons(models.Model):
    raison=models.TextField()
    def __str__(self) -> str:
        return self.raison

# raisons of in of balance
class Inraisons(models.Model):
    raison=models.TextField()
    #ch!7al b9a 3ndo
    rest=models.FloatField(default=0.0)
    #ignored means that I will not count it in the total balance(ref 544R34RR), but I want to keep it for record
    ignored=models.BooleanField(default=False)
    def __str__(self) -> str:
        return self.raison

class Outbalance(models.Model):
    amount=models.FloatField()
    date=models.DateTimeField()
    raison=models.ForeignKey(Outraisons, on_delete=models.CASCADE)
    note=models.TextField(default=None, null=True, blank=True)
    def __str__(self) -> str:
        return str(self.date)
class Inbalance(models.Model):
    amount=models.FloatField()
    date=models.DateTimeField()
    raison=models.ForeignKey(Inraisons, on_delete=models.CASCADE)
    note=models.TextField(default=None, null=True, blank=True)
    
        
class Activity(models.Model):
    date=models.DateField(default=timezone.now, null=True)
    events=models.TextField()
    prayer=models.BooleanField(default=False)
    fajr=models.BooleanField(default=False)
    duhr=models.BooleanField(default=False)
    asr=models.BooleanField(default=False)
    maghrib=models.BooleanField(default=False)
    isha=models.BooleanField(default=False)
    shower=models.BooleanField(default=False)
    football=models.BooleanField(default=False)
    run=models.BooleanField(default=False)
    coding=models.BooleanField(default=False)
    quran=models.BooleanField(default=False)
    working=models.BooleanField(default=False)
    sick=models.BooleanField(default=False)
    pushups=models.BooleanField(default=False)
    freelancing=models.BooleanField(default=False)
    mast=models.IntegerField(default=0)
    sleep=models.TimeField(default=None, null=True, blank=True)
    wake=models.TimeField(default=None, null=True, blank=True)
    face=models.ImageField(upload_to='faces/', default=None, null=True, blank=True)
    abs=models.ImageField(upload_to='abss/', default=None, null=True, blank=True)
    def __str__(self) -> str:
        return str(self.date)
    
class Depense(models.Model):
    name=models.CharField(max_length=500)
    amount=models.FloatField()
    isfix=models.BooleanField(default=False)
    date=models.DateTimeField(auto_now=True)
    def __str__(self) -> str:
        return str(self.date)
    
class Node(models.Model):
    title = models.CharField(max_length=200)
    type = models.CharField(max_length=200, default='', null=True, blank=True)  # e.g., "task", "idea"
    imglink = models.CharField(max_length=200, default=None, null=True, blank=True)  # e.g., "task", "idea"
    videolink = models.CharField(max_length=200, default=None, null=True, blank=True)  # e.g., "task", "idea"
    ytlink = models.CharField(max_length=200, default=None, null=True, blank=True)  # e.g., "task", "idea"
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="node_images/", blank=True, null=True)
    x = models.FloatField(default=100)  # position on board
    y = models.FloatField(default=100)
    def __str__(self):
        return self.title


class Connection(models.Model):
    source = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="connections_from")
    target = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="connections_to")
    label = models.CharField(max_length=200, blank=True)
    color = models.CharField(max_length=20, default="#000")  # optional color

    def __str__(self):
        return f"{self.source} -> {self.target} ({self.label})"
class Item(models.Model):
    name = models.CharField(max_length=200)
    image=models.ImageField(upload_to="item_images/", blank=True, null=True)
    def __str__(self):
        return self.name
class Roadmap(models.Model):
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    estimated_completion_date = models.DateTimeField(null=True, blank=True)
    def __str__(self):
        return self.title

class RoadmapItem(models.Model):
    # admin.site.register(models.Profile)
    roadmap = models.ForeignKey(Roadmap, on_delete=models.CASCADE, related_name="items")

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    category = models.CharField(max_length=200, blank=True)  
    # No fixed choices → flexible for any roadmap type

    order = models.IntegerField(default=0)  
    # You can use order instead of day_start/day_end to support ALL kinds of roadmaps

    completed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.title} - {'Done' if self.completed else 'Pending'}"
    
class Moneyexpected(models.Model):
    amount=models.FloatField()
    raison=models.ForeignKey(Inraisons, on_delete=models.CASCADE)
    # wether I get it or not
    paid=models.BooleanField(default=False)
    note=models.TextField(default=None, null=True, blank=True)
    def __str__(self) -> str:
        return f"{self.amount} expected from {self.raison.raison}"
