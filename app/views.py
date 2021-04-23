from django.shortcuts import render
from django.http import (HttpResponse,HttpResponseRedirect,JsonResponse)
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from algoritmos import settings
from bs4 import BeautifulSoup
import urllib.request
import pandas as pd
import functools
import requests
import pypyodbc
import datetime
import sqlite3
import json
import csv
import os


comparationscon = sqlite3.connect('comparations.db',check_same_thread=False)

maxvalue = 75
#connStr = (r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=\\Grupofux\prestamos clientes\FINANCIERA UNIVERSAL XPRESS\COTIZACIONES\GRUPO_FUX_COTIZADOR\Archivo\GFUX_DWH.accdb;")
connStr = (r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=C:\Users\HP\Documents\projects\algoritmos\GFUX_DWH.accdb;")

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
        query = "SELECT count(id) FROM tbl_permisos where tipo in ('Administrador','Cobros') and  User ='"+request.POST['user'] +"' and password='"+request.POST['password'] +"'"

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
        #try:
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
                query +=  "','"+request.COOKIES['username'].replace("'",'')+"',"+request.POST['score-'+a]+",'0',"+idinsert+",'"+accion+"' )"

                curguarda = comparationscon.cursor()
                curguarda.execute("INSERT INTO comparations (idcliente, idofac)  VALUES ('"+idcliente+"', "+a+");")
                cur.execute(query)
            comparationscon.commit()
            cur.commit()
            cur.close()
            conn.close()
            return HttpResponse('{"response":"true"}',content_type='application/json')
        #except:
        #    return HttpResponse('{"response":"false"}',content_type='application/json')
    return HttpResponse('{"response":"fasle"}',content_type='application/json')


@require_http_methods(["GET"])
def initpage(request):
    if 'username' in request.COOKIES:
        idinsert = datetime.datetime.now().strftime("%d%m%Y")
        #downloadfile()
        getToken()
        verificareporte(request.COOKIES['username'],idinsert)
        conn = pypyodbc.connect(connStr)
        cur = conn.cursor()
        query = "SELECT id, name, lastname FROM OFAC where id not in(SELECT distinct idclinete FROM tbl_ofac_reportados where accion ='Reportado')"
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

        response =  searchName(nombre.replace(',','').upper(),skip)
        
        totalrs = len(response) 
        if totalrs > 0:
            rs.append({'datos':response,'total':totalrs,'nombre':nombre})
        return JsonResponse(rs,safe=False)


def searchName(name,skip):
    token=""
    with open('ofactoken.json') as json_file:
        data = json.load(json_file)
    token=data['token']
    r=[]
    r = requests.post('https://sanctionssearch.ofac.treas.gov/', 
    data = {
        'ctl00_ctl03_HiddenField':';;AjaxControlToolkit, Version=3.5.40412.0, Culture=neutral, PublicKeyToken=28f01b0e84b6d53e:en-US:1547e793-5b7e-48fe-8490-03a375b13a33:475a4ef5:5546a2b:d2e10b12:497ef277:effe2a26',
        '__EVENTTARGET':'',
        '__EVENTARGUMENT':'',
        '__VIEWSTATE':token,
        '__VIEWSTATEGENERATOR':'CA0B0334',
        'ctl00$MainContent$ddlType':'',
        'ctl00$MainContent$txtAddress':'',
        'ctl00$MainContent$txtLastName':name,
        'ctl00$MainContent$txtCity':'',
        'ctl00$MainContent$txtID':'',
        'ctl00$MainContent$txtState':'',
        'ctl00$MainContent$lstPrograms':'',
        'ctl00$MainContent$ddlCountry':'',               
        'ctl00$MainContent$ddlList':'',  
        'ctl00$MainContent$Slider1':'85',  
        'ctl00$MainContent$Slider1_Boundcontrol':'85',  
        'ctl00$MainContent$btnSearch':'Search' 
        })
    
    soup = BeautifulSoup(r.text, 'html.parser')
    rsdata=[]
    table = soup.find(id="gvSearchResults")
    
    if table is not None:
        for link in table.find_all('tr'):
            newdata=[]
            linkofac=link.a
            actialid=0
            if linkofac is not None:
                actialid = linkofac.get('href').split("=")[1]
                #actialid= datalink.split("=")[1].replace('"','')
                newdata.append(actialid)
            if int(actialid) not in skip:
                for item in link.find_all('td'):
                    newdata.append(item.get_text().strip())
                rsdata.append(newdata)
    
    return rsdata



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
        conn = pypyodbc.connect(connStr)
        cur = conn.cursor()
        query = 'select reporta,fecha,idclinete, name, lastname, id,observacion,idcompara,nombrecompara,jaro,sound, accion from tbl_ofac_reportados inner join OFAC on OFAC.id=tbl_ofac_reportados.idclinete where report='+str(idreport)
        cur.execute(query)
        row = cur.fetchall()

        file_name = str(idreport)+'-reporte.xlsx'
        path_to_file = settings.BASE_DIR+'/static/exports/'

        df = pd.DataFrame(row, columns = ['Reportado Por','Fecha reportado','ID Cliente', 'Nombres', 'Apellidos', 'Cédula','Observación','ID OFAC','Nombre OFAC','Score','','Acción'])
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


def getToken():
    r=[]
    r = requests.get('https://sanctionssearch.ofac.treas.gov/')
    soup = BeautifulSoup(r.text, 'html.parser')
    rsdata=[]
    table = soup.find(id="__VIEWSTATE")['value']
    data={"token":table}
    
    with open('ofactoken.json', 'w') as write_file:
        json.dump(data,write_file)
    return False

