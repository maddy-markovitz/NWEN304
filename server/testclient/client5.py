import json, requests, sys

json_headers = { 'Content-type' : 'application/json', 
				 'Accept' : 'text/plain'}

server_info = {
	'server_url' : 'http://localhost',#"http://111.67.18.188",
	'port': "8080"
}

base_path = ("%(server_url)s:%(port)s" % server_info)

# login once
r = requests.post(base_path + '/doeverything', data = """
    {
        "__method__" : "login",
        "phone_number" : 1,
        "password" : "seecret"
    }
    """, headers = json_headers)

print r.status_code
print r.text
s1 = json.loads(r.text)['session_id']
