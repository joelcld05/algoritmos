from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from algoritmos import settings
from bs4 import BeautifulSoup
import urllib.request
import pandas as pd
import requests
import pypyodbc
import datetime
import sqlite3
import json
import csv
import os
import logging


# comparationscon = sqlite3.connect("comparations.db", check_same_thread=False)

maxvalue = 75
# connStr = (r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=\\Grupofux\prestamos clientes\FINANCIERA UNIVERSAL XPRESS\COTIZACIONES\GRUPO_FUX_COTIZADOR\Archivo\GFUX_DWH.accdb;")
# connStr = (r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=C:\Users\HP\Documents\projects\algoritmos\GFUX_DWH.accdb;")
connStr = (
    r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ="
    + os.path.join(settings.BASE_DIR, "GFUX_DWH.accdb")
    + ";"
)


@require_http_methods(["GET"])
def index(request):
    if "username" in request.COOKIES:
        return HttpResponseRedirect("resultdos")
    else:
        response = HttpResponse(render(request, "index.html"))
        response.delete_cookie("message")
        return response


@csrf_exempt
def login(request):
    if request.method == "POST":
        conn = pypyodbc.connect(connStr)
        cur = conn.cursor()
        query = (
            "SELECT count(id) FROM tbl_permisos where tipo in ('Administrador','Cobros') and  User ='"
            + request.POST["user"]
            + "' and password='"
            + request.POST["password"]
            + "'"
        )

        cur.execute(query)
        rs = []
        while True:
            row = cur.fetchone()
            if row is None:
                break
            rs = row
        if rs[0] >= 1:
            response = HttpResponseRedirect("reportes")
            response.set_cookie("username", request.POST["user"])
        else:
            response = HttpResponse(
                render(request, "index.html", {"message": "Credenciales incorrectas"})
            )
        return response
    else:
        return HttpResponseRedirect("reportes")


def logout(request):
    response = HttpResponseRedirect("/")
    response.delete_cookie("username")
    return response


@csrf_exempt
def guarda(request):
    if request.method == "POST":
        # try:
        idinsert = request.POST["idreporte"]
        idcliente = request.POST["idcliente"]
        idcompara = request.POST[idcliente + "-idcompara"]
        lista1 = list(dict.fromkeys(idcompara.split(",")))
        conn = pypyodbc.connect(connStr)
        cur = conn.cursor()

        for a in lista1:
            accion = request.POST["conservar-" + a]
            query = "update tbl_ofac_reportados set "
            query += (
                "observacion='"
                + request.POST["observacion-" + a].replace("'", "")
                + "',idcompara='"
                + a
                + "',nombrecompara='"
                + request.POST["nombrecompara-" + a].replace("'", "")
            )

            query += (
                "', reporta='"
                + request.COOKIES["username"].replace("'", "")
                + "', jaro="
                + request.POST["score-" + a]
                + ",report="
                + idinsert
                + ",accion='"
                + accion
                + "' where id = "
                + idcliente
            )

            # curguarda = comparationscon.cursor()
            # curguarda.execute(
            #     "INSERT INTO comparations (idcliente, idofac)  VALUES ('"
            #     + idcliente
            #     + "', "
            #     + a
            #     + ");"
            # )
            # comparationscon.commit()
            cur.execute(query)
        cur.commit()
        cur.close()
        conn.close()
        updateUserSearch(idcliente)
        return HttpResponse('{"response":"true"}', content_type="application/json")
    return HttpResponse('{"response":"fasle"}', content_type="application/json")


@require_http_methods(["GET"])
def reportpage(request, idreport):
    if "username" in request.COOKIES and idreport != "":
        getToken()
        conn = pypyodbc.connect(connStr)
        cur = conn.cursor()
        query = (
            "SELECT tbl_ofac_clients_search.id FROM tbl_ofac_clients_search where idreporte="
            + str(idreport)
            + " and status = 0"
        )
        cur.execute(query)

        rs = []
        while True:
            row = cur.fetchone()
            if row is None:
                break
            rs.append(row[0])
        cur.commit()
        cur.close()
        conn.close()
        return HttpResponse(
            render(
                request, "table.html", {"datsdb": json.dumps(rs), "idreporte": idreport}
            )
        )
    else:
        return HttpResponseRedirect("/")


def verificareporte(username, idinsert):
    conn = pypyodbc.connect(connStr)
    cur = conn.cursor()
    query = "SELECT id FROM tbl_ofac_reportes where id=" + idinsert
    cur.execute(query)
    row = cur.fetchall()
    if len(row) == 0:
        conn2 = pypyodbc.connect(connStr)
        cur2 = conn2.cursor()
        query = (
            "insert into tbl_ofac_reportes(id,usuario) values ("
            + idinsert
            + ",'"
            + username
            + "');"
        )
        cur2.execute(query)
        cur2.commit()
        cur2.close()
        conn2.close()
    cur.close()
    conn.close()
    return len(row)


@csrf_exempt
def getresult(request):
    if request.method == "POST":
        rs = []

        idcompara = request.POST["id"]

        # cursor = comparationscon.execute(
        #     "SELECT idofac from comparations where idcliente='" + idcompara + "'"
        # )

        rows = []  # cursor.fetchall()
        skip = []
        for row in rows:
            skip.append(row[0])

        conn = pypyodbc.connect(connStr)
        cur = conn.cursor()
        query = (
            "SELECT OFAC.id, OFAC.Name, OFAC.LastName FROM tbl_ofac_clients_search inner join OFAC on OFAC.ID=tbl_ofac_clients_search.idclinete where tbl_ofac_clients_search.id = "
            + idcompara
        )
        cur.execute(query)
        rsName = cur.fetchone()
        cur.commit()
        cur.close()
        conn.close()

        nombre = str(rsName[1]).strip() + " " + str(rsName[2]).strip()
        try:
            response = searchName(nombre.replace(",", "").upper(), skip)
            totalrs = len(response)
            if totalrs > 0:
                rs.append(
                    {
                        "datos": response,
                        "total": totalrs,
                        "nombre": nombre,
                        "idclinete": rsName[0],
                    }
                )
            else:
                updateUserSearch(idcompara)

            return JsonResponse(rs, safe=False)
        except:
            return HttpResponse(status=400)


@csrf_exempt
def create_reporte(request):
    if "username" in request.COOKIES and request.method == "POST":
        idinsert = datetime.datetime.now().strftime("%d%m%Y")
        getToken()
        lenRep = verificareporte(request.COOKIES["username"], idinsert)
        if lenRep == 0:
            conn = pypyodbc.connect(connStr)
            cur = conn.cursor()

            query = "SELECT id FROM OFAC where id not in(SELECT distinct idclinete FROM tbl_ofac_reportados where accion ='Reportado')"
            cur.execute(query)
            rows = cur.fetchall()
            for row in rows:
                cur2 = conn.cursor()
                cur2.execute(
                    "insert into tbl_ofac_clients_search (idclinete, idreporte) values ('"
                    + row[0]
                    + "',"
                    + idinsert
                    + ")"
                )
                cur2.commit()
                cur2.close()

            cur.commit()
            cur.close()
            conn.close()

        return HttpResponseRedirect("/reportes")
    else:
        return HttpResponseRedirect("/")


def searchName(name, skip):
    token = ""
    with open("ofactoken.json") as json_file:
        data = json.load(json_file)
    token = data["token"]
    r = []
    r = requests.post(
        "https://sanctionssearch.ofac.treas.gov/",
        data={
            "ctl00_ctl03_HiddenField": ";;AjaxControlToolkit, Version=3.5.40412.0, Culture=neutral",
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": token,
            "__VIEWSTATEGENERATOR": "CA0B0334",
            "ctl00$MainContent$ddlType": "",
            "ctl00$MainContent$txtAddress": "",
            "ctl00$MainContent$txtLastName": name,
            "ctl00$MainContent$txtCity": "",
            "ctl00$MainContent$txtID": "",
            "ctl00$MainContent$txtState": "",
            "ctl00$MainContent$lstPrograms": "",
            "ctl00$MainContent$ddlCountry": "",
            "ctl00$MainContent$ddlList": "",
            "ctl00$MainContent$Slider1": "85",
            "ctl00$MainContent$Slider1_Boundcontrol": "85",
            "ctl00$MainContent$btnSearch": "Search",
        },
    )

    soup = BeautifulSoup(r.text, "html.parser")
    rsdata = []
    table = soup.find(id="gvSearchResults")

    if table is not None:
        for link in table.find_all("tr"):
            newdata = []
            linkofac = link.a
            actialid = 0
            if linkofac is not None:
                actialid = linkofac.get("href").split("=")[1]
                newdata.append(actialid)
            if int(actialid) not in skip:
                for item in link.find_all("td"):
                    newdata.append(item.get_text().strip())
                rsdata.append(newdata)

    return rsdata


def updateUserSearch(idcompara):
    conn2 = pypyodbc.connect(connStr)
    cur2 = conn2.cursor()
    query = (
        "update tbl_ofac_clients_search set status=1 where tbl_ofac_clients_search.id = "
        + idcompara
    )
    cur2.execute(query)
    cur2.commit()
    cur2.close()
    conn2.close()


def downloadfile():
    try:
        sdn = []
        alt = {}
        name = datetime.datetime.now().strftime("%d-%m-%Y")
        urlsdn = "https://www.treasury.gov/ofac/downloads/sdn.csv"
        urlalt = "https://www.treasury.gov/ofac/downloads/alt.csv"
        urllib.request.urlretrieve(
            urlsdn, os.path.join(settings.BASE_DIR, "static/data/sdn-" + name + ".csv")
        )
        urllib.request.urlretrieve(
            urlalt, os.path.join(settings.BASE_DIR, "static/data/alt-" + name + ".csv")
        )

        with open("static/data/alt-" + name + ".csv", newline="") as csvfile:
            spamreader = csv.reader(csvfile)
            for row in spamreader:
                if not row[0] in alt:
                    alt[row[0]] = [row]
                else:
                    alt[row[0]].append(row)

        with open("static/data/sdn-" + name + ".csv", newline="") as csvfile:
            spamreader = csv.reader(csvfile)
            for row in spamreader:
                akadato = []
                if row[0] in alt:
                    akadato = alt[row[0]]
                item = {"data": row, "aka": akadato}
                sdn.append(item)

        with open("data.json", "w") as write_file:
            json.dump(sdn, write_file)
    except:
        pass


@require_http_methods(["GET"])
def reportpageIndex(request):
    if "username" in request.COOKIES:
        conn = pypyodbc.connect(connStr)
        cur = conn.cursor()
        query = "select top 12 str(tbl_ofac_reportes.fecha) as fecha, tbl_ofac_reportes.usuario, count(tbl_ofac_reportes.ID) as totales,tbl_ofac_reportes.ID from tbl_ofac_reportes left join tbl_ofac_reportados on tbl_ofac_reportados.report=tbl_ofac_reportes.ID group by tbl_ofac_reportes.ID, tbl_ofac_reportes.fecha, tbl_ofac_reportes.usuario order by tbl_ofac_reportes.fecha desc"
        cur.execute(query)
        rs = []
        while True:
            row = cur.fetchone()
            if row is None:
                break
            rs.append(row)
        return HttpResponse(render(request, "reportes.html", {"datsdb": rs}))
    else:
        return HttpResponseRedirect("/")


@require_http_methods(["GET"])
def printReport(request, idreport):
    if "username" in request.COOKIES:
        conn = pypyodbc.connect(connStr)
        cur = conn.cursor()
        query = (
            "select reporta,fecha,idclinete, name, lastname, id,observacion,idcompara,nombrecompara,jaro,sound, accion from tbl_ofac_reportados inner join OFAC on OFAC.id=tbl_ofac_reportados.idclinete where report="
            + str(idreport)
        )
        cur.execute(query)
        row = cur.fetchall()

        file_name = str(idreport) + "-reporte.xlsx"
        path_to_file = settings.BASE_DIR + "/static/exports/"

        df = pd.DataFrame(
            row,
            columns=[
                "Reportado Por",
                "Fecha reportado",
                "ID Cliente",
                "Nombres",
                "Apellidos",
                "Cédula",
                "Observación",
                "ID OFAC",
                "Nombre OFAC",
                "Score",
                "",
                "Acción",
            ],
        )
        df.to_excel(path_to_file + file_name, index=False, header=True)

        file_path = path_to_file + file_name
        if os.path.exists(file_path):
            with open(file_path, "rb") as fh:
                response = HttpResponse(
                    fh.read(), content_type="application/vnd.ms-excel"
                )
                response[
                    "Content-Disposition"
                ] = "inline; filename=" + os.path.basename(file_path)
                return response
        raise HttpResponse(status=[400])
    else:
        return HttpResponseRedirect("/")


def getToken():
    r = []
    r = requests.get("https://sanctionssearch.ofac.treas.gov/")
    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find(id="__VIEWSTATE")["value"]
    data = {"token": table}

    with open("ofactoken.json", "w") as write_file:
        json.dump(data, write_file)
    return False
