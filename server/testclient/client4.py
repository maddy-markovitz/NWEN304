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
s1 = json.loads(r.text)['session_id']

# logout
r = requests.post(base_path + '/logout', data = """
    {
        "session_id" : "%s"
    }
    """ % s1, headers = json_headers)

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
s1 = json.loads(r.text)['session_id']

# login yet again
print '1 logs in'
r = requests.post(base_path + '/login', data = """
    {
        "phone_number" : 1,
        "password" : "seecret"
    }
    """, headers = json_headers)

print r.status_code
print r.text
s1 = json.loads(r.text)['session_id']

# login another user
print '2 logs in'
r = requests.post(base_path + '/login', data = """
    {
        "phone_number" : 2,
        "password" : "seecret"
    }
    """, headers = json_headers)

print r.status_code
print r.text
s2 = json.loads(r.text)['session_id']


# now do some shit


print '1 invites 2'
r = requests.post(base_path + '/groupinvite', data = """
    {
        "session_id" : "%s",
        "group_id" : 4,
        "user_id" : 2
    }
    """ % s1, headers = json_headers)

print r.status_code
print r.text
ginv = json.loads(r.text)['invite_id']

print '2 requests g4'
r = requests.post(base_path + '/grouprequest', data = """
    {
        "session_id" : "%s",
        "group_id" : 4
    }
    """ % s2, headers = json_headers)

print r.status_code
print r.text

print '1 checks notifications'
r = requests.get(base_path + '/notifications', data = """
    {
        "session_id" : "%s"
    }
    """ % s1, headers = json_headers)

print r.status_code
print r.text
greq = json.loads(r.text)['notifications'][0]['request_id']

print '2 checks notifications'
r = requests.get(base_path + '/notifications', data = """
    {
        "session_id" : "%s"
    }
    """ % s2, headers = json_headers)

print r.status_code
print r.text

print '1 accepts request'
r = requests.post(base_path + '/acceptgrouprequest', data = """
    {
        "session_id" : "%s",
        "request_id" : "%s"
    }
    """ % (s1, greq), headers = json_headers)

print r.status_code
print r.text

print '1 withdraws invite'
r = requests.delete(base_path + '/groupinvite', data = """
    {
        "session_id" : "%s",
        "invite_id" : "%s"
    }
    """ % (s1, ginv), headers = json_headers)

print r.status_code
print r.text

print '1 updates g4 gps'
r = requests.put(base_path + '/gps', data = """
    {
        "session_id" : "%s",
        "group_id" : 4,
        "latitude" : 27.3,
        "longitude" : 180.222
    }
    """ % s1, headers = json_headers)

print r.status_code
print r.text

print '1 checks notifications'
r = requests.get(base_path + '/notifications', data = """
    {
        "session_id" : "%s"
    }
    """ % s1, headers = json_headers)

print r.status_code
print r.text

print '2 checks notifications'
r = requests.get(base_path + '/notifications', data = """
    {
        "session_id" : "%s"
    }
    """ % s2, headers = json_headers)

print r.status_code
print r.text



























