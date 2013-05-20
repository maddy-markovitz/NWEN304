import json, sqlite3, sys
from bottle import route, run, template, get, post, request, response, HTTPError

_dataBasePath = "CarPool.db"
_host = "localhost"
_port = 8080

conn = sqlite3.connect(_dataBasePath)
c = conn.cursor()

@post('/createGroup')
def createGroup():

    #get json payload
	response.content_type = 'application/json'
	json = request.json


	#retrieve users id from database
	#checks phone number & password
	try:
		c.execute("SELECT * FROM users WHERE phone_number = ? AND password = ?", 
			     (int(json['phone_number'].encode('ascii','ignore'))
			     ,json['password']))

		result = c.fetchall()
		id = result[0][0]
	except IndexError:
		print("Invalid user credentials")
		raise HTTPError(400, "Invalid User Credentials")
		#return "Error - Invalid User Credentials"
	
	#add group to database (requires user id from above!)
	try:
		c.execute("INSERT INTO groups VALUES (?,?,?,?,?,?,?,?,?)", 
			(id, None, json['group_name'],json['origin'], json['destination'],
				json['arival_time'],json['departure_time'],json['seats'],json['days']))
		conn.commit()

	except sqlite3.IntegrityError:
		print("Invalid group name, duplicate exists")
		raise HTTPError(400, "A group with this name already exists")
		#return "Error - A group with this name already exists"
		
	print("Group added")
	return "Group Added"


@get('/getGroups')
def getGroups():
    return {'Key' : ':D'}



	
run(host=_host,port=_port,)


