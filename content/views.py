from .models import Activity, CarouselImage
from django.shortcuts import render

def home(request):
    hero = CarouselImage.objects.first()
    print("HERO =", hero)

    activities = Activity.objects.all()
    return render(request, "home.html", {
        "hero": hero,
        "activities": activities,
    })
