from django.shortcuts import render
from dashboard.models import Roadmap, RoadmapItem
def roadmaps(request):
    roadmaps = Roadmap.objects.all()
    print('rr',roadmaps)
    return render(request, 'main/roadmaps.html', {'roadmaps': roadmaps})