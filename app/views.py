from django.shortcuts import render
from django.http import HttpResponse
import urllib.request
import datetime
import pypyodbc
import pyodbc
import jaro
import fuzzy
import csv
pypyodbc.lowercase = False






# Create your views here.
def current_datetime(request):
    downloadfile()
    connStr = (r"DRIVER={Microsoft Access Driver (*.mdb)};DBQ=C:\Users\jcleveland\Documents\GitHub\busqueda\algoritmos\db.mdb;")
    conn = pypyodbc.connect(connStr)
    cur = conn.cursor()
    cur.execute("SELECT CreatureID, Name_EN, Name_JP FROM Creatures")
    soundx = fuzzy.Soundex(10)
    html = "<html><body><table><tr><th>word</th><th>Compare</th><th>soundex</th><th>jaro</th></tr>"
    word = 'GoXila'
    originalsoundx = soundx(word)

    while True:
        row = cur.fetchone()
        if row is None:
            break

        comparewithcsv(row.get("Name_EN"))
        rsjaro = jaro.jaro_winkler_metric(word,row.get("Name_EN"))
        presaundex = soundx(row.get("Name_EN"))
        rssound    = jaro.jaro_winkler_metric(originalsoundx,presaundex)
        html += u"<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td></tr>".format(word,row.get("Name_EN"),rssound, rsjaro)

    cur.close()
    conn.close()
    html += "</table></body></html>"
    return HttpResponse(html)


def comparewithcsv(name):
    soundx = fuzzy.Soundex(10)
    originalsoundx = soundx(name)
    maxjaro=0
    maxsound=0
    rssounddata={}
    rsjarodata={}
    with open('file.csv', newline='') as csvfile:
        spamreader = csv.DictReader(csvfile)
        for row in spamreader:
            data = dict(row)
            namecsv     =  data[' "Name"'].strip().replace('"','')
            rsjaro      = jaro.jaro_winkler_metric(name,namecsv)
            presaundex  = soundx(namecsv.encode('utf-8'))
            rssound     = jaro.jaro_winkler_metric(originalsoundx,presaundex)
            
            if rsjaro > maxjaro:
                maxjaro = rsjaro
                rsjarodata = data.copy()

            if rsjaro > maxsound:
                maxjaro = rsjaro
                rssound = data.copy()

            print(u"this is {0} - {1} - {2} - {3}".format(name,namecsv,rssound, rsjaro))


def downloadfile():
    print('Beginning file download with urllib2...')
    url = 'https://people.sc.fsu.edu/~jburkardt/data/csv/oscar_age_male.csv'
    urllib.request.urlretrieve(url, 'C:\\Users\\jcleveland\\Documents\\GitHub\\busqueda\\algoritmos\\file.csv')
    