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
import jaro
import json
import csv
import os


comparationscon = sqlite3.connect('comparations.db',check_same_thread=False)

maxvalue = 75
connStr = (r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ="+os.path.join(settings.BASE_DIR, 'GFUX_DWH.accdb')+";")

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
        '__VIEWSTATE':'/wEPDwUJMzIwMTQ1Njg3D2QWAmYPZBYCAgMPZBYQAgUPDxYCHgRUZXh0BZ4OU3BlY2lhbGx5IERlc2lnbmF0ZWQgTmF0aW9uYWxzIGFuZCBCbG9ja2VkIFBlcnNvbnMgbGlzdCAoIlNETiBMaXN0IikgYW5kIGFsbCBvdGhlciBzYW5jdGlvbnMgbGlzdHMgYWRtaW5pc3RlcmVkIGJ5IE9GQUMsIGluY2x1ZGluZyB0aGUgRm9yZWlnbiBTYW5jdGlvbnMgRXZhZGVycyBMaXN0LCB0aGUgTm9uLVNETiBJcmFuIFNhbmN0aW9ucyBBY3QgTGlzdCwgdGhlIFNlY3RvcmFsIFNhbmN0aW9ucyBJZGVudGlmaWNhdGlvbnMgTGlzdCwgdGhlIExpc3Qgb2YgRm9yZWlnbiBGaW5hbmNpYWwgSW5zdGl0dXRpb25zIFN1YmplY3QgdG8gQ29ycmVzcG9uZGVudCBBY2NvdW50IG9yIFBheWFibGUtVGhyb3VnaCBBY2NvdW50IFNhbmN0aW9ucyBhbmQgdGhlIE5vbi1TRE4gUGFsZXN0aW5pYW4gTGVnaXNsYXRpdmUgQ291bmNpbCBMaXN0LiBHaXZlbiB0aGUgbnVtYmVyIG9mIGxpc3RzIHRoYXQgbm93IHJlc2lkZSBpbiB0aGUgU2FuY3Rpb25zIExpc3QgU2VhcmNoIHRvb2wsIGl0IGlzIHN0cm9uZ2x5IHJlY29tbWVuZGVkIHRoYXQgdXNlcnMgcGF5IGNsb3NlIGF0dGVudGlvbiB0byB0aGUgcHJvZ3JhbSBjb2RlcyBhc3NvY2lhdGVkIHdpdGggZWFjaCByZXR1cm5lZCByZWNvcmQuIFRoZXNlIHByb2dyYW0gY29kZXMgaW5kaWNhdGUgaG93IGEgdHJ1ZSBoaXQgb24gYSByZXR1cm5lZCB2YWx1ZSBzaG91bGQgYmUgdHJlYXRlZC4gVGhlIFNhbmN0aW9ucyBMaXN0IFNlYXJjaCB0b29sIHVzZXMgYXBwcm94aW1hdGUgc3RyaW5nIG1hdGNoaW5nIHRvIGlkZW50aWZ5IHBvc3NpYmxlIG1hdGNoZXMgYmV0d2VlbiB3b3JkIG9yIGNoYXJhY3RlciBzdHJpbmdzIGFzIGVudGVyZWQgaW50byBTYW5jdGlvbnMgTGlzdCBTZWFyY2gsIGFuZCBhbnkgbmFtZSBvciBuYW1lIGNvbXBvbmVudCBhcyBpdCBhcHBlYXJzIG9uIHRoZSBTRE4gTGlzdCBhbmQvb3IgdGhlIHZhcmlvdXMgb3RoZXIgc2FuY3Rpb25zIGxpc3RzLiBTYW5jdGlvbnMgTGlzdCBTZWFyY2ggaGFzIGEgc2xpZGVyLWJhciB0aGF0IG1heSBiZSB1c2VkIHRvIHNldCBhIHRocmVzaG9sZCAoaS5lLiwgYSBjb25maWRlbmNlIHJhdGluZykgZm9yIHRoZSBjbG9zZW5lc3Mgb2YgYW55IHBvdGVudGlhbCBtYXRjaCByZXR1cm5lZCBhcyBhIHJlc3VsdCBvZiBhIHVzZXIncyBzZWFyY2guIFNhbmN0aW9ucyBMaXN0IFNlYXJjaCB3aWxsIGRldGVjdCBjZXJ0YWluIG1pc3NwZWxsaW5ncyBvciBvdGhlciBpbmNvcnJlY3RseSBlbnRlcmVkIHRleHQsIGFuZCB3aWxsIHJldHVybiBuZWFyLCBvciBwcm94aW1hdGUsIG1hdGNoZXMsIGJhc2VkIG9uIHRoZSBjb25maWRlbmNlIHJhdGluZyBzZXQgYnkgdGhlIHVzZXIgdmlhIHRoZSBzbGlkZXItYmFyLiBPRkFDIGRvZXMgbm90IHByb3ZpZGUgcmVjb21tZW5kYXRpb25zIHdpdGggcmVnYXJkIHRvIHRoZSBhcHByb3ByaWF0ZW5lc3Mgb2YgYW55IHNwZWNpZmljIGNvbmZpZGVuY2UgcmF0aW5nLiBTYW5jdGlvbnMgTGlzdCBTZWFyY2ggaXMgb25lIHRvb2wgb2ZmZXJlZCB0byBhc3Npc3QgdXNlcnMgaW4gdXRpbGl6aW5nIHRoZSBTRE4gTGlzdCBhbmQvb3IgdGhlIHZhcmlvdXMgb3RoZXIgc2FuY3Rpb25zIGxpc3RzOyB1c2Ugb2YgU2FuY3Rpb25zIExpc3QgU2VhcmNoIGlzIG5vdCBhIHN1YnN0aXR1dGUgZm9yIHVuZGVydGFraW5nIGFwcHJvcHJpYXRlIGR1ZSBkaWxpZ2VuY2UuIFRoZSB1c2Ugb2YgU2FuY3Rpb25zIExpc3QgU2VhcmNoIGRvZXMgbm90IGxpbWl0IGFueSBjcmltaW5hbCBvciBjaXZpbCBsaWFiaWxpdHkgZm9yIGFueSBhY3QgdW5kZXJ0YWtlbiBhcyBhIHJlc3VsdCBvZiwgb3IgaW4gcmVsaWFuY2Ugb24sIHN1Y2ggdXNlLmRkAgcPDxYCHgtOYXZpZ2F0ZVVybAV5aHR0cHM6Ly9ob21lLnRyZWFzdXJ5Lmdvdi9wb2xpY3ktaXNzdWVzL2ZpbmFuY2lhbC1zYW5jdGlvbnMvc3BlY2lhbGx5LWRlc2lnbmF0ZWQtbmF0aW9uYWxzLWxpc3QtZGF0YS1mb3JtYXRzLWRhdGEtc2NoZW1hc2RkAgkPDxYCHwEFa2h0dHBzOi8vaG9tZS50cmVhc3VyeS5nb3YvcG9saWN5LWlzc3Vlcy9vZmZpY2Utb2YtZm9yZWlnbi1hc3NldHMtY29udHJvbC1zYW5jdGlvbnMtcHJvZ3JhbXMtYW5kLWluZm9ybWF0aW9uZGQCCw8PFgIfAQViaHR0cHM6Ly9ob21lLnRyZWFzdXJ5Lmdvdi9wb2xpY3ktaXNzdWVzL2ZpbmFuY2lhbC1zYW5jdGlvbnMvY29uc29saWRhdGVkLXNhbmN0aW9ucy1saXN0LWRhdGEtZmlsZXNkZAINDw8WAh8BBZkBaHR0cHM6Ly9ob21lLnRyZWFzdXJ5Lmdvdi9wb2xpY3ktaXNzdWVzL2ZpbmFuY2lhbC1zYW5jdGlvbnMvc3BlY2lhbGx5LWRlc2lnbmF0ZWQtbmF0aW9uYWxzLWxpc3Qtc2RuLWxpc3QvcHJvZ3JhbS10YWctZGVmaW5pdGlvbnMtZm9yLW9mYWMtc2FuY3Rpb25zLWxpc3RzZGQCDw9kFgQCBQ9kFggCAw8QDxYEHg1EYXRhVGV4dEZpZWxkBQdzZG5UeXBlHgtfIURhdGFCb3VuZGdkEBUFA0FsbAhBaXJjcmFmdAZFbnRpdHkKSW5kaXZpZHVhbAZWZXNzZWwVBQAIQWlyY3JhZnQGRW50aXR5CkluZGl2aWR1YWwGVmVzc2VsFCsDBWdnZ2dnZGQCGw8QDxYEHwIFCnNkblByb2dyYW0fA2dkEBVEA0FsbAs1NjEtUmVsYXRlZAdCQUxLQU5TB0JFTEFSVVMHQlVSVU5ESQ1DQUFUU0EgLSBJUkFOD0NBQVRTQSAtIFJVU1NJQQNDQVIEQ1VCQQZDWUJFUjIGREFSRlVSBERQUksFRFBSSzIFRFBSSzMFRFBSSzQLRFBSSy1OS1NQRUEHRFJDT05HTxBFTEVDVElPTi1FTzEzODQ4BkZTRS1JUgZGU0UtU1kDRlRPBkdMT01BRwZISUZQQUEKSEstRU8xMzkzNgdIUklULUlSB0hSSVQtU1kMSUNDUC1FTzEzOTI4BElGQ0EESUZTUgRJUkFOEElSQU4tQ09OLUFSTVMtRU8MSVJBTi1FTzEzODQ2DElSQU4tRU8xMzg3MQxJUkFOLUVPMTM4NzYMSVJBTi1FTzEzOTAyB0lSQU4tSFIISVJBTi1UUkEFSVJBUTIFSVJBUTMESVJHQwNJU0EHTEVCQU5PTgZMSUJZQTIGTElCWUEzBk1BR05JVAxNQUxJLUVPMTM4ODIJTklDQVJBR1VBD05JQ0FSQUdVQS1OSFJBQQVOUFdNRAZOUy1QTEMEU0RHVARTRE5UBVNETlRLB1NPTUFMSUELU09VVEggU1VEQU4FU1lSSUEMU1lSSUEtQ0FFU0FSDVNZUklBLUVPMTM4OTQDVENPD1VLUkFJTkUtRU8xMzY2MA9VS1JBSU5FLUVPMTM2NjEPVUtSQUlORS1FTzEzNjYyD1VLUkFJTkUtRU8xMzY4NQlWRU5FWlVFTEERVkVORVpVRUxBLUVPMTM4NTARVkVORVpVRUxBLUVPMTM4ODQFWUVNRU4IWklNQkFCV0UVRAALNTYxLVJlbGF0ZWQHQkFMS0FOUwdCRUxBUlVTB0JVUlVOREkNQ0FBVFNBIC0gSVJBTg9DQUFUU0EgLSBSVVNTSUEDQ0FSBENVQkEGQ1lCRVIyBkRBUkZVUgREUFJLBURQUksyBURQUkszBURQUks0C0RQUkstTktTUEVBB0RSQ09OR08QRUxFQ1RJT04tRU8xMzg0OAZGU0UtSVIGRlNFLVNZA0ZUTwZHTE9NQUcGSElGUEFBCkhLLUVPMTM5MzYHSFJJVC1JUgdIUklULVNZDElDQ1AtRU8xMzkyOARJRkNBBElGU1IESVJBThBJUkFOLUNPTi1BUk1TLUVPDElSQU4tRU8xMzg0NgxJUkFOLUVPMTM4NzEMSVJBTi1FTzEzODc2DElSQU4tRU8xMzkwMgdJUkFOLUhSCElSQU4tVFJBBUlSQVEyBUlSQVEzBElSR0MDSVNBB0xFQkFOT04GTElCWUEyBkxJQllBMwZNQUdOSVQMTUFMSS1FTzEzODgyCU5JQ0FSQUdVQQ9OSUNBUkFHVUEtTkhSQUEFTlBXTUQGTlMtUExDBFNER1QEU0ROVAVTRE5USwdTT01BTElBC1NPVVRIIFNVREFOBVNZUklBDFNZUklBLUNBRVNBUg1TWVJJQS1FTzEzODk0A1RDTw9VS1JBSU5FLUVPMTM2NjAPVUtSQUlORS1FTzEzNjYxD1VLUkFJTkUtRU8xMzY2Mg9VS1JBSU5FLUVPMTM2ODUJVkVORVpVRUxBEVZFTkVaVUVMQS1FTzEzODUwEVZFTkVaVUVMQS1FTzEzODg0BVlFTUVOCFpJTUJBQldFFCsDRGdnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZGQCIQ8QDxYEHwIFCWNvdW50cmllcx8DZ2QQFakBA0FsbAtBZmdoYW5pc3RhbgdBbGJhbmlhB0FsZ2VyaWEGQW5nb2xhCUFyZ2VudGluYQdBcm1lbmlhBUFydWJhCUF1c3RyYWxpYQdBdXN0cmlhCkF6ZXJiYWlqYW4MQmFoYW1hcywgVGhlB0JhaHJhaW4KQmFuZ2xhZGVzaAhCYXJiYWRvcwdCZWxhcnVzB0JlbGdpdW0GQmVsaXplBUJlbmluB0JvbGl2aWEWQm9zbmlhIGFuZCBIZXJ6ZWdvdmluYQZCcmF6aWwIQnVsZ2FyaWEMQnVya2luYSBGYXNvBUJ1cm1hB0J1cnVuZGkIQ2FtYm9kaWEGQ2FuYWRhDkNheW1hbiBJc2xhbmRzGENlbnRyYWwgQWZyaWNhbiBSZXB1YmxpYwVDaGlsZQVDaGluYQhDb2xvbWJpYQdDb21vcm9zIUNvbmdvLCBEZW1vY3JhdGljIFJlcHVibGljIG9mIHRoZRZDb25nbywgUmVwdWJsaWMgb2YgdGhlCkNvc3RhIFJpY2ENQ290ZSBkIEl2b2lyZQdDcm9hdGlhBEN1YmEGQ3lwcnVzDkN6ZWNoIFJlcHVibGljB0Rlbm1hcmsIRG9taW5pY2ESRG9taW5pY2FuIFJlcHVibGljB0VjdWFkb3IFRWd5cHQLRWwgU2FsdmFkb3IRRXF1YXRvcmlhbCBHdWluZWEHRXJpdHJlYQhFdGhpb3BpYQdGaW5sYW5kBkZyYW5jZQdHZW9yZ2lhB0dlcm1hbnkFR2hhbmEJR2licmFsdGFyBkdyZWVjZQlHdWF0ZW1hbGEIR3Vlcm5zZXkGR3V5YW5hBUhhaXRpCEhvbmR1cmFzCUhvbmcgS29uZwVJbmRpYQlJbmRvbmVzaWEESXJhbgRJcmFxB0lyZWxhbmQGSXNyYWVsBUl0YWx5B0phbWFpY2EFSmFwYW4GSmVyc2V5BkpvcmRhbgpLYXpha2hzdGFuBUtlbnlhDEtvcmVhLCBOb3J0aAxLb3JlYSwgU291dGgGS29zb3ZvBkt1d2FpdApLeXJneXpzdGFuBExhb3MGTGF0dmlhB0xlYmFub24HTGliZXJpYQVMaWJ5YQ1MaWVjaHRlbnN0ZWluCkx1eGVtYm91cmcITWFsYXlzaWEITWFsZGl2ZXMETWFsaQVNYWx0YRBNYXJzaGFsbCBJc2xhbmRzCk1hdXJpdGFuaWEGTWV4aWNvB01vbGRvdmEITW9uZ29saWEKTW9udGVuZWdybwdNb3JvY2NvCk1vemFtYmlxdWUHTmFtaWJpYQtOZXRoZXJsYW5kcxROZXRoZXJsYW5kcyBBbnRpbGxlcwtOZXcgWmVhbGFuZAlOaWNhcmFndWEFTmlnZXIHTmlnZXJpYQZOb3J3YXkET21hbghQYWtpc3RhbgtQYWxlc3RpbmlhbgZQYW5hbWEIUGFyYWd1YXkEUGVydQtQaGlsaXBwaW5lcwZQb2xhbmQFUWF0YXIOUmVnaW9uOiBDcmltZWEMUmVnaW9uOiBHYXphE1JlZ2lvbjogS2FmaWEgS2luZ2kVUmVnaW9uOiBOb3J0aGVybiBNYWxpB1JvbWFuaWEGUnVzc2lhBlJ3YW5kYRVTYWludCBLaXR0cyBhbmQgTmV2aXMgU2FpbnQgVmluY2VudCBhbmQgdGhlIEdyZW5hZGluZXMFU2Ftb2EMU2F1ZGkgQXJhYmlhB1NlbmVnYWwGU2VyYmlhClNleWNoZWxsZXMMU2llcnJhIExlb25lCVNpbmdhcG9yZQhTbG92YWtpYQhTbG92ZW5pYQdTb21hbGlhDFNvdXRoIEFmcmljYQtTb3V0aCBTdWRhbgVTcGFpbglTcmkgTGFua2EFU3VkYW4GU3dlZGVuC1N3aXR6ZXJsYW5kBVN5cmlhBlRhaXdhbgpUYWppa2lzdGFuCFRhbnphbmlhCFRoYWlsYW5kClRoZSBHYW1iaWETVHJpbmlkYWQgYW5kIFRvYmFnbwdUdW5pc2lhBlR1cmtleQxUdXJrbWVuaXN0YW4GVWdhbmRhB1VrcmFpbmUMdW5kZXRlcm1pbmVkFFVuaXRlZCBBcmFiIEVtaXJhdGVzDlVuaXRlZCBLaW5nZG9tDVVuaXRlZCBTdGF0ZXMHVXJ1Z3VheQpVemJla2lzdGFuB1ZhbnVhdHUJVmVuZXp1ZWxhB1ZpZXRuYW0XVmlyZ2luIElzbGFuZHMsIEJyaXRpc2gJV2VzdCBCYW5rBVllbWVuCFppbWJhYndlFakBAAtBZmdoYW5pc3RhbgdBbGJhbmlhB0FsZ2VyaWEGQW5nb2xhCUFyZ2VudGluYQdBcm1lbmlhBUFydWJhCUF1c3RyYWxpYQdBdXN0cmlhCkF6ZXJiYWlqYW4MQmFoYW1hcywgVGhlB0JhaHJhaW4KQmFuZ2xhZGVzaAhCYXJiYWRvcwdCZWxhcnVzB0JlbGdpdW0GQmVsaXplBUJlbmluB0JvbGl2aWEWQm9zbmlhIGFuZCBIZXJ6ZWdvdmluYQZCcmF6aWwIQnVsZ2FyaWEMQnVya2luYSBGYXNvBUJ1cm1hB0J1cnVuZGkIQ2FtYm9kaWEGQ2FuYWRhDkNheW1hbiBJc2xhbmRzGENlbnRyYWwgQWZyaWNhbiBSZXB1YmxpYwVDaGlsZQVDaGluYQhDb2xvbWJpYQdDb21vcm9zIUNvbmdvLCBEZW1vY3JhdGljIFJlcHVibGljIG9mIHRoZRZDb25nbywgUmVwdWJsaWMgb2YgdGhlCkNvc3RhIFJpY2ENQ290ZSBkIEl2b2lyZQdDcm9hdGlhBEN1YmEGQ3lwcnVzDkN6ZWNoIFJlcHVibGljB0Rlbm1hcmsIRG9taW5pY2ESRG9taW5pY2FuIFJlcHVibGljB0VjdWFkb3IFRWd5cHQLRWwgU2FsdmFkb3IRRXF1YXRvcmlhbCBHdWluZWEHRXJpdHJlYQhFdGhpb3BpYQdGaW5sYW5kBkZyYW5jZQdHZW9yZ2lhB0dlcm1hbnkFR2hhbmEJR2licmFsdGFyBkdyZWVjZQlHdWF0ZW1hbGEIR3Vlcm5zZXkGR3V5YW5hBUhhaXRpCEhvbmR1cmFzCUhvbmcgS29uZwVJbmRpYQlJbmRvbmVzaWEESXJhbgRJcmFxB0lyZWxhbmQGSXNyYWVsBUl0YWx5B0phbWFpY2EFSmFwYW4GSmVyc2V5BkpvcmRhbgpLYXpha2hzdGFuBUtlbnlhDEtvcmVhLCBOb3J0aAxLb3JlYSwgU291dGgGS29zb3ZvBkt1d2FpdApLeXJneXpzdGFuBExhb3MGTGF0dmlhB0xlYmFub24HTGliZXJpYQVMaWJ5YQ1MaWVjaHRlbnN0ZWluCkx1eGVtYm91cmcITWFsYXlzaWEITWFsZGl2ZXMETWFsaQVNYWx0YRBNYXJzaGFsbCBJc2xhbmRzCk1hdXJpdGFuaWEGTWV4aWNvB01vbGRvdmEITW9uZ29saWEKTW9udGVuZWdybwdNb3JvY2NvCk1vemFtYmlxdWUHTmFtaWJpYQtOZXRoZXJsYW5kcxROZXRoZXJsYW5kcyBBbnRpbGxlcwtOZXcgWmVhbGFuZAlOaWNhcmFndWEFTmlnZXIHTmlnZXJpYQZOb3J3YXkET21hbghQYWtpc3RhbgtQYWxlc3RpbmlhbgZQYW5hbWEIUGFyYWd1YXkEUGVydQtQaGlsaXBwaW5lcwZQb2xhbmQFUWF0YXIOUmVnaW9uOiBDcmltZWEMUmVnaW9uOiBHYXphE1JlZ2lvbjogS2FmaWEgS2luZ2kVUmVnaW9uOiBOb3J0aGVybiBNYWxpB1JvbWFuaWEGUnVzc2lhBlJ3YW5kYRVTYWludCBLaXR0cyBhbmQgTmV2aXMgU2FpbnQgVmluY2VudCBhbmQgdGhlIEdyZW5hZGluZXMFU2Ftb2EMU2F1ZGkgQXJhYmlhB1NlbmVnYWwGU2VyYmlhClNleWNoZWxsZXMMU2llcnJhIExlb25lCVNpbmdhcG9yZQhTbG92YWtpYQhTbG92ZW5pYQdTb21hbGlhDFNvdXRoIEFmcmljYQtTb3V0aCBTdWRhbgVTcGFpbglTcmkgTGFua2EFU3VkYW4GU3dlZGVuC1N3aXR6ZXJsYW5kBVN5cmlhBlRhaXdhbgpUYWppa2lzdGFuCFRhbnphbmlhCFRoYWlsYW5kClRoZSBHYW1iaWETVHJpbmlkYWQgYW5kIFRvYmFnbwdUdW5pc2lhBlR1cmtleQxUdXJrbWVuaXN0YW4GVWdhbmRhB1VrcmFpbmUMdW5kZXRlcm1pbmVkFFVuaXRlZCBBcmFiIEVtaXJhdGVzDlVuaXRlZCBLaW5nZG9tDVVuaXRlZCBTdGF0ZXMHVXJ1Z3VheQpVemJla2lzdGFuB1ZhbnVhdHUJVmVuZXp1ZWxhB1ZpZXRuYW0XVmlyZ2luIElzbGFuZHMsIEJyaXRpc2gJV2VzdCBCYW5rBVllbWVuCFppbWJhYndlFCsDqQFnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZGQCIw8QDxYEHwIFCGxpc3RUeXBlHwNnZBAVAwNBbGwHTm9uLVNETgNTRE4VAwAHTm9uLVNETgNTRE4UKwMDZ2dnZGQCCQ9kFgICBQ88KwARAgEQFgAWABYADBQrAABkAhEPDxYCHwAFL1NETiBMaXN0IGxhc3QgdXBkYXRlZCBvbjogMTAvMjMvMjAyMCAyOjA1OjM3IFBNZGQCEw8PFgIfAAUzTm9uLVNETiBMaXN0IGxhc3QgdXBkYXRlZCBvbjogMy8xNy8yMDIwIDEwOjUzOjI3IEFNZGQYAgUeX19Db250cm9sc1JlcXVpcmVQb3N0QmFja0tleV9fFgMFHmN0bDAwJE1haW5Db250ZW50JEltYWdlQnV0dG9uMgUdY3RsMDAkTWFpbkNvbnRlbnQkbHN0UHJvZ3JhbXMFHmN0bDAwJE1haW5Db250ZW50JEltYWdlQnV0dG9uMQUhY3RsMDAkTWFpbkNvbnRlbnQkZ3ZTZWFyY2hSZXN1bHRzD2dkcDRloTLfeFENAcSkm2tM+VURxTVl9xbgnaSw5O7QFaQ=',
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


