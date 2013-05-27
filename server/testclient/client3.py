import json, requests, sys

json_headers = { 'Content-type' : 'application/json', 
				 'Accept' : 'text/plain'}

server_info = {
	'server_url' : 'http://localhost',#"http://111.67.18.188",
	'port': "8080"
}

base_path = ("%(server_url)s:%(port)s" % server_info)

r = requests.post(base_path + '/login', data = """
    {
        "phone_number" : 9001,
        "password" : "seecret"
    }
    """, headers = json_headers)

print r.status_code
print r.text

session_id = json.loads(r.text)['session_id']

r = requests.post(base_path + '/createGroup', data = """
    {
        "session_id" : "%s",
        "group" :
            {
                "name" : "sfdgfdsh2",
                "origin" : "wellington",
                "destination" : "khazakstanistan",
                "arrival_time" : "1:00:00",
                "departure_time" : "2:00:00",
                "seats" : 3,
                "days" : "1010101"
            }
    }
    """ % session_id, headers = json_headers)

print r.status_code
print r.text
