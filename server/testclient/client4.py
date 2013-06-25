import json, requests, sys

json_headers = { 'Content-type' : 'application/json', 
				 'Accept' : 'text/plain'}

server_info = {
	'server_url' : 'http://localhost',#"http://111.67.18.188",
	'port': "8080"
}

base_path = ("%(server_url)s:%(port)s" % server_info)

r = requests.get(base_path + '/group', data = """
    {
        "group_name" : "%s"
        
    }
    """ % ('g-unit',), headers = json_headers)

print r.status_code
print r.text
