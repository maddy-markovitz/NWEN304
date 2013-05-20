 #! /bin/bash
 #To run use command python testclient.py -t <target>
 #e.g python testclient.py -t /createGroup
import json, requests, sys

#Server information - Change this if anything changes.
server_info = {
	'server_url' : 'http://localhost',#"http://111.67.18.188",
	'port': "8080",
	'target' : "/createGroup"
}

json_headers = { 'Content-type' : 'application/json', 
				 'Accept' : 'text/plain'}

#This is the JSON data we will be using to send to the server.
data = {
	'phone_number':'42377348',
	'password' : 'secret',
	'group_name':':D:D', 
	'origin':'Narnia', 
	'destination':'The Wardrobe', 
	'arival_time':'12:00:00', 
	'departure_time':'13:00:00', 
	'seats':'6', 
	'days':'1111111'
}




#Pretty colours! ASCII CODES YAY!
HEADER    =    '\033[95m'
OKBLUE    =    '\033[94m'
OKCYAN    =    '\033[36m'
OKGREEN   =    '\033[92m'
WARNING   =    '\033[93m'
FAIL      =    '\033[91m'
ENDC      =    '\033[0m'
BOLD      =    '\033[1m'
UNDERLINE =    '\033[4m'
NEGATIVE  =    '\033[7m'


full_path = "%(server_url)s:%(port)s%(target)s" % server_info



#Check the command params!
if "-t" in sys.argv:
	loc = sys.argv.index("-t")
	new_target = None
	try:
		new_target = sys.argv[loc+1]
		server_info["target"] = new_target
	except:
		print FAIL + "Failed to load target (Did you remember to type it in after -t?)" + ENDC


#Pretty colours! Keep the user updated about what is happeni
print HEADER + "Sending POST to " + BOLD + UNDERLINE + full_path + ENDC

try:
	r = requests.post(full_path,data=json.dumps(data),headers=json_headers)

	print OKCYAN + "Content Type:", r.headers['content-type'] +ENDC

	print WARNING + "Status Code:" + str(r.status_code) + "\n" + r.text + ENDC
		

except requests.exceptions.ConnectionError:
	print FAIL + "Connection Refused to ", full_path + ". Server is probably down." + ENDC
