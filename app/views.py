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
connStr = (r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=\\Grupofux\prestamos clientes\FINANCIERA UNIVERSAL XPRESS\COTIZACIONES\GRUPO_FUX_COTIZADOR\Archivo\GFUX_DWH.accdb;")

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
    r=[]

    r = requests.post('https://sanctionssearch.ofac.treas.gov/', 
    data = {
        'ctl00_ctl03_HiddenField':';;AjaxControlToolkit, Version=3.5.40412.0, Culture=neutral, PublicKeyToken=28f01b0e84b6d53e:en-US:1547e793-5b7e-48fe-8490-03a375b13a33:475a4ef5:5546a2b:d2e10b12:497ef277:effe2a26',
        '__EVENTTARGET':'',
        '__EVENTARGUMENT':'',
        '__VIEWSTATE':'/wEPDwUJMzIwMTQ1Njg3D2QWAmYPZBYCAgMPZBYSAgUPDxYCHgRUZXh0BZ4OU3BlY2lhbGx5IERlc2lnbmF0ZWQgTmF0aW9uYWxzIGFuZCBCbG9ja2VkIFBlcnNvbnMgbGlzdCAoIlNETiBMaXN0IikgYW5kIGFsbCBvdGhlciBzYW5jdGlvbnMgbGlzdHMgYWRtaW5pc3RlcmVkIGJ5IE9GQUMsIGluY2x1ZGluZyB0aGUgRm9yZWlnbiBTYW5jdGlvbnMgRXZhZGVycyBMaXN0LCB0aGUgTm9uLVNETiBJcmFuIFNhbmN0aW9ucyBBY3QgTGlzdCwgdGhlIFNlY3RvcmFsIFNhbmN0aW9ucyBJZGVudGlmaWNhdGlvbnMgTGlzdCwgdGhlIExpc3Qgb2YgRm9yZWlnbiBGaW5hbmNpYWwgSW5zdGl0dXRpb25zIFN1YmplY3QgdG8gQ29ycmVzcG9uZGVudCBBY2NvdW50IG9yIFBheWFibGUtVGhyb3VnaCBBY2NvdW50IFNhbmN0aW9ucyBhbmQgdGhlIE5vbi1TRE4gUGFsZXN0aW5pYW4gTGVnaXNsYXRpdmUgQ291bmNpbCBMaXN0LiBHaXZlbiB0aGUgbnVtYmVyIG9mIGxpc3RzIHRoYXQgbm93IHJlc2lkZSBpbiB0aGUgU2FuY3Rpb25zIExpc3QgU2VhcmNoIHRvb2wsIGl0IGlzIHN0cm9uZ2x5IHJlY29tbWVuZGVkIHRoYXQgdXNlcnMgcGF5IGNsb3NlIGF0dGVudGlvbiB0byB0aGUgcHJvZ3JhbSBjb2RlcyBhc3NvY2lhdGVkIHdpdGggZWFjaCByZXR1cm5lZCByZWNvcmQuIFRoZXNlIHByb2dyYW0gY29kZXMgaW5kaWNhdGUgaG93IGEgdHJ1ZSBoaXQgb24gYSByZXR1cm5lZCB2YWx1ZSBzaG91bGQgYmUgdHJlYXRlZC4gVGhlIFNhbmN0aW9ucyBMaXN0IFNlYXJjaCB0b29sIHVzZXMgYXBwcm94aW1hdGUgc3RyaW5nIG1hdGNoaW5nIHRvIGlkZW50aWZ5IHBvc3NpYmxlIG1hdGNoZXMgYmV0d2VlbiB3b3JkIG9yIGNoYXJhY3RlciBzdHJpbmdzIGFzIGVudGVyZWQgaW50byBTYW5jdGlvbnMgTGlzdCBTZWFyY2gsIGFuZCBhbnkgbmFtZSBvciBuYW1lIGNvbXBvbmVudCBhcyBpdCBhcHBlYXJzIG9uIHRoZSBTRE4gTGlzdCBhbmQvb3IgdGhlIHZhcmlvdXMgb3RoZXIgc2FuY3Rpb25zIGxpc3RzLiBTYW5jdGlvbnMgTGlzdCBTZWFyY2ggaGFzIGEgc2xpZGVyLWJhciB0aGF0IG1heSBiZSB1c2VkIHRvIHNldCBhIHRocmVzaG9sZCAoaS5lLiwgYSBjb25maWRlbmNlIHJhdGluZykgZm9yIHRoZSBjbG9zZW5lc3Mgb2YgYW55IHBvdGVudGlhbCBtYXRjaCByZXR1cm5lZCBhcyBhIHJlc3VsdCBvZiBhIHVzZXIncyBzZWFyY2guIFNhbmN0aW9ucyBMaXN0IFNlYXJjaCB3aWxsIGRldGVjdCBjZXJ0YWluIG1pc3NwZWxsaW5ncyBvciBvdGhlciBpbmNvcnJlY3RseSBlbnRlcmVkIHRleHQsIGFuZCB3aWxsIHJldHVybiBuZWFyLCBvciBwcm94aW1hdGUsIG1hdGNoZXMsIGJhc2VkIG9uIHRoZSBjb25maWRlbmNlIHJhdGluZyBzZXQgYnkgdGhlIHVzZXIgdmlhIHRoZSBzbGlkZXItYmFyLiBPRkFDIGRvZXMgbm90IHByb3ZpZGUgcmVjb21tZW5kYXRpb25zIHdpdGggcmVnYXJkIHRvIHRoZSBhcHByb3ByaWF0ZW5lc3Mgb2YgYW55IHNwZWNpZmljIGNvbmZpZGVuY2UgcmF0aW5nLiBTYW5jdGlvbnMgTGlzdCBTZWFyY2ggaXMgb25lIHRvb2wgb2ZmZXJlZCB0byBhc3Npc3QgdXNlcnMgaW4gdXRpbGl6aW5nIHRoZSBTRE4gTGlzdCBhbmQvb3IgdGhlIHZhcmlvdXMgb3RoZXIgc2FuY3Rpb25zIGxpc3RzOyB1c2Ugb2YgU2FuY3Rpb25zIExpc3QgU2VhcmNoIGlzIG5vdCBhIHN1YnN0aXR1dGUgZm9yIHVuZGVydGFraW5nIGFwcHJvcHJpYXRlIGR1ZSBkaWxpZ2VuY2UuIFRoZSB1c2Ugb2YgU2FuY3Rpb25zIExpc3QgU2VhcmNoIGRvZXMgbm90IGxpbWl0IGFueSBjcmltaW5hbCBvciBjaXZpbCBsaWFiaWxpdHkgZm9yIGFueSBhY3QgdW5kZXJ0YWtlbiBhcyBhIHJlc3VsdCBvZiwgb3IgaW4gcmVsaWFuY2Ugb24sIHN1Y2ggdXNlLmRkAgcPDxYCHgtOYXZpZ2F0ZVVybAV5aHR0cHM6Ly9ob21lLnRyZWFzdXJ5Lmdvdi9wb2xpY3ktaXNzdWVzL2ZpbmFuY2lhbC1zYW5jdGlvbnMvc3BlY2lhbGx5LWRlc2lnbmF0ZWQtbmF0aW9uYWxzLWxpc3QtZGF0YS1mb3JtYXRzLWRhdGEtc2NoZW1hc2RkAgkPDxYCHwEFRGh0dHBzOi8vaG9tZS50cmVhc3VyeS5nb3YvcG9saWN5LWlzc3Vlcy9maW5hbmNpYWwtc2FuY3Rpb25zL2ZhcXMvMjg3ZGQCCw8PFgIfAQVraHR0cHM6Ly9ob21lLnRyZWFzdXJ5Lmdvdi9wb2xpY3ktaXNzdWVzL29mZmljZS1vZi1mb3JlaWduLWFzc2V0cy1jb250cm9sLXNhbmN0aW9ucy1wcm9ncmFtcy1hbmQtaW5mb3JtYXRpb25kZAINDw8WAh8BBWJodHRwczovL2hvbWUudHJlYXN1cnkuZ292L3BvbGljeS1pc3N1ZXMvZmluYW5jaWFsLXNhbmN0aW9ucy9jb25zb2xpZGF0ZWQtc2FuY3Rpb25zLWxpc3QtZGF0YS1maWxlc2RkAg8PDxYCHwEFmQFodHRwczovL2hvbWUudHJlYXN1cnkuZ292L3BvbGljeS1pc3N1ZXMvZmluYW5jaWFsLXNhbmN0aW9ucy9zcGVjaWFsbHktZGVzaWduYXRlZC1uYXRpb25hbHMtbGlzdC1zZG4tbGlzdC9wcm9ncmFtLXRhZy1kZWZpbml0aW9ucy1mb3Itb2ZhYy1zYW5jdGlvbnMtbGlzdHNkZAIRD2QWBAIFD2QWCAIDDxAPFgQeDURhdGFUZXh0RmllbGQFB3NkblR5cGUeC18hRGF0YUJvdW5kZ2QQFQUDQWxsCEFpcmNyYWZ0BkVudGl0eQpJbmRpdmlkdWFsBlZlc3NlbBUFAAhBaXJjcmFmdAZFbnRpdHkKSW5kaXZpZHVhbAZWZXNzZWwUKwMFZ2dnZ2dkZAIbDxAPFgQfAgUKc2RuUHJvZ3JhbR8DZ2QQFUQDQWxsCzU2MS1SZWxhdGVkB0JBTEtBTlMHQkVMQVJVUwdCVVJVTkRJDUNBQVRTQSAtIElSQU4PQ0FBVFNBIC0gUlVTU0lBA0NBUgRDVUJBBkNZQkVSMgZEQVJGVVIERFBSSwVEUFJLMgVEUFJLMwVEUFJLNAtEUFJLLU5LU1BFQQdEUkNPTkdPEEVMRUNUSU9OLUVPMTM4NDgGRlNFLUlSBkZTRS1TWQNGVE8GR0xPTUFHBkhJRlBBQQpISy1FTzEzOTM2B0hSSVQtSVIHSFJJVC1TWQxJQ0NQLUVPMTM5MjgESUZDQQRJRlNSBElSQU4QSVJBTi1DT04tQVJNUy1FTwxJUkFOLUVPMTM4NDYMSVJBTi1FTzEzODcxDElSQU4tRU8xMzg3NgxJUkFOLUVPMTM5MDIHSVJBTi1IUghJUkFOLVRSQQVJUkFRMgVJUkFRMwRJUkdDA0lTQQdMRUJBTk9OBkxJQllBMgZMSUJZQTMGTUFHTklUDE1BTEktRU8xMzg4MglOSUNBUkFHVUEPTklDQVJBR1VBLU5IUkFBBU5QV01EBk5TLVBMQwRTREdUBFNETlQFU0ROVEsHU09NQUxJQQtTT1VUSCBTVURBTgVTWVJJQQxTWVJJQS1DQUVTQVINU1lSSUEtRU8xMzg5NANUQ08PVUtSQUlORS1FTzEzNjYwD1VLUkFJTkUtRU8xMzY2MQ9VS1JBSU5FLUVPMTM2NjIPVUtSQUlORS1FTzEzNjg1CVZFTkVaVUVMQRFWRU5FWlVFTEEtRU8xMzg1MBFWRU5FWlVFTEEtRU8xMzg4NAVZRU1FTghaSU1CQUJXRRVEAAs1NjEtUmVsYXRlZAdCQUxLQU5TB0JFTEFSVVMHQlVSVU5ESQ1DQUFUU0EgLSBJUkFOD0NBQVRTQSAtIFJVU1NJQQNDQVIEQ1VCQQZDWUJFUjIGREFSRlVSBERQUksFRFBSSzIFRFBSSzMFRFBSSzQLRFBSSy1OS1NQRUEHRFJDT05HTxBFTEVDVElPTi1FTzEzODQ4BkZTRS1JUgZGU0UtU1kDRlRPBkdMT01BRwZISUZQQUEKSEstRU8xMzkzNgdIUklULUlSB0hSSVQtU1kMSUNDUC1FTzEzOTI4BElGQ0EESUZTUgRJUkFOEElSQU4tQ09OLUFSTVMtRU8MSVJBTi1FTzEzODQ2DElSQU4tRU8xMzg3MQxJUkFOLUVPMTM4NzYMSVJBTi1FTzEzOTAyB0lSQU4tSFIISVJBTi1UUkEFSVJBUTIFSVJBUTMESVJHQwNJU0EHTEVCQU5PTgZMSUJZQTIGTElCWUEzBk1BR05JVAxNQUxJLUVPMTM4ODIJTklDQVJBR1VBD05JQ0FSQUdVQS1OSFJBQQVOUFdNRAZOUy1QTEMEU0RHVARTRE5UBVNETlRLB1NPTUFMSUELU09VVEggU1VEQU4FU1lSSUEMU1lSSUEtQ0FFU0FSDVNZUklBLUVPMTM4OTQDVENPD1VLUkFJTkUtRU8xMzY2MA9VS1JBSU5FLUVPMTM2NjEPVUtSQUlORS1FTzEzNjYyD1VLUkFJTkUtRU8xMzY4NQlWRU5FWlVFTEERVkVORVpVRUxBLUVPMTM4NTARVkVORVpVRUxBLUVPMTM4ODQFWUVNRU4IWklNQkFCV0UUKwNEZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dkZAIhDxAPFgQfAgUJY291bnRyaWVzHwNnZBAVqQEDQWxsC0FmZ2hhbmlzdGFuB0FsYmFuaWEHQWxnZXJpYQZBbmdvbGEJQXJnZW50aW5hB0FybWVuaWEFQXJ1YmEJQXVzdHJhbGlhB0F1c3RyaWEKQXplcmJhaWphbgxCYWhhbWFzLCBUaGUHQmFocmFpbgpCYW5nbGFkZXNoCEJhcmJhZG9zB0JlbGFydXMHQmVsZ2l1bQZCZWxpemUFQmVuaW4HQm9saXZpYRZCb3NuaWEgYW5kIEhlcnplZ292aW5hBkJyYXppbAhCdWxnYXJpYQxCdXJraW5hIEZhc28FQnVybWEHQnVydW5kaQhDYW1ib2RpYQZDYW5hZGEOQ2F5bWFuIElzbGFuZHMYQ2VudHJhbCBBZnJpY2FuIFJlcHVibGljBUNoaWxlBUNoaW5hCENvbG9tYmlhB0NvbW9yb3MhQ29uZ28sIERlbW9jcmF0aWMgUmVwdWJsaWMgb2YgdGhlFkNvbmdvLCBSZXB1YmxpYyBvZiB0aGUKQ29zdGEgUmljYQ1Db3RlIGQgSXZvaXJlB0Nyb2F0aWEEQ3ViYQZDeXBydXMOQ3plY2ggUmVwdWJsaWMHRGVubWFyawhEb21pbmljYRJEb21pbmljYW4gUmVwdWJsaWMHRWN1YWRvcgVFZ3lwdAtFbCBTYWx2YWRvchFFcXVhdG9yaWFsIEd1aW5lYQdFcml0cmVhCEV0aGlvcGlhB0ZpbmxhbmQGRnJhbmNlB0dlb3JnaWEHR2VybWFueQVHaGFuYQlHaWJyYWx0YXIGR3JlZWNlCUd1YXRlbWFsYQhHdWVybnNleQZHdXlhbmEFSGFpdGkISG9uZHVyYXMJSG9uZyBLb25nBUluZGlhCUluZG9uZXNpYQRJcmFuBElyYXEHSXJlbGFuZAZJc3JhZWwFSXRhbHkHSmFtYWljYQVKYXBhbgZKZXJzZXkGSm9yZGFuCkthemFraHN0YW4FS2VueWEMS29yZWEsIE5vcnRoDEtvcmVhLCBTb3V0aAZLb3Nvdm8GS3V3YWl0Ckt5cmd5enN0YW4ETGFvcwZMYXR2aWEHTGViYW5vbgdMaWJlcmlhBUxpYnlhDUxpZWNodGVuc3RlaW4KTHV4ZW1ib3VyZwhNYWxheXNpYQhNYWxkaXZlcwRNYWxpBU1hbHRhEE1hcnNoYWxsIElzbGFuZHMKTWF1cml0YW5pYQZNZXhpY28HTW9sZG92YQhNb25nb2xpYQpNb250ZW5lZ3JvB01vcm9jY28KTW96YW1iaXF1ZQdOYW1pYmlhC05ldGhlcmxhbmRzFE5ldGhlcmxhbmRzIEFudGlsbGVzC05ldyBaZWFsYW5kCU5pY2FyYWd1YQVOaWdlcgdOaWdlcmlhBk5vcndheQRPbWFuCFBha2lzdGFuC1BhbGVzdGluaWFuBlBhbmFtYQhQYXJhZ3VheQRQZXJ1C1BoaWxpcHBpbmVzBlBvbGFuZAVRYXRhcg5SZWdpb246IENyaW1lYQxSZWdpb246IEdhemETUmVnaW9uOiBLYWZpYSBLaW5naRVSZWdpb246IE5vcnRoZXJuIE1hbGkHUm9tYW5pYQZSdXNzaWEGUndhbmRhFVNhaW50IEtpdHRzIGFuZCBOZXZpcyBTYWludCBWaW5jZW50IGFuZCB0aGUgR3JlbmFkaW5lcwVTYW1vYQxTYXVkaSBBcmFiaWEHU2VuZWdhbAZTZXJiaWEKU2V5Y2hlbGxlcwxTaWVycmEgTGVvbmUJU2luZ2Fwb3JlCFNsb3Zha2lhCFNsb3ZlbmlhB1NvbWFsaWEMU291dGggQWZyaWNhC1NvdXRoIFN1ZGFuBVNwYWluCVNyaSBMYW5rYQVTdWRhbgZTd2VkZW4LU3dpdHplcmxhbmQFU3lyaWEGVGFpd2FuClRhamlraXN0YW4IVGFuemFuaWEIVGhhaWxhbmQKVGhlIEdhbWJpYRNUcmluaWRhZCBhbmQgVG9iYWdvB1R1bmlzaWEGVHVya2V5DFR1cmttZW5pc3RhbgZVZ2FuZGEHVWtyYWluZQx1bmRldGVybWluZWQUVW5pdGVkIEFyYWIgRW1pcmF0ZXMOVW5pdGVkIEtpbmdkb20NVW5pdGVkIFN0YXRlcwdVcnVndWF5ClV6YmVraXN0YW4HVmFudWF0dQlWZW5lenVlbGEHVmlldG5hbRdWaXJnaW4gSXNsYW5kcywgQnJpdGlzaAlXZXN0IEJhbmsFWWVtZW4IWmltYmFid2UVqQEAC0FmZ2hhbmlzdGFuB0FsYmFuaWEHQWxnZXJpYQZBbmdvbGEJQXJnZW50aW5hB0FybWVuaWEFQXJ1YmEJQXVzdHJhbGlhB0F1c3RyaWEKQXplcmJhaWphbgxCYWhhbWFzLCBUaGUHQmFocmFpbgpCYW5nbGFkZXNoCEJhcmJhZG9zB0JlbGFydXMHQmVsZ2l1bQZCZWxpemUFQmVuaW4HQm9saXZpYRZCb3NuaWEgYW5kIEhlcnplZ292aW5hBkJyYXppbAhCdWxnYXJpYQxCdXJraW5hIEZhc28FQnVybWEHQnVydW5kaQhDYW1ib2RpYQZDYW5hZGEOQ2F5bWFuIElzbGFuZHMYQ2VudHJhbCBBZnJpY2FuIFJlcHVibGljBUNoaWxlBUNoaW5hCENvbG9tYmlhB0NvbW9yb3MhQ29uZ28sIERlbW9jcmF0aWMgUmVwdWJsaWMgb2YgdGhlFkNvbmdvLCBSZXB1YmxpYyBvZiB0aGUKQ29zdGEgUmljYQ1Db3RlIGQgSXZvaXJlB0Nyb2F0aWEEQ3ViYQZDeXBydXMOQ3plY2ggUmVwdWJsaWMHRGVubWFyawhEb21pbmljYRJEb21pbmljYW4gUmVwdWJsaWMHRWN1YWRvcgVFZ3lwdAtFbCBTYWx2YWRvchFFcXVhdG9yaWFsIEd1aW5lYQdFcml0cmVhCEV0aGlvcGlhB0ZpbmxhbmQGRnJhbmNlB0dlb3JnaWEHR2VybWFueQVHaGFuYQlHaWJyYWx0YXIGR3JlZWNlCUd1YXRlbWFsYQhHdWVybnNleQZHdXlhbmEFSGFpdGkISG9uZHVyYXMJSG9uZyBLb25nBUluZGlhCUluZG9uZXNpYQRJcmFuBElyYXEHSXJlbGFuZAZJc3JhZWwFSXRhbHkHSmFtYWljYQVKYXBhbgZKZXJzZXkGSm9yZGFuCkthemFraHN0YW4FS2VueWEMS29yZWEsIE5vcnRoDEtvcmVhLCBTb3V0aAZLb3Nvdm8GS3V3YWl0Ckt5cmd5enN0YW4ETGFvcwZMYXR2aWEHTGViYW5vbgdMaWJlcmlhBUxpYnlhDUxpZWNodGVuc3RlaW4KTHV4ZW1ib3VyZwhNYWxheXNpYQhNYWxkaXZlcwRNYWxpBU1hbHRhEE1hcnNoYWxsIElzbGFuZHMKTWF1cml0YW5pYQZNZXhpY28HTW9sZG92YQhNb25nb2xpYQpNb250ZW5lZ3JvB01vcm9jY28KTW96YW1iaXF1ZQdOYW1pYmlhC05ldGhlcmxhbmRzFE5ldGhlcmxhbmRzIEFudGlsbGVzC05ldyBaZWFsYW5kCU5pY2FyYWd1YQVOaWdlcgdOaWdlcmlhBk5vcndheQRPbWFuCFBha2lzdGFuC1BhbGVzdGluaWFuBlBhbmFtYQhQYXJhZ3VheQRQZXJ1C1BoaWxpcHBpbmVzBlBvbGFuZAVRYXRhcg5SZWdpb246IENyaW1lYQxSZWdpb246IEdhemETUmVnaW9uOiBLYWZpYSBLaW5naRVSZWdpb246IE5vcnRoZXJuIE1hbGkHUm9tYW5pYQZSdXNzaWEGUndhbmRhFVNhaW50IEtpdHRzIGFuZCBOZXZpcyBTYWludCBWaW5jZW50IGFuZCB0aGUgR3JlbmFkaW5lcwVTYW1vYQxTYXVkaSBBcmFiaWEHU2VuZWdhbAZTZXJiaWEKU2V5Y2hlbGxlcwxTaWVycmEgTGVvbmUJU2luZ2Fwb3JlCFNsb3Zha2lhCFNsb3ZlbmlhB1NvbWFsaWEMU291dGggQWZyaWNhC1NvdXRoIFN1ZGFuBVNwYWluCVNyaSBMYW5rYQVTdWRhbgZTd2VkZW4LU3dpdHplcmxhbmQFU3lyaWEGVGFpd2FuClRhamlraXN0YW4IVGFuemFuaWEIVGhhaWxhbmQKVGhlIEdhbWJpYRNUcmluaWRhZCBhbmQgVG9iYWdvB1R1bmlzaWEGVHVya2V5DFR1cmttZW5pc3RhbgZVZ2FuZGEHVWtyYWluZQx1bmRldGVybWluZWQUVW5pdGVkIEFyYWIgRW1pcmF0ZXMOVW5pdGVkIEtpbmdkb20NVW5pdGVkIFN0YXRlcwdVcnVndWF5ClV6YmVraXN0YW4HVmFudWF0dQlWZW5lenVlbGEHVmlldG5hbRdWaXJnaW4gSXNsYW5kcywgQnJpdGlzaAlXZXN0IEJhbmsFWWVtZW4IWmltYmFid2UUKwOpAWdnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dkZAIjDxAPFgQfAgUIbGlzdFR5cGUfA2dkEBUDA0FsbAdOb24tU0ROA1NEThUDAAdOb24tU0ROA1NEThQrAwNnZ2dkZAIJD2QWAgIFDzwrABECARAWABYAFgAMFCsAAGQCEw8PFgIfAAUvU0ROIExpc3QgbGFzdCB1cGRhdGVkIG9uOiAxMC8yNi8yMDIwIDE6MTI6NTkgUE1kZAIVDw8WAh8ABTNOb24tU0ROIExpc3QgbGFzdCB1cGRhdGVkIG9uOiAzLzE3LzIwMjAgMTA6NTM6MjcgQU1kZBgCBR5fX0NvbnRyb2xzUmVxdWlyZVBvc3RCYWNrS2V5X18WAwUeY3RsMDAkTWFpbkNvbnRlbnQkSW1hZ2VCdXR0b24yBR1jdGwwMCRNYWluQ29udGVudCRsc3RQcm9ncmFtcwUeY3RsMDAkTWFpbkNvbnRlbnQkSW1hZ2VCdXR0b24xBSFjdGwwMCRNYWluQ29udGVudCRndlNlYXJjaFJlc3VsdHMPZ2TS70G7eApDyKotqpOLV4XnWalULmcC4r0TtHI0L4aiFQ==',
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
            linkofac=link.find(id="btnDetails")
            actialid=0
            if linkofac is not None:
                datalink = linkofac.get('href').split(",")[4]
                actialid= datalink.split("=")[1].replace('"','')
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


