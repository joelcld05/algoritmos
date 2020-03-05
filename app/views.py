from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from pyphonetics import Soundex
import urllib.request
import datetime
import pypyodbc
import jaro
import csv


@require_http_methods(["GET", "POST"])
def index(request):
    return HttpResponse(render(request, 'index.html'))

# Create your views here.
def current_datetime(request):
    connStr = (r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=C:\Users\jcleveland\Documents\GitHub\busqueda\algoritmos\db.accdb;")
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
    maxvalue = 90
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
                            if rsjaro >= maxvalue or rssound >= maxvalue:
                                results.append([row[0],row[1],akaname,row[3],rsjaro, rssound])
                                continue
                            rsjarowords = comparationbyword(name, akaname)
                            if rsjarowords[1] >= maxvalue and rsjarowords[0] >= maxvalue:
                                results.append({'id':row[0],'nombre':row[1],'alias':akaname,'tipo':row[3],'jaro':float("{0:.2f}".format(rsjarowords[0])), 'sound':float("{0:.2f}".format(rsjarowords[1]))})

                namecsv     = row[1].upper()
                rsjaro      = jaro.jaro_winkler_metric(name,namecsv)*100
                presaundex  = soundex.phonetics(namecsv)
                rssound     = jaro.jaro_winkler_metric(originalsoundx,presaundex)*100
                if rsjaro >= maxvalue and rssound >= maxvalue:
                    results.append({'id':row[0],'nombre':row[1],'alias':'','tipo':row[3],'jaro':rsjaro, 'sound':rssound})
                    continue
                rsjarowords = comparationbyword(name, namecsv)
                if  rsjarowords[1] >= 90 and rsjarowords[0] >= 85:
                    results.append({'id':row[0],'nombre':row[1],'alias':'','tipo':row[3],'jaro':float("{0:.2f}".format(rsjarowords[0])), 'sound':float("{0:.2f}".format(rsjarowords[1]))})        
            except:
                pass
            
    results = sorted(results, key=lambda x: x['jaro'], reverse=True)
    return results


def comparationbyword(name,compare):
    soundex = Soundex()
    lista1 = list(dict.fromkeys(name.replace(',','').split(' ')))
    lista2 = list(dict.fromkeys(compare.replace(',','').split(' ')))
    maxvalue = 85
    cuentaj = 0
    cuentas = 0
    maxjaro=[]
    maxsound= []
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
    print('Beginning file download with urllib2...')
    url = 'https://people.sc.fsu.edu/~jburkardt/data/csv/oscar_age_male.csv'
    urllib.request.urlretrieve(url, 'C:\\Users\\jcleveland\\Documents\\GitHub\\busqueda\\algoritmos\\file.csv')
    