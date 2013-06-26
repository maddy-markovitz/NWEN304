import json, requests, sys

json_headers = { 'Content-type' : 'application/json', 
				 'Accept' : 'text/plain'}

server_info = {
	'server_url' : 'http://localhost',#"http://111.67.18.188",
	'port': "8080"
}

base_path = ("%(server_url)s:%(port)s" % server_info)

r = requests.post(base_path + '/passengers', data = """
    {
        "group_id" : 4,
        "user_id" : 2
    }
    """, headers = json_headers)

print r.status_code
print r.text

r = requests.post(base_path + '/passengers', data = """
    {
        "group_id" : 4,
        "user_id" : 3
    }
    """, headers = json_headers)

print r.status_code
print r.text

r = requests.post(base_path + '/passengers', data = """
    {
        "group_id" : 5,
        "user_id" : 4
    }
    """, headers = json_headers)

print r.status_code
print r.text

r = requests.put(base_path + '/gps', data = """
    {
        "group_id" : 4,
        "latitude" : 27.3,
        "longitude" : 180.222
    }
    """, headers = json_headers)

print r.status_code
print r.text

r = requests.get(base_path + '/notifications', data = """
    {
        
    }
    """, headers = json_headers)

print r.status_code
print r.text

r = requests.get(base_path + '/notifications', data = """
    {
        
    }
    """, headers = json_headers)

print r.status_code
print r.text
