from flask import Flask, request, send_from_directory, send_file
from flask_cors import CORS
from json import dumps, loads
from pathlib import Path
from random import randint
from hashlib import sha256
import time
import ldap3
import boto3

app = Flask(__name__)
CORS(app)
ALLOWED_TYPES = ["A", "AAAA", "CNAME", "TXT"]

class SessionManager:
    def __init__(self):
        self.session = {}
    
    def new(self, userid) -> str:
        sessionid = sha256(f"{randint(100000, 999999)}{userid}{str(time.time())}".encode()).hexdigest()
        self.session[sessionid] = {
            'id': sessionid,
            'userid': userid,
            'created': time.time(),
            'lastaccess': time.time(),
        }
        return sessionid
    
    def update(self, sessionid):
        if sessionid in self.session:
            self.session[sessionid]['lastaccess'] = time.time()
            return True
        else:
            return False
    
    def is_valid(self, sessionid) -> bool:
        if sessionid in self.session:
            if self.session[sessionid]['lastaccess'] - self.session[sessionid]['created'] < config["expire"]:
                return True
            else:
                self.session.pop(sessionid)
                return False
        else:
            return False
        
    def logout(self, sessionid):
        if sessionid in self.session:
            self.session.pop(sessionid)
            return True
        else:
            return False
        
    def get_userinfo(self, sessionid) -> dict:
        if sessionid in self.session:
            return self.session[sessionid]
        else:
            return None
    
    def get_userid(self, sessionid) -> str:
        if sessionid in self.session:
            return self.session[sessionid]['userid']
        else:
            return None


config = loads(Path('config.json').read_text())
session = SessionManager()
botor53 = boto3.client('route53', aws_access_key_id=config['aws']['accessKeyId'], aws_secret_access_key=config['aws']['secretAccessKey'])

@app.route('/')
def index():
    root = Path("../front/build/")
    return send_file(root.joinpath("index.html"))

@app.route('/<path:path>')
def index(path):
    root = Path("../front/build/")
    if path != "" and root.joinpath(path).is_file():
        return send_from_directory(root, path)
    else:
        return "Not Found", 404

@app.route('/api/auth', methods=['POST'])
def auth():
    global session
    if "userid" not in request.json or "userpw" not in request.json:
        return dumps({'status': 400, 'message': 'Invalid request'}), 400
    
    userid = request.json['userid'].lower()
    passwd = request.json['userpw']
    
    try:
        server = ldap3.Server(config['ldap']['host'], get_info=ldap3.ALL)
        conn = ldap3.Connection(server, f"uid={userid},{config['ldap']['bindDn']}", passwd, auto_bind=True)
        if conn.bind():
            sessionid = session.new(userid)
            return dumps({'status': 200, 'sessid': sessionid, 'message': 'Successfully logged in'})
        else:
            return dumps({'status': 401, 'message': 'Invalid credentials'}), 401
    
    except ldap3.core.exceptions.LDAPBindError:
        return dumps({'status': 401, 'message': 'Wrong id or password.'}), 401
    except Exception as e:
        raise e
        return dumps({'status': 500, 'message': "Error in server. Contact wheel!"}), 500

@app.route('/api/auth', methods=['GET'])
def auth_check():
    global session
    if "sessid" not in request.headers: return dumps({'status': 400, 'message': 'Invalid request'}), 400
    if session.is_valid(request.headers['sessid']):
        session.update(request.headers['sessid'])
        return dumps({'status': 200, 'message': 'Session is valid'}), 200
    else:
        return dumps({'status': 401, 'message': 'Session is invalid'}), 401
    
@app.route('/api/auth', methods=['DELETE'])
def auth_logout():
    global session
    if "sessid" not in request.headers: return dumps({'status': 'error', 'message': 'Invalid request'}), 400
    if session.is_valid(request.headers['sessid']):
        session.logout(request.headers['sessid'])
        return dumps({'status': 200, 'message': 'Session is deleted'}), 200
    else:
        return dumps({'status': 401, 'message': 'Session is invalid'}), 401
    
@app.route('/api/dns', methods=['GET'])
def dns_list():
    global botor53
    if "sessid" not in request.headers: return dumps({'status': 'error', 'message': 'Invalid request'}), 400
    if not session.is_valid(request.headers['sessid']):
        return dumps({'status': 401, 'message': 'Session is invalid'}), 401
    session.update(request.headers['sessid'])
    sessid = request.headers['sessid']
    
    check: list = botor53.list_resource_record_sets(HostedZoneId=config['aws']['hostedZoneId'])["ResourceRecordSets"]
    if len(check) == 0:
        return dumps({'status': 404, 'message': 'No records found'}), 404
    checkdns: str = check[0]["Name"]
    if checkdns.endswith("."): checkdns = checkdns[:-1]
    level2_dns = ".".join(checkdns.split(".")[-2:])

    if level2_dns != ".".join(config['domain'].split(".")[-2:]):
        return dumps({'status': 500, 'message': 'Invalid domain. Contact wheel.'}), 500

    search_domain = f"{session.get_userid(sessid)}.{config['domain']}"
    search_domain_txt = f"_acme-challenge.{search_domain}"

    result = {}
    checkdns = botor53.list_resource_record_sets(HostedZoneId=config['aws']['hostedZoneId'], StartRecordName=search_domain, StartRecordType="A")["ResourceRecordSets"]
    for record in checkdns:
        if record["Name"] == f"{search_domain}.":
            result[record["Name"]] = {"type": record["Type"], "value": record["ResourceRecords"][0]["Value"]}
        elif record["Name"] == f"{search_domain_txt}.":
            result[record["Name"]] = {"type": record["Type"], "value": record["ResourceRecords"][0]["Value"]}
        if len(result) == 2: break
    if search_domain not in result: result[search_domain] = {"type": "", "value": ""}
    if search_domain_txt not in result: result[search_domain_txt] = {"type": "", "value": ""}

    return dumps({'status': 200, 'message': 'Successfully get records', 'data': result, "available_types": ALLOWED_TYPES}), 200



@app.route('/api/dns', methods=['POST'])
def update_dns():
    global botor53
    if "sessid" not in request.headers: return dumps({'status': 'error', 'message': 'Invalid request'}), 400
    if not session.is_valid(request.headers['sessid']):
        return dumps({'status': 401, 'message': 'Session is invalid'}), 401
    sessid = request.headers['sessid']
    session.update(sessid)

    data = request.json
    domain = f"{session.get_userid(sessid)}.{config['domain']}"
    domain_txt = f"_acme-challenge.{domain}"

    if domain not in data or domain_txt not in data:
        return dumps({'status': 400, 'message': 'Invalid request'}), 400
    
    if data[domain]['type'] not in ALLOWED_TYPES or data[domain_txt]['type'] not in ALLOWED_TYPES:
        return dumps({'status': 400, 'message': 'Invalid record type'}), 400
    
    changes = {"Changes": []}
    if domain in data and data[domain]['type'] != "":
        if data[domain]['type'] == "TXT":
            data[domain]['value'] = f"\"{data[domain]['value']}\""
        changes["Changes"].append({
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": f'{domain}.',
                "Type": data[domain]['type'],
                "TTL": 300,
                "ResourceRecords": [{"Value": data[domain]['value']}]
            }
        })
    if domain in data and data[domain_txt]['type'] != "":
        if data[domain_txt]['type'] == "TXT":
            data[domain_txt]['value'] = f"\"{data[domain_txt]['value']}\""

        changes["Changes"].append({
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": f"{domain_txt}.",
                "Type": data[domain_txt]['type'],
                "TTL": 300,
                "ResourceRecords": [{"Value": data[domain]['value']}]
            }
        })
    
    if len(changes) == 0:
        return dumps({'status': 400, 'message': 'No changes to update'}), 400
    
    try:
        botor53.change_resource_record_sets(HostedZoneId=config['aws']['hostedZoneId'], ChangeBatch=changes)
        return dumps({'status': 200, 'message': 'Successfully updated records'}), 200
    except Exception as e:
        return dumps({'status': 500, 'message': f"Error in server. Contact wheel! {e}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
