from django.shortcuts import render
from django.core.cache import cache
from django.http import (HttpResponse,JsonResponse)
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from multiprocessing import Pool
from pyphonetics import Soundex
from algoritmos import settings
import urllib.request
import datetime
import functools
import pypyodbc
import jaro
import json
import csv
import os

soundex = Soundex()
maxvalue = 85


@require_http_methods(["GET"])
def index(request):
    return HttpResponse(render(request, 'index.html'))


@csrf_exempt 
def guarda(request):
    if request.method == "POST":
        try:
            connStr = (r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ="+os.path.join(settings.BASE_DIR, 'db.accdb')+";")
            conn = pypyodbc.connect(connStr)
            cur = conn.cursor()
            cur.execute("insert into DatosGuardados(idclinete, observacion) values ("+request.POST['id']+",'"+request.POST['comentario'].replace("'",'')+"')")
            cur.commit()
            cur.close()
            conn.close()
            return HttpResponse('{"response":"true"}',content_type='application/json')
        except:
            pass
    return HttpResponse('{"response":"fasle"}',content_type='application/json')



@require_http_methods(["GET"])
def initpage(request):
    downloadfile()
    connStr = (r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ="+os.path.join(settings.BASE_DIR, 'db.accdb')+";")
    conn = pypyodbc.connect(connStr)
    cur = conn.cursor()
    query = "SELECT id, Name_EN FROM clientes"
    cur.execute(query)
    rs = []
    #print(alt)
    while True:
        row = cur.fetchone()
        if row is None:
            break
        rs.append(row)
    return HttpResponse(render(request, 'table.html',{'datsdb':json.dumps(rs)}))


@csrf_exempt 
def getresult(request):
    if request.method == "POST":
        rs = []
        nombre = request.POST['nombre']
        response =  comparewithcsv(nombre.upper())
        totalrs = len(response)
        if totalrs > 0:
            rs.append({'datos':response,'total':totalrs,'nombre':nombre})
        return JsonResponse(rs,safe=False)


def comparewithcsv(name):
    originalsoundx = soundex.phonetics(name)
    results = []
    sdn=[]
    alias = 'a.k.a. '
    with open('sdn.csv', newline='') as csvfile:
        spamreader = csv.reader(csvfile)
        for row in spamreader:
            try:
                splitaka= row[11].find(alias)
                if splitaka > 0:
                    akdata = row[11].split(';')
                    for i in akdata: 
                        if i.find(alias) > 0:
                            akaname     = i.split("'")[1].upper()
                            presaundex  = soundex.phonetics(akaname[1])
                            rsjaro      = jaro.jaro_winkler_metric(name,akaname[1])*100
                            rssound     = jaro.jaro_winkler_metric(originalsoundx,presaundex)*100
                            if rsjaro >= maxvalue and rssound >= maxvalue:
                                results.append([row[0],row[1],akaname,row[3],rsjaro, rssound])
                            rsjarowords = comparationbyword(name, akaname)
                            if rsjarowords[1] >= maxvalue and rsjarowords[0] >= maxvalue:
                                results.append({'id':row[0],'nombre':row[1],'alias':akaname,'tipo':row[3],'jaro':rsjarowords[0], 'sound':rsjarowords[1]})
                namecsv     = row[1].upper()
                presaundex  = soundex.phonetics(namecsv)
                rsjaro      = jaro.jaro_winkler_metric(name,namecsv)*100
                rssound     = jaro.jaro_winkler_metric(originalsoundx,presaundex)*100
                
                if rsjaro >= maxvalue and rssound >= maxvalue:
                    results.append({'id':row[0],'nombre':row[1],'alias':'','tipo':row[3],'jaro':rsjaro, 'sound':rssound})
                
                rsjarowords = comparationbyword(name, namecsv)
                if rsjarowords[1] >= maxvalue and rsjarowords[0] >= maxvalue:
                    results.append({'id':row[0],'nombre':row[1],'alias':'','tipo':row[3],'jaro':rsjarowords[0], 'sound':rsjarowords[1]})  
            except:
                pass
    results = sorted(results, key=lambda x: x['jaro'], reverse=True)
    return results


def comparationbyword(name,compare):
    #soundex = Soundex()
    lista1 = list(dict.fromkeys(name.replace(',','').split(' ')))
    lista2 = list(dict.fromkeys(compare.replace(',','').split(' ')))

    arrayj= []
    cuentaj = 0
    cuentas = 0
    indexj = 0
    indexs = 0

    for a in lista1: 
        for b in lista2: 
            datojaro = jaro.jaro_winkler_metric(a,b)*100
            datosound = jaro.jaro_winkler_metric(soundex.phonetics(a),soundex.phonetics(b))*100
            if datojaro >= maxvalue:
                indexj +=1
                cuentaj += datojaro
            if datosound >= maxvalue:
                indexs +=1
                cuentas += datosound
    cuentaj = cuentaj / max([len(lista1),indexj])
    cuentas = cuentas / max([len(lista1),indexs])
    return [cuentaj,cuentas]


def comparationcompletename():
    presaundex  = soundex.phonetics(akaname[1])
    rsjaro      = jaro.jaro_winkler_metric(name,akaname[1])*100
    rssound     = jaro.jaro_winkler_metric(originalsoundx,presaundex)*100
    return [rsjaro,rssound]



def downloadfile():
    try:
        sdn=[]
        alt=[]
        urlsdn = 'https://www.treasury.gov/ofac/downloads/sdn.csv'
        urlalt = 'https://www.treasury.gov/ofac/downloads/alt.csv'
        urllib.request.urlretrieve(urlsdn, os.path.join(settings.BASE_DIR, 'sdn.csv'))
        urllib.request.urlretrieve(urlalt, os.path.join(settings.BASE_DIR, 'alt.csv'))
        with open('sdn.csv', newline='') as csvfile:
            spamreader = csv.reader(csvfile)
            for row in spamreader:
                sdn.append(row)


        cache.set('sdn', sdn)

        with open('alt.csv', newline='') as csvfile:
            spamreader = csv.reader(csvfile)
            for row in spamreader:
                alt.append(row)

    except:
        pass
            
    