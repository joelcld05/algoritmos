from django.shortcuts import render
from django.http import (HttpResponse,HttpResponseRedirect,JsonResponse)
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from pyphonetics import Soundex
from algoritmos import settings

import urllib.request
import pandas as pd
import numpy as np
import functools
import pypyodbc
import datetime
import sqlite3
import jaro
import json
import csv
import os

comparationscon = sqlite3.connect('comparations.db',check_same_thread=False)

soundex = Soundex()
maxvalue = 85
connStr = (r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ="+os.path.join(settings.BASE_DIR, 'GFUX_DWH2.accdb')+";")

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
            response = HttpResponseRedirect('reportes')
            response.set_cookie('username', request.POST['user'])
        else:
            response = HttpResponse(render(request, 'index.html',{"message" : 'Credenciales incorrectas'}))
        return response
    else:
        return HttpResponseRedirect('reportes')


def logout(request):
    response = HttpResponseRedirect('/')
    response.delete_cookie('username')
    return response


@csrf_exempt
def guarda(request):
    if request.method == "POST":
        try:
            idinsert = datetime.datetime.now().strftime("%d%m%Y")
            idcliente=request.POST['idcliente']
            nombrecliente=request.POST['idcliente']
            idcompara=request.POST[idcliente+'-idcompara']
            lista1 = list(dict.fromkeys(idcompara.split(',')))
            conn = pypyodbc.connect(connStr)
            cur = conn.cursor()
            for a in lista1: 
                accion=request.POST["conservar-"+a]
                query = "insert into tbl_ofac_reportados(idclinete,observacion,idcompara,nombrecompara,reporta,jaro,sound,report,accion)"
                query +=  " values ('"+idcliente+"','"+request.POST['observacion-'+a].replace("'",'')+"','"+a+"','"+request.POST['nombrecompara-'+a].replace("'",'')
                query +=  "','"+request.COOKIES['username'].replace("'",'')+"',"+request.POST['jaro-'+a]+","+request.POST['sound-'+a]+","+idinsert+",'"+accion+"' )"
                
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
        idinsert = datetime.datetime.now().strftime("%d%m%Y")
        downloadfile()
        verificareporte(request.COOKIES['username'],idinsert)
        conn = pypyodbc.connect(connStr)
        cur = conn.cursor()
        query = 'SELECT id, name, lastname FROM OFAC'
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
        return HttpResponse(render(request, 'table.html',{'datsdb':json.dumps(rs), 'idreporte':idinsert}))
    else:
        return HttpResponseRedirect('/')


def verificareporte(username,idinsert):
    conn = pypyodbc.connect(connStr)
    cur = conn.cursor()
    query = 'SELECT id FROM tbl_ofac_reportes where id='+idinsert
    cur.execute(query)
    row = cur.fetchall()
    if len(row)==0:
        conn2 = pypyodbc.connect(connStr)
        cur2 = conn2.cursor()
        query = "insert into tbl_ofac_reportes(id,usuario) values ("+idinsert+",'"+ username+"');"
        cur2.execute(query)
        cur2.commit()
        cur2.close()
        conn2.close()
    cur.close()
    conn.close()
    

@csrf_exempt 
def getresult(request):
    if request.method == "POST":
        rs = []
        nombre = request.POST['nombre']
        idcompara = request.POST['id']

        cursor = comparationscon.execute("SELECT idofac from comparations where idcliente='"+idcompara+"'")
        rows = cursor.fetchall()
        skip = []
        for row in rows:
            skip.append(row[0])

        conn = pypyodbc.connect(connStr)
        cur = conn.cursor()
        query = "SELECT idcompara,idclinete FROM tbl_ofac_reportados where idclinete ='"+idcompara+"' and accion='Reportado'"
        cur.execute(query)

        while True:
            row = cur.fetchone()
            if row is None:
                break
            lista = list(dict.fromkeys(row[0].split('-')))
            idofac=lista[0].split("-")
            skip.append(int(idofac[0]))

        cur.commit()
        cur.close()
        conn.close()
    
        response =  comparewithcsv(nombre.replace(',','').upper(), skip,idcompara)
        totalrs = len(response) 
        if totalrs > 0:
            rs.append({'datos':response,'total':totalrs,'nombre':nombre})
        return JsonResponse(rs,safe=False)


def comparewithcsv(name,skip,idcompara):
    originalsoundx = soundex.phonetics(name)
    results = []
    sdn=[]
    alias = 'a.k.a. '
    with open('data.json') as json_file:
        data = json.load(json_file)
        for rowdata in data:
            guardaofac=0
            try:
                row=rowdata['data']
                if int(row[0]) not in skip:
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
                                    guardaofac=1
                                    continue

                                rsjarowords = comparationbyword(name, akaname)
                                if rsjarowords[1] >= maxvalue and rsjarowords[0] >= maxvalue:
                                    results.append({'id':row[0],'nombre':row[1],'alias':akaname,'tipo':row[3],'jaro':rsjarowords[0], 'sound':rsjarowords[1]})
                                    guardaofac=1

                    if len(akadata) > 0:
                        for i in akadata: 
                            akaname     = i[3].strip().replace(',','').upper()
                            comparename=comparationcompletename(name,akaname,originalsoundx)
                            if comparename[0] >= maxvalue and comparename[1] >= maxvalue:
                                results.append({'id':row[0]+'-'+i[1] ,'nombre':row[1],'alias':akaname,'tipo':row[3],'jaro':rsjaro, 'sound':rssound})
                                guardaofac=1
                                continue

                            rsjarowords = comparationbyword(name, akaname)
                            if rsjarowords[1] >= maxvalue and rsjarowords[0] >= maxvalue:
                                results.append({'id':row[0]+'-'+i[1] ,'nombre':row[1],'alias':akaname,'tipo':row[3],'jaro':rsjarowords[0], 'sound':rsjarowords[1]})
                                guardaofac=1
                    
                    namecsv     = row[1].replace(',','').upper()
                    comparename=comparationcompletename(name,namecsv,originalsoundx)
                    if comparename[0] >= maxvalue and comparename[1] >= maxvalue:
                        results.append({'id':row[0],'nombre':row[1],'alias':'','tipo':row[3],'jaro':rsjaro, 'sound':rssound})
                        guardaofac=1
                        continue

                    rsjarowords = comparationbyword(name, namecsv)
                    if rsjarowords[1] >= maxvalue and rsjarowords[0] >= maxvalue:
                        results.append({'id':row[0],'nombre':row[1],'alias':'','tipo':row[3],'jaro':rsjarowords[0], 'sound':rsjarowords[1]})
                        guardaofac=1

                    if guardaofac==0:
                        cur = comparationscon.cursor()
                        cur.execute("INSERT INTO comparations (idcliente, idofac)  VALUES ('"+idcompara+"', "+row[0]+");")
                    
                    
            except:
                    pass
    results = sorted(results, key=lambda x: x['jaro'], reverse=True)
    comparationscon.commit()
    return results

def comparationcompletename(name,compare,sound):
    presaundex  = soundex.phonetics(compare)
    rsjaro      = jaro.jaro_winkler_metric(name,compare)*100
    rssound     = jaro.jaro_winkler_metric(sound,presaundex)*100
    return [rsjaro,rssound]


def comparationbyword(name,compare):
    lista1 = list(dict.fromkeys(name.replace(',','').replace("'",'').split(' ')))
    lista2 = list(dict.fromkeys(compare.replace(',','').replace("'",'').split(' ')))

    arrayj= []
    cantidadenlista=0
    cuentaj = 0
    cuentas = 0
    indexj = 0
    indexs = 0

    for a in lista1: 
        for b in lista2: 

            try:
                datojaro = jaro.jaro_winkler_metric(a.strip(),b.strip())*100
                datosound = jaro.jaro_winkler_metric(soundex.phonetics(a),soundex.phonetics(b))*100
            except:
                pass

            if datojaro >= maxvalue:
                indexj +=1
                cuentaj += datojaro
            if datosound >= maxvalue:
                indexs +=1
                cuentas += datosound

    cuentaj = cuentaj / max([len(lista1), indexj])
    cuentas = cuentas / max([len(lista1), indexs])
    
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
        idinsert = datetime.datetime.now().strftime("%d%m%Y")
        #connStr = (r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ="+os.path.join(settings.BASE_DIR, 'db.accdb')+";")
        conn = pypyodbc.connect(connStr)
        cur = conn.cursor()
        query = 'select top 12 str(tbl_ofac_reportes.fecha) as fecha, tbl_ofac_reportes.usuario, count(tbl_ofac_reportes.ID) as totales,tbl_ofac_reportes.ID from tbl_ofac_reportes inner join tbl_ofac_reportados on tbl_ofac_reportados.report=tbl_ofac_reportes.ID group by tbl_ofac_reportes.ID, tbl_ofac_reportes.fecha, tbl_ofac_reportes.usuario order by tbl_ofac_reportes.fecha desc'
        cur.execute(query)
        rs = []
        while True:
            row = cur.fetchone()
            if row is None:
                break
            rs.append(row)
        
        return HttpResponse(render(request, 'reportes.html',{'datsdb': rs}))
    else:
        return HttpResponseRedirect('/')


@require_http_methods(["GET"])
def printReport(request,idreport):
    if 'username' in request.COOKIES:
        idinsert = datetime.datetime.now().strftime("%d%m%Y")
        #connStr = (r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ="+os.path.join(settings.BASE_DIR, 'db.accdb')+";")
        conn = pypyodbc.connect(connStr)
        cur = conn.cursor()
        query = 'select reporta,fecha,idclinete, name, lastname, id,observacion,idcompara,nombrecompara,jaro,sound, accion from tbl_ofac_reportados inner join OFAC on OFAC.id=tbl_ofac_reportados.idclinete where report='+str(idreport)
        cur.execute(query)
        row = cur.fetchall()

        file_name = str(idreport)+'-reporte.xlsx'
        path_to_file = settings.BASE_DIR+'/static/exports/'

        df = pd.DataFrame(row, columns = ['Reportado Por','Fecha reportado','ID Cliente', 'Nombres', 'Apellidos', 'Cédula','Observación','ID OFAC','Nombre OFAC','Jaro','Sound','Acción'])
        df.to_excel(path_to_file+file_name, index = False, header=True)
        
        file_path=path_to_file+file_name
        if os.path.exists(file_path):
            with open(file_path, 'rb') as fh:
                response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
                response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
                return response
        raise Http404
    else:
        return HttpResponseRedirect('/')