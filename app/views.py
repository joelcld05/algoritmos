from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from algoritmos import settings
import pandas as pd
import pypyodbc
import datetime
import json
import os

from .utils.process import (
    getToken,
    logout,
    connStr,
    verificareporte,
    updateUserSearch,
    searchName,
    updateUserWithData,
    updateUserReviewed,
)


@require_http_methods(["GET"])
def index(request):
    if "username" in request.COOKIES:
        return HttpResponseRedirect("reportes")
    else:
        response = HttpResponse(render(request, "index.html"))
        response.delete_cookie("message")
        return response


@csrf_exempt
@require_http_methods(["POST"])
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


@csrf_exempt
@require_http_methods(["POST"])
def guarda(request):
    if request.method == "POST":
        # try:
        idinsert = request.POST["idreporte"]
        idcliente = request.POST["idcliente"]
        idclientedb = request.POST["idclientedb"]
        idcompara = request.POST[idcliente + "-idcompara"]
        lista1 = list(dict.fromkeys(idcompara.split(",")))
        conn = pypyodbc.connect(connStr)
        cur = conn.cursor()
        for a in lista1:
            ab = a.split("~")
            accion = request.POST["conservar-" + a]
            query = """
            insert into tbl_ofac_reportados (observacion,idcompara,nombrecompara,reporta,jaro,report,accion,idclinete) values
            (
            '{}',
            '{}',
            '{}',
            '{}', 
            {}, 
            {},
            '{}',
            '{}'
            );
            """.format(
                request.POST["observacion-" + a].replace("'", ""),
                ab[1],
                request.POST["nombrecompara-" + a].replace("'", ""),
                request.COOKIES["username"].replace("'", ""),
                request.POST["score-" + a],
                idinsert,
                accion,
                idclientedb,
            )

            cur.execute(query)
            updateUserReviewed(idcliente)
        cur.commit()
        cur.close()
        conn.close()

        return HttpResponse('{"response":"true"}', content_type="application/json")
    return HttpResponse('{"response":"fasle"}', content_type="application/json")


@require_http_methods(["GET"])
def reportpage(request, idreport):
    if "username" in request.COOKIES and idreport != "":
        getToken()
        conn = pypyodbc.connect(connStr)
        cur = conn.cursor()
        query = (
            "SELECT tbl_ofac_clients_search.id, data, status FROM tbl_ofac_clients_search where revisado=0 and idreporte="
            + str(idreport)
        )
        queryCount = """
        select 
            (select count(t.idclinete) from (select distinct tbl_ofac_reportados.idclinete,report from tbl_ofac_reportados) as t where t.report=tbl_ofac_reportes.ID) as totales_reported, 
            (select count(tbl_ofac_clients_search.ID) from tbl_ofac_clients_search where tbl_ofac_clients_search.idreporte=tbl_ofac_reportes.ID ) as totales_search, 
            (select count(tbl_ofac_clients_search.ID) from tbl_ofac_clients_search where tbl_ofac_clients_search.idreporte=tbl_ofac_reportes.ID and status = 1) as totales_completed,
            status
        from tbl_ofac_reportes where tbl_ofac_reportes.ID={idreport} 
        order by tbl_ofac_reportes.fecha desc
        """.format(
            idreport=str(idreport)
        )
        cur.execute(query)

        rs = []
        dataFounf = []
        while True:
            row = cur.fetchone()
            if row is None:
                break
            if row[1]:
                dataFounf.append({"id": row[0], "data": json.loads(row[1])})
            else:
                if row[2] == 0:
                    rs.append(row[0])

        # cur.commit()

        rsCount = []
        cur.execute(queryCount)
        rsCount = cur.fetchone()

        cur.close()
        conn.close()
        return HttpResponse(
            render(
                request,
                "search.html",
                {
                    "datsdb": json.dumps(rs),
                    "totals": json.dumps(rsCount),
                    "idreporte": idreport,
                    "reportesmade": dataFounf,
                },
            )
        )
    else:
        return HttpResponseRedirect("/")


@csrf_exempt
@require_http_methods(["POST"])
def getresult(request):
    rs = []

    idcompara = request.POST["id"]

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
            compara = []
            countt = 1
            for row in response:
                compara.append("{}~{}".format(countt, row[0]))
                countt = countt + 1
            data = {
                "total": totalrs,
                "nombre": nombre,
                "idclinete": rsName[0],
                "comparacion": ",".join(compara),
                "datos": response,
            }
            rs.append(data)
            updateUserWithData(json.dumps(data), idcompara)
        else:
            updateUserSearch(idcompara)

        return JsonResponse(rs, safe=False)
    except:
        return HttpResponse(status=400)


@csrf_exempt
@require_http_methods(["POST"])
def create_reporte(request):
    if "username" in request.COOKIES:
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
        return HttpResponseRedirect("/resultados/" + idinsert)
    else:
        return HttpResponseRedirect("/")


@require_http_methods(["GET"])
def reportpageIndex(request):
    if "username" in request.COOKIES:
        conn = pypyodbc.connect(connStr)
        cur = conn.cursor()
        query = """
        select top 100 
            str(tbl_ofac_reportes.fecha) as fecha, 
            tbl_ofac_reportes.usuario, 
            (select count(t.idclinete) from (select distinct tbl_ofac_reportados.idclinete,report from tbl_ofac_reportados) as t where t.report=tbl_ofac_reportes.ID) as totales, 
            (select count(tbl_ofac_clients_search.ID) from tbl_ofac_clients_search where tbl_ofac_clients_search.idreporte=tbl_ofac_reportes.ID ) as totales_search, 
            tbl_ofac_reportes.ID,
            status
        from tbl_ofac_reportes 
        order by tbl_ofac_reportes.fecha desc
        """
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
        return HttpResponse(status=[])
    else:
        return HttpResponseRedirect("/")


@require_http_methods(["POST"])
def endReport(request, idreport):
    try:
        if "username" in request.COOKIES:
            conn2 = pypyodbc.connect(connStr)
            cur2 = conn2.cursor()
            query = (
                "select count(ID) from tbl_ofac_clients_search where status=0 and idreporte="
                + str(idreport)
            )
            cur2.execute(query)
            row = cur2.fetchone()

            if row[0] > 0:
                raise

            query = (
                "select count(ID) from tbl_ofac_clients_search where data is not null and revisado=0 and idreporte="
                + str(idreport)
            )
            cur2.execute(query)
            row = cur2.fetchone()

            if row[0] > 0:
                raise

            query = (
                "update tbl_ofac_reportes set status=1 where tbl_ofac_reportes.id = "
                + str(idreport)
            )
            cur2.execute(query)
            cur2.commit()
            cur2.close()
            conn2.close()
            return HttpResponseRedirect("/reportes")
        else:
            return HttpResponseRedirect("/login")
    except:
        messages.error(request, "La búsqueda aún no ha finalizado o existen usuarios que no se han validado")
        return HttpResponseRedirect(
            "/resultados/" + str(idreport),
        )
