from django.http import HttpResponseRedirect
from algoritmos import settings
from bs4 import BeautifulSoup
import urllib.request
import requests
import pypyodbc
import datetime
import json
import csv
import os

# connStr = (r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=\\Grupofux\prestamos clientes\FINANCIERA UNIVERSAL XPRESS\COTIZACIONES\GRUPO_FUX_COTIZADOR\Archivo\GFUX_DWH.accdb;")

connStr = (
    r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ="
    + os.path.join(settings.BASE_DIR, "GFUX_DWH.accdb")
    + ";"
)


def getToken():
    r = []
    r = requests.get("https://sanctionssearch.ofac.treas.gov/")
    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find(id="__VIEWSTATE")["value"]
    data = {"token": table}

    with open("ofactoken.json", "w") as write_file:
        json.dump(data, write_file)
    return False


def logout(request):
    response = HttpResponseRedirect("/")
    response.delete_cookie("username")
    return response


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
        idcount = 1
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
                newdata.append("{}~{}".format(idcount, actialid))
                idcount = idcount + 1
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


def updateUserWithData(data, idcompara):
    conn2 = pypyodbc.connect(connStr)
    cur2 = conn2.cursor()
    query = "update tbl_ofac_clients_search set data='{}', status=1 where tbl_ofac_clients_search.id = {}".format(
        data.replace("'", ""), idcompara
    )
    cur2.execute(query)
    cur2.commit()
    cur2.close()
    conn2.close()

def updateUserReviewed( idcompara):
    conn2 = pypyodbc.connect(connStr)
    cur2 = conn2.cursor()
    query = "update tbl_ofac_clients_search set revisado=1 where tbl_ofac_clients_search.id = {}".format(
        idcompara
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
