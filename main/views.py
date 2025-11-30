from django.shortcuts import render, redirect
from dashboard.models import Profile, Outraisons, Inraisons, Inbalance, Outbalance, Activity, Depense, Essance, Node, Connection
from django.http import JsonResponse
from itertools import chain
from datetime import date, timedelta
from django.db.models import Sum
from django.utils import timezone
thismonth=date.today().month
thisyear=date.today().year
# Create your views here.
def main(request):
    profile=Profile.objects.get(pk=1)
    essances=list(Essance.objects.all())
    # litters=essances.aggregate(total=Sum('qty'))['total'] or 0
    distance=float(essances[-1].km)-float(essances[-2].km)
    previouslitter=essances[-2].qty
    print('>> dust', distance, previouslitter)
    lastlitter=essances[-1].qty
    # nextfill=(distance*lastlitter)/previouslitter
    # nextfill=round(nextfill+essances[-1].km, 2)
    tt=round((195*essances[-1].qty)/3.75)
    ageindays=int(profile.age())*365.5
    print('>>', ageindays, profile.age_in_days())
    ageindays=(profile.age_in_days()/21915)*100
    print('>>', ageindays)
    nextfill=tt+essances[-1].km
    
    # print('litters', litters)
    # perkm=litters/distance
    # print('perkm', perkm)
    # print('perkm', 1.48*perkm)

    previousmonth=thismonth-1
    balancein=Inbalance.objects.all().order_by('-date')
    balanceout=Outbalance.objects.all().order_by('-date')
    # totalfixeddepense=Depense.objects.filter(isfix=True).aggregate(total=Sum('amount'))['total'] or 0
    fromlastmonth=0
    if Inbalance.objects.filter(raison_id=14, date__year=thisyear, date__month=thismonth).exists():
        fromlastmonth=Inbalance.objects.filter(raison_id=14, date__year=thisyear, date__month=thismonth)[0].amount
    totalfixeddepense=Outbalance.objects.filter(date__year=thisyear, date__month=thismonth, raison_id=6).aggregate(total=Sum('amount'))['total'] or 0
    totalthismonthin=balancein.exclude(raison_id=14).filter(date__year=thisyear, date__month=thismonth).aggregate(total=Sum('amount'))['total'] or 0
    totalthismonthout=balanceout.filter(date__year=thisyear, date__month=thismonth).aggregate(total=Sum('amount'))['total'] or 0
    thismonthbalance=totalthismonthin-totalthismonthout
    previousmonthin=balancein.filter(date__year=thisyear, date__month=previousmonth).aggregate(total=Sum('amount'))['total'] or 0
    previousmonthout=balanceout.filter(date__year=thisyear, date__month=previousmonth).aggregate(total=Sum('amount'))['total'] or 0
    previousmonthbalance=previousmonthin-previousmonthout
    for i in balanceout.filter(date__year=thisyear, date__month=thismonth-2):
        print('>>', i.amount, i.note)
    print('previous month out', previousmonthbalance)
    netpreviousmonthbalance=previousmonthbalance-totalfixeddepense
    sold=totalthismonthin+previousmonthbalance
    print('>> previousmonthin', previousmonthin, 'previousmonthout', previousmonthout, 'totalfixeddepense', totalfixeddepense, 'netpreviousmonthbalance', netpreviousmonthbalance)
    # netmonthbalance=thismonthbalance-totalfixeddepense
    # get all outbalances with raison id is 4
    essenceout=Outbalance.objects.filter(date__year=thisyear, date__month=thismonth, raison_id=4).aggregate(total=Sum('amount'))['total'] or 0
    # get days passed in this month and divideessenceout by it
    dayspassed=date.today().day
    essenceoutperday=essenceout/dayspassed
    netmonthbalance=totalthismonthin-totalthismonthout+fromlastmonth
    thismonthessence=round(essenceoutperday*30)
    releve = sorted(
        chain(((inb, 'inb') for inb in balancein.filter(date__year=thisyear, date__month=thismonth)), ((outbb, 'outbb') for outbb in balanceout.filter(date__year=thisyear, date__month=thismonth))),
        key=lambda item: item[0].date,
        reverse=True  # Sort in descending order
    )
    totalin=Inbalance.objects.exclude(raison_id=14).aggregate(Sum('amount'))['amount__sum']
    totalout=Outbalance.objects.aggregate(Sum('amount'))['amount__sum']
    print(totalin, totalout, totalin-totalout)
    ctx = {
        'essenceoutperday': essenceoutperday,
        'essenceout': essenceout,
        'nextfill': nextfill,
        'thismonthessence': thismonthessence,
        'previousmonthbalance':previousmonthbalance,
        'title': 'Dashboard',
        'profile': profile,
        'outraisons': Outraisons.objects.all(),
        'inraisons': Inraisons.objects.all(),
        'releve': releve,
        'thismonthin':totalthismonthin,
        'thismonthout':totalthismonthout,
        'totalfixeddepense':totalfixeddepense,
        'netmonthbalance':netmonthbalance,
        'sold':sold,
        'ageindays':ageindays,
        'fromlastmonth':fromlastmonth
    }
    return render(request, 'main/main.html', ctx)




def addtobalance(request):
    profile=Profile.objects.get(pk=1)

    amountin=request.POST.get('amountin')
    raison=request.POST.get('raisonin')
    Inbalance.objects.create(amount=amountin, raison_id=raison, date=timezone.now())
    inraisons=Inraisons.objects.get(pk=raison)
    if inraisons.rest>0:
        inraisons.rest-=float(amountin)
        inraisons.save()
    profile.balance+=float(amountin)
    profile.save()
    print(amountin, raison)
    return redirect('main:main')

def outbalance(request):
    profile=Profile.objects.get(pk=1)
    amountout=request.POST.get('amountout')
    essaanceprice=request.POST.get('essaanceprice')
    # this will be used as note
    kilomtrage=request.POST.get('kilomtrage')
    raison=request.POST.get('raisonout')
    empty=request.POST.get('empty')=='yes'
    print(amountout, raison, essaanceprice)
    if raison=="4":
        qty=round(float(amountout)/float(essaanceprice), 2)
        Essance.objects.create(price=essaanceprice, amount=amountout, km=kilomtrage,  qty=qty, empty=empty)
    Outbalance.objects.create(amount=amountout, raison_id=raison, note=kilomtrage, date=timezone.now())
    profile.balance-=float(amountout)
    profile.save()
    return redirect('main:main')


def activities(request):
    last_activity = Activity.objects.last()
    if last_activity:
        last_activity_date = last_activity.date
        today = timezone.now().date()
        print("ee", (today - last_activity_date).days)
        if (today - last_activity_date).days > 0:
            # Create missing days
            for day in range((today - last_activity_date).days):
                new_activity_date = last_activity_date + timedelta(days=day + 1)
                if new_activity_date <= today:
                    Activity.objects.create(date=new_activity_date, events="missed fajr")
                    print(new_activity_date)
    ctx={
        'title':'Acttivities',
        'activities':Activity.objects.all().order_by('-date')
    }
    return render(request, 'main/activites.html', ctx)

def createactivity(request):
    today = date.today()

    todayact=Activity.objects.filter(date=today)
    if not todayact:
        Activity.objects.create()
    return JsonResponse({
        'done':True
    })

def updateactiv(request):
    id=request.GET.get('id')
    activity=request.GET.get('activity')
    act=Activity.objects.get(pk=id)
    if activity=='mast':
        print('>> mast')
        act.mast+=1
    else:
        setattr(act, activity, not getattr(act, activity))
    act.save()
    return JsonResponse({
        'done':True
    })

def updatewaketime(request):
    id=request.GET.get('id')
    time=request.GET.get('time')
    act=Activity.objects.get(pk=id)
    act.wake=time
    act.save()
    return JsonResponse({
        'success':True
    })

def updatesleeptime(request):
    id=request.GET.get('id')
    time=request.GET.get('time')
    act=Activity.objects.get(pk=id)
    if time:
        act.sleep=time
    else:
        act.sleep=None
    act.save()
    print(">> time", time)
    return JsonResponse({
        'success':True
    })

def addevents(request):
    id=request.GET.get('id')
    events=request.GET.get('events')
    act=Activity.objects.get(pk=id)
    act.events=events
    act.save()
    return JsonResponse({
        'success':True
    })

def getsource(request):
    source=request.GET.get('source')
    balancein=Inbalance.objects.filter(raison=source).order_by('-date')
    total=balancein.aggregate(total=Sum('amount'))
    return JsonResponse({
        'trs':render(request, 'main/source.html', {'releve':balancein}).content.decode('utf-8'),
        'total':total['total'],
        'rest':Inraisons.objects.get(pk=source).rest
    })

def adjustsold(request):
    realsold=request.GET.get('realsold')
    actualsold=request.GET.get('actualsold')
    print('actualsold', actualsold, 'realsold', realsold)
    
    diff=float(actualsold)-float(realsold)
    # just create an outbalance with the diff
    Outbalance.objects.create(amount=diff, raison_id=3, date=timezone.now())

    return JsonResponse({
        'success':True
    })

def quran(request):
    ctx={
        'title':'quran',
    }
    return render(request, 'main/quran.html', ctx)
def tree(request):
    ctx={
        'title':'tree',
    }
    return render(request, 'main/tree.html', ctx)

# def getdata(request):
#     villages = Village.objects.all()
#     #"name": village.name,
#     # Serialize the queryset to JSON
#     data = [{"lat": village.lat, "long": village.long, "ishelped": village.ishelped, "isaccessible": village.isaccissible, "habitat": village.habitat} for village in villages]

#     return JsonResponse(data, safe=False)


