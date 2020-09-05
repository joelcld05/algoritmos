from django.shortcuts import render
from django.http import (HttpResponse,HttpResponseRedirect,JsonResponse)
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
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
connStr = (r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ="+os.path.join(settings.BASE_DIR, 'db.accdb')+";")

@require_http_methods(["GET"])
def index(request):
    if 'username' in request.COOKIES:
        return HttpResponseRedirect('resultdos')
    else:
        response = HttpResponse(render(request, 'index.html'))
        response.delete_cookie('message')
        return response


@csrf_exempt 
def login(request):
    if request.method == "POST":
        conn = pypyodbc.connect(connStr)
        cur = conn.cursor()
        query = "SELECT count(id) FROM tbl_permisos where tipo='Administrador' and  User ='"+request.POST['user'] +"' and password='"+request.POST['password'] +"'"

        cur.execute(query)
        rs = []
        while True:
            row = cur.fetchone()
            if row is None:
                break
            rs=row
            
        if rs[0]>=1:
            username = request.POST['user']
            response = HttpResponseRedirect('resultdos')
            response.set_cookie('username', datetime.datetime.now())
        else:
            response = HttpResponse(render(request, 'index.html',{"message" : 'Credenciales incorrectas'}))
        return response
    else:
        return HttpResponseRedirect('/')


def logout(request):
    response = HttpResponseRedirect('/')
    response.delete_cookie('username')
    return response




@csrf_exempt 
def guarda(request):
    if request.method == "POST":
        try:
            idcliente=request.POST['idcliente']
            nombrecliente=request.POST['idcliente']
            idcompara=request.POST[idcliente+'-idcompara']
            lista1 = list(dict.fromkeys(idcompara.split(',')))
            conn = pypyodbc.connect(connStr)
            cur = conn.cursor()
            for a in lista1: 
                query = "insert into DatosGuardados(idclinete, observacion,idcompara,nombrecompara,reporta,jaro,sound)"
                query +=  " values ("+idcliente+",'"+request.POST['observacion-'+a]+"','"+a+"','"+request.POST['nombrecompara-'+a].replace("'",'')
                query +=  "',"+request.POST['conservar-'+a]+","+request.POST['jaro-'+a]+","+request.POST['sound-'+a]+" )"
                cur.execute(query)
            cur.commit()
            cur.close()
            conn.close()
            return HttpResponse('{"response":"true"}',content_type='application/json')
        except:
            return HttpResponse('{"response":"false"}',content_type='application/json')
    return HttpResponse('{"response":"fasle"}',content_type='application/json')



@require_http_methods(["GET"])
def initpage(request):
    if 'username' in request.COOKIES:
        downloadfile()
        conn = pypyodbc.connect(connStr)
        cur = conn.cursor()
        query = 'SELECT id, Nombre, Apellidos FROM clientes'
        cur.execute(query)
        rs = []
        while True:
            row = cur.fetchone()
            if row is None:
                break
            rs.append(row)
        cur.commit()
        cur.close()
        conn.close()
        return HttpResponse(render(request, 'table.html',{'datsdb':json.dumps(rs)}))
    else:
        return HttpResponseRedirect('/')


@csrf_exempt 
def getresult(request):
    if request.method == "POST":
        rs = []
        nombre = request.POST['nombre']
        idcompara = request.POST['id']
        conn = pypyodbc.connect(connStr)
        cur = conn.cursor()
        query = 'SELECT idcompara FROM DatosGuardados where idclinete ='+idcompara
        cur.execute(query)
        skip = []
        while True:
            row = cur.fetchone()
            if row is None:
                break
            lista = list(dict.fromkeys(row[0].split('-')))
            skip.append(lista[0])
        cur.commit()
        cur.close()
        conn.close()
        response =  comparewithcsv(nombre.replace(',','').upper(), skip)
        totalrs = len(response) 
        if totalrs > 0:
            rs.append({'datos':response,'total':totalrs,'nombre':nombre})
        return JsonResponse(rs,safe=False)


def comparewithcsv(name,skip):
    originalsoundx = soundex.phonetics(name)
    results = []
    sdn=[]
    alias = 'a.k.a. '

    with open('data.json') as json_file:
        data = json.load(json_file)
        for rowdata in data:
            try:
                row=rowdata['data']
                if row[0] in skip:
                    continue
                akadata= rowdata['aka']
                splitaka= row[11].find(alias)
                if splitaka > 0:
                    akdata = row[11].split(';')
                    for i in akdata: 
                        if i.find(alias) > 0:
                            akaname     = i.strip().replace(',','').split("'")[1].upper()
                            comparename=comparationcompletename(name,akaname,originalsoundx)
                            if comparename[0] >= maxvalue and comparename[1] >= maxvalue:
                                results.append({'id':row[0],'nombre':row[1],'alias':akaname,'tipo':row[3],'jaro':rsjaro, 'sound':rssound})
                                continue

                            rsjarowords = comparationbyword(name, akaname)
                            if rsjarowords[1] >= maxvalue and rsjarowords[0] >= maxvalue:
                                results.append({'id':row[0],'nombre':row[1],'alias':akaname,'tipo':row[3],'jaro':rsjarowords[0], 'sound':rsjarowords[1]})
                                
                
                if len(akadata) > 0:
                    for i in akadata: 
                        akaname     = i[3].strip().replace(',','').upper()
                        comparename=comparationcompletename(name,akaname,originalsoundx)
                        if comparename[0] >= maxvalue and comparename[1] >= maxvalue:
                            results.append({'id':row[0]+'-'+i[1] ,'nombre':row[1],'alias':akaname,'tipo':row[3],'jaro':rsjaro, 'sound':rssound})
                            continue

                        rsjarowords = comparationbyword(name, akaname)
                        if rsjarowords[1] >= maxvalue and rsjarowords[0] >= maxvalue:
                            results.append({'id':row[0]+'-'+i[1] ,'nombre':row[1],'alias':akaname,'tipo':row[3],'jaro':rsjarowords[0], 'sound':rsjarowords[1]})
                
                namecsv     = row[1].replace(',','').upper()
                comparename=comparationcompletename(name,namecsv,originalsoundx)
                if comparename[0] >= maxvalue and comparename[1] >= maxvalue:
                    results.append({'id':row[0],'nombre':row[1],'alias':'','tipo':row[3],'jaro':rsjaro, 'sound':rssound})
                    continue

                rsjarowords = comparationbyword(name, namecsv)
                if rsjarowords[1] >= maxvalue and rsjarowords[0] >= maxvalue:
                    results.append({'id':row[0],'nombre':row[1],'alias':'','tipo':row[3],'jaro':rsjarowords[0], 'sound':rsjarowords[1]})  
            except:
                pass
    results = sorted(results, key=lambda x: x['jaro'], reverse=True)
    return results

def comparationcompletename(name,compare,sound):
    presaundex  = soundex.phonetics(compare)
    rsjaro      = jaro.jaro_winkler_metric(name,compare)*100
    rssound     = jaro.jaro_winkler_metric(sound,presaundex)*100
    return [rsjaro,rssound]


def comparationbyword(name,compare):

    lista1 = list(dict.fromkeys(name.replace(',','').split(' ')))
    lista2 = list(dict.fromkeys(compare.replace(',','').split(' ')))

    arrayj= []
    cuentaj = 0
    cuentas = 0
    indexj = 0
    indexs = 0

    for a in lista1: 
        for b in lista2: 
            datojaro = jaro.jaro_winkler_metric(a.strip(),b.strip())*100
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
    try:
        sdn=[]
        alt={}
        name=datetime.datetime.now().strftime("%d-%m-%Y")
        urlsdn = 'https://www.treasury.gov/ofac/downloads/sdn.csv'
        urlalt = 'https://www.treasury.gov/ofac/downloads/alt.csv'
        urllib.request.urlretrieve(urlsdn, os.path.join(settings.BASE_DIR, 'static/data/sdn-'+name+'.csv'))
        urllib.request.urlretrieve(urlalt, os.path.join(settings.BASE_DIR, 'static/data/alt-'+name+'.csv'))

        with open('static/data/alt-'+name+'.csv', newline='') as csvfile:
            spamreader = csv.reader(csvfile)
            for row in spamreader:
                if not row[0] in alt:
                    alt[row[0]]=[row]
                else:
                    alt[row[0]].append(row)

        with open('static/data/sdn-'+name+'.csv', newline='') as csvfile:
            spamreader = csv.reader(csvfile)
            for row in spamreader:
                akadato=[]
                if row[0] in alt:
                    akadato=alt[row[0]]
                item = {'data':row,'aka':akadato}
                sdn.append(item)
        
        with open('data.json', 'w') as write_file:
            json.dump(sdn,write_file)
    except:
        pass
            



@require_http_methods(["GET"])
def reportpage(request):
    if 'username' in request.COOKIES:
        downloadfile()
        connStr = (r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ="+os.path.join(settings.BASE_DIR, 'db.accdb')+";")
        conn = pypyodbc.connect(connStr)
        cur = conn.cursor()
        query = 'SELECT ID Apellidos FROM reprotes'
        cur.execute(query)
        rs = []
        while True:
            row = cur.fetchone()
            if row is None:
                break
            rs.append(row)
        return HttpResponse(render(request, 'table.html',{'datsdb':json.dumps(rs)}))
    else:
        return HttpResponseRedirect('/')