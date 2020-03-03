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
    #downloadfile()
    connStr = (r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=C:\Users\jcleveland\Documents\GitHub\busqueda\algoritmos\db.mdb;")
    conn = pypyodbc.connect(connStr)
    cur = conn.cursor()
    cur.execute("SELECT CreatureID, Name_EN, Name_JP FROM Creatures")
    
    html = "<html><body><table><tr><th>word</th><th>Compare</th><th>soundex</th><th>jaro</th></tr>"
    word = 'GoXila'
    comparationsoundex('Reyes martinez Raul'.upper(),'Reyes Raul'.upper())
    comparewithcsv('Raul'.upper())

    while True:
        row = cur.fetchone()
        if row is None:
            break
        #comparewithcsv(row[1].upper())
        
        #rsjaro = jaro.jaro_winkler_metric(word,row.get("Name_EN"))
        #presaundex = soundx(row.get("Name_EN"))
        #rssound    = jaro.jaro_winkler_metric(originalsoundx,presaundex)
        #html += u"<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td></tr>".format(word,row.get("Name_EN"),rssound, rsjaro)
    cur.close()
    conn.close()
    html += "</table></body></html>"
    return HttpResponse(html)


def comparewithcsv(name):
    soundex = Soundex()
    originalsoundx = soundex.phonetics(name)
    maxjaro=0
    maxsound=0
    rssounddata={}
    rsjarodata={}
    results = []
    with open('file.csv', newline='') as csvfile:
        spamreader = csv.reader(csvfile)
        for row in spamreader:
            try:
                namecsv= row[1].upper()
                splitaka= row[11].find('a.k.a. ')
                if splitaka > 0:
                    akdata = row[11].split(';')
                    for i in akdata: 
                        if i.find('a.k.a. ') > 0:
                            akaname = i.split("'")
                            rsjaro      = jaro.original_metric(name,akaname[1].upper())*100
                            presaundex  = soundex.phonetics(akaname[1].upper())
                            rssound     = jaro.jaro_metric(originalsoundx,presaundex)*100
                            if rsjaro > 85 :
                                print(u"this is {0} - {1} - {2} - {3}".format(name,akaname[1].upper(),rssound, rsjaro))
                                maxjaro = rsjaro
                                results.append(row)
                
                rsjaro      = jaro.original_metric(name,namecsv)*100
                presaundex  = soundex.phonetics(namecsv)
                rssound     = jaro.original_metric(originalsoundx,presaundex)*100
                
                if rsjaro > 85:
                    print(u"this is {0} - {1} - {2} - {3}".format(name,namecsv,rssound, rsjaro))
                    maxjaro = rsjaro
                    results.append(row)
            except:
                pass
    #print(results)
    #return results


def comparationsoundex(name,compare):
    soundex = Soundex()
    lista1 = name.replace(',','').split(' ')
    lista2 = compare.replace(',','').split(' ') 
    rs = []
    for a in lista1: 
        print('-- '+a)
        for b in lista2: 
            print('---- '+b)
            dato = jaro.jaro_winkler_metric(a,b)*100
            if 
            rs.append(dato)
    print(rs)


def downloadfile():
    print('Beginning file download with urllib2...')
    url = 'https://people.sc.fsu.edu/~jburkardt/data/csv/oscar_age_male.csv'
    urllib.request.urlretrieve(url, 'C:\\Users\\jcleveland\\Documents\\GitHub\\busqueda\\algoritmos\\file.csv')
    