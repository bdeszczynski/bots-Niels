import json
from datetime import date, timedelta, datetime

import re
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

PPT_API = 'https://new.portpoint.com/ppt-api/'
headers = {'Content-Type': 'application/json'}

token = None
lastTokenRead = None

QUOTED_STRING_RE = re.compile(
    r"(?P<quote>['\"])(?P<string>.*?)(?<!\\)(?P=quote)")


def getToken():
    global lastTokenRead
    if lastTokenRead is None or ( lastTokenRead < (datetime.now() + timedelta(hours=-1))):
        lastTokenRead = datetime.now()
        body = '{"username": "NIELS","password": "Password1234"}'
        response = requests.post(PPT_API + 'users/atlis/sessions?', headers=headers, data=body, verify=False)
        return response.text[1:-1]
    else:
        return token


def getCosts(portId, dwtMin, dwtMax):
    token = getToken()
    url = 'https://new.portpoint.com/ppt-api/cost-statistics/ports/%s?Marcura-Auth-Token=%s&dwt-max=%s&dwt-min=%s&eta-from=%s' % \
          (str(portId), token, str(dwtMax), str(dwtMin),
           (date.today() + timedelta(days=-730)).strftime("%Y-%m-%dT%H:%M:%S.000"))
    response = requests.get(url)
    if "average" in response.json():
        return response.json()['average']['cost']
    else:
        return 0


with open('data/vessels.json') as v:
    vessels = json.loads(v.read())

with open('data/ports.json') as p:
    ports = json.loads(p.read())

token = getToken()


def getPortId(portName):
    f = list(filter(lambda port: port['name'] == portName.upper(), ports))
    if len(f) == 0:
        return -1
    else:
        return f[0]['id']


def getVesselDwt(vesselName):
    f = list(filter(lambda vessel: vessel['name'] == vesselName.upper(), vessels))
    if len(f) == 0:
        return -1
    else:
        return f[0]['DWT']


@app.route("/portcosts", methods=['POST'])
def portcosts():
    cmd = request.form.get('text', '')
    l = cmd.split(' ')
    if l[0].lower().find('portcost') < 0:
        return jsonify(text="unknown command. try portcost <port> <vessel>")

    ret = QUOTED_STRING_RE.findall(cmd);
    if ret is None or len(ret) < 2:
        return jsonify(text="unknown command. try portcost <port> <vessel>")
    portName = ret[0][1]
    vesselName = ret[1][1]
    portId = getPortId(portName)
    if portId == -1:
        return jsonify(text="Port not found")

    dwt = getVesselDwt(vesselName)
    if dwt == -1:
        return jsonify(text="Vessel not found")
    cost = getCosts(portId, int(dwt * 0.8), int(dwt * 1.2))
    if cost > 0:
        return jsonify(text='{0:,.2f}'.format(cost) + ' USD (excluding the agency fee)')
    else:
        return jsonify(text="Not enough data to benchmark")


if __name__ == "__main__":
    app.run(threaded=True, port=8045, host='0.0.0.0')
