"""
% python client2.py POST /login "{ 'phone_number' : 9001, 'password' : 'seecret' }"
200
{"session_expires": 1369369986, "session_id": "7a94c0cc62bc4ef08821e4a3528797df"}

% python client2.py POST /createGroup "{ 'session_id' : '7a94c0cc62bc4ef08821e4a3528797df', 'group' : { 'name' : 'fred', 'origin' : 'narnia', 'destination' : 'wardrobe', 'arrival_time' : '8:00:00', 'departure_time' : '7:00:00', 'seats' : 2, 'days' : '1111111' } }"
200
{}
"""

﻿import json, requests, sys

json_headers = { 'Content-type' : 'application/json', 
				 'Accept' : 'text/plain'}

server_info = {
	'server_url' : 'http://localhost',#"http://111.67.18.188",
	'port': "8080"
}

full_path = ("%(server_url)s:%(port)s" % server_info) + sys.argv[2]

if sys.argv[1] == 'POST':
    r = requests.post(full_path,data=sys.argv[3].replace("'", '"'),headers=json_headers)
else:
    r = requests.get(full_path,data=sys.argv[3].replace("'", '"'),headers=json_headers)

print r.status_code
print r.text
