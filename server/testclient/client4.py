import json, requests, sys

json_headers = { 'Content-type' : 'application/json', 
				 'Accept' : 'text/plain'}

server_info = {
	'server_url' : 'http://localhost',#"http://111.67.18.188",
	'port': "8080"
}

base_path = ("%(server_url)s:%(port)s" % server_info)

# login once
r = requests.post(base_path + '/login', data = """
    {
        "phone_number" : 1,
        "password" : "seecret"
    }
    """, headers = json_headers)

print r.status_code
print r.text
session_id = json.loads(r.text)['session_id']

# logout
r = requests.post(base_path + '/logout', data = """
    {
        "session_id" : "%s"
    }
    """ % session_id, headers = json_headers)

print r.status_code
print r.text

# login again
r = requests.post(base_path + '/login', data = """
    {
        "phone_number" : 1,
        "password" : "seecret"
    }
    """, headers = json_headers)

print r.status_code
print r.text
session_id = json.loads(r.text)['session_id']

# login yet again
r = requests.post(base_path + '/login', data = """
    {
        "phone_number" : 1,
        "password" : "seecret"
    }
    """, headers = json_headers)

print r.status_code
print r.text
session_id = json.loads(r.text)['session_id']

r = requests.post(base_path + '/passengers', data = """
    {
        "session_id" : "%s",
        "group_id" : 4,
        "user_id" : 2
    }
    """ % session_id, headers = json_headers)

print r.status_code
print r.text

r = requests.post(base_path + '/passengers', data = """
    {
        "session_id" : "%s",
        "group_id" : 4,
        "user_id" : 3
    }
    """ % session_id, headers = json_headers)

print r.status_code
print r.text

r = requests.post(base_path + '/passengers', data = """
    {
        "session_id" : "%s",
        "group_id" : 5,
        "user_id" : 4
    }
    """ % session_id, headers = json_headers)

print r.status_code
print r.text

r = requests.put(base_path + '/gps', data = """
    {
        "session_id" : "%s",
        "group_id" : 4,
        "latitude" : 27.3,
        "longitude" : 180.222
    }
    """ % session_id, headers = json_headers)

print r.status_code
print r.text

r = requests.get(base_path + '/notifications', data = """
    {
        "session_id" : "%s"
    }
    """ % session_id, headers = json_headers)

print r.status_code
print r.text

r = requests.get(base_path + '/notifications', data = """
    {
        "session_id" : "%s"
    }
    """ % session_id, headers = json_headers)

print r.status_code
print r.text
