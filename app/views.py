from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from pyphonetics import Soundex
from algoritmos import settings
from fuzzywuzzy import fuzz
import urllib.request
import datetime
import pypyodbc
import jaro
import csv
import os

@require_http_methods(["GET", "POST"])
def index(request):
    #connStr = (r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ="+os.path.join(settings.BASE_DIR, 'db.accdb')+";")
    #conn = pypyodbc.connect(connStr)
    #cur = conn.cursor()
    #cur.execute("insert into Creatures(CreatureID, Name_EN, Name_JP) values (4,'Joshua','Joel')")
    #cur.commit()
    #cur.close()
    #conn.close()
    return HttpResponse(render(request, 'index.html'))

# Create your views here.
def current_datetime(request):
    #downloadfile()
    connStr = (r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ="+os.path.join(settings.BASE_DIR, 'db.accdb')+";")
    conn = pypyodbc.connect(connStr)
    cur = conn.cursor()
    cur.execute("SELECT CreatureID, Name_EN, Name_JP FROM Creatures")
    rs = []
    while True:
        row = cur.fetchone()
        if row is None:
            break
        nombre = row[1].upper()
        response= comparewithcsv(nombre)
        totalrs =  len(response)
        if totalrs > 0:
            rs.append({'datos':response,'total':totalrs,'nombre':nombre})
    cur.close()
    conn.close()
    return HttpResponse(render(request, 'table.html',{'datsdb':rs}))


def comparewithcsv(name):
    soundex = Soundex()
    originalsoundx = soundex.phonetics(name)
    results = []
    maxvalue = 85
    with open('file.csv', newline='') as csvfile:
        spamreader = csv.reader(csvfile)
        for row in spamreader:
            try:
                splitaka= row[11].find('a.k.a. ')
                if splitaka > 0:
                    akdata = row[11].split(';')
                    for i in akdata: 
                        if i.find('a.k.a. ') > 0:
                            akaname     = i.split("'")[1].upper()
                            rsjaro      = jaro.jaro_winkler_metric(name,akaname[1])*100
                            presaundex  = soundex.phonetics(akaname[1])
                            rssound     = jaro.jaro_winkler_metric(originalsoundx,presaundex)*100
                            if rsjaro >= maxvalue and rssound >= maxvalue:
                                results.append([row[0],row[1],akaname,row[3],rsjaro, rssound])
                                #continue
                                
                            rsjarowords = comparationbyword(name, akaname)
                            if rsjarowords[1] >= maxvalue and rsjarowords[0] >= maxvalue:
                                results.append({'id':row[0],'nombre':row[1],'alias':akaname,'tipo':row[3],'jaro':rsjarowords[0], 'sound':rsjarowords[1]})
                            
                    
                namecsv     = row[1].upper()
                rsjaro      = jaro.jaro_winkler_metric(name,namecsv)*100
                presaundex  = soundex.phonetics(namecsv)
                rssound     = jaro.jaro_winkler_metric(originalsoundx,presaundex)*100
                if rsjaro >= maxvalue and rssound >= maxvalue:
                    results.append({'id':row[0],'nombre':row[1],'alias':'','tipo':row[3],'jaro':rsjaro, 'sound':rssound})
                    #continue

                rsjarowords = comparationbyword(name, namecsv)
                if rsjarowords[1] >= maxvalue and rsjarowords[0] >= maxvalue:
                                results.append({'id':row[0],'nombre':row[1],'alias':'','tipo':row[3],'jaro':rsjarowords[0], 'sound':rsjarowords[1]})
                            
            except:
                pass
            
    results = sorted(results, key=lambda x: x['jaro'], reverse=True)

    return results


def comparationbyword(name,compare):
    soundex = Soundex()
    lista1 = list(dict.fromkeys(name.replace(',','').split(' ')))
    lista2 = list(dict.fromkeys(compare.replace(',','').split(' ')))
    maxvalue = 85
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


def downloadfile():
    url = 'https://www.treasury.gov/ofac/downloads/sdn.csv'
    urllib.request.urlretrieve(url, os.path.join(settings.BASE_DIR, 'file.csv'))
    