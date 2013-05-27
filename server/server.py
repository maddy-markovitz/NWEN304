import json, sqlite3, sys, uuid, time, traceback, hashlib
from os import urandom
from bottle import route, run, template, get, post, delete, put, request, response, abort, HTTPError

#
# TODO link groups with their passengers
#

_dataBasePath = "CarPool.db"
# default host: all interfaces
_host = "0.0.0.0"
_port = 8080

# db connection
# using ? in the SQL protects against injection
_dbcon = sqlite3.connect(_dataBasePath)
_dbcon.row_factory = sqlite3.Row

# seconds each session lasts for
_session_ttl = 3600
# dict of session ids to sessions
_sessions = {}

# a user session
class Session:
    def __init__(self, user_id_):
        self.id = uuid.uuid4()
        self.user_id = user_id_
        self.created = long(time.time())
        self.expires = self.created + long(_session_ttl)

    def ttl(self):
        return self.expires - long(time.time())
    
    def expired(self):
        return long(time.time()) >= self.expires

# get the session object for the current request, or abort HTTP 401
def getSession():
    try:
        s = _sessions[uuid.UUID(request.json['session_id'])]
        if s.expired():
            abort(401, 'Session expired.')
        return s
    except:
        print('Invalid session id.')
        traceback.print_exc()
        abort(401, 'Invalid session id.')

# check a user's password against the db. True iff authentication successful
def authenticate(user, pword):
    try:
        row = _dbcon.execute('SELECT * FROM users WHERE phone_number = ?', (int(user),)).fetchone()
        pwd_salt = row['salt']
        pwd_hash = row['hash']
        if hashlib.sha512(pwd_salt + pword).hexdigest() == pwd_hash:
            return True
    except:
        print('Failure in authenticate()')
        traceback.print_exc()
    return False

# get the unique id for a user (phone number)
def userID(user):
    try:
        return _dbcon.execute('SELECT * FROM users WHERE phone_number = ?', (int(user),)).fetchone()[0]
    except:
        return -1

# API method to register a new user
@post('/register')
def register():
    try:
        phone = int(request.json['phone_number'])
        name = request.json['name']
        pword = request.json['password']
        user = phone
        
        if userID(user) >= 0:
            abort(400, 'Phone number already in use.')
        
        print('register() : phone=%s, name=%s' % (phone, name))
        
        # TODO sanity check ?
        
        pwd_salt = hashlib.sha512(urandom(128)).hexdigest()
        pwd_hash = hashlib.sha512(pwd_salt + pword).hexdigest()
        
        try:
            _dbcon.execute('INSERT INTO users VALUES(?, ?, ?, ?, ?)', (None, name, phone, pwd_salt, pwd_hash))
            _dbcon.commit()
        finally:
            _dbcon.rollback()
        
        # init session
        s = Session(userID(user))
        _sessions[s.id] = s
        
        # return session 'cookie'
        return { 'session_id' : s.id.hex, 'session_expires' : s.expires }
        
    except:
        print('Bad register request:')
        traceback.print_exc();
        abort(400, 'Bad register request.')

# API method to login a user
@post('/login')
def login():
    try:
        user = request.json['phone_number']
        pword = request.json['password']
        
        # authenticate
        if not authenticate(user, pword):
            print('Invalid login : user = %s' % user)
            abort(401, 'Invalid user or password.')
        
        # init session (if logged in, resets ttl)
        s = Session(userID(user))
        _sessions[s.id] = s
        
        # return session 'cookie'
        return { 'session_id' : s.id.hex, 'session_expires' : s.expires }
        
    except HTTPError:
        raise
    except:
        print('Bad login request:')
        traceback.print_exc()
        abort(400, 'Bad login request.')

# API method to create a group
@post('/createGroup')
def createGroup():
    s = getSession()
    try:
        group = request.json['group']
        name = group['name']
        origin = group['origin']
        destin = group['destination']
        t_arr = group['arrival_time']
        t_dep = group['departure_time']
        seats = group['seats']
        days = group['days']
        
        print('createGroup() : user_id=%s, name=%s' % (s.user_id, name))
        
        # TODO sanity check
        
        # check the group doesn't already exist
        # mainly to return helpful errors
        if _dbcon.execute('SELECT * FROM groups WHERE group_name = ?', (name,)).fetchone():
            print('createGroup() : group %s already exists.' % name)
            abort(400, 'A group by that name already exists.')
        
        # create the group
        try:
            _dbcon.execute('INSERT INTO groups VALUES(?,?,?,?,?,?,?,?,?)',
                (s.user_id, None, name, origin, destin, t_arr, t_dep, seats, days))
            _dbcon.commit()
        finally:
            _dbcon.rollback()
        
        # TODO return { group : {...} }
        return { }
        
    except HTTPError:
        raise
    except:
        print('Bad create group request.')
        traceback.print_exc()
        abort(400, 'Bad create group request.')

# API method to delete a goup
@delete('/group/<id:int>')
def deleteGroup():
    s = getSession()
    try:
        # TODO deletion by name (or id?)
        
        pass
    except:
        print('Bad delete group request.')
        traceback.print_exc()
        abort(400, 'Bad delete group request.')

# API method to get everything for a group (?)
@get('/group/<id:int>')
def getGroup():
    s = getSession()
    # TODO

# API method to update stuff for a group (?)
@put('/group/<id:int>')
def updateGroup():
    s = getSession()
    # TODO

# API method to get groups user drives
@get('/getDriverGroups')
def getDriverGroups():
    s = getSession()
    # TODO
    return {'Key' : ':D'}

# API method to get groups user is a passenger of
@get('/getPassengerGroups')
def getPassengerGroups():
    s = getSession()
    # TODO
    return {'Key' : ':P'}

# this needs to be at the bottom
if __name__ == '__main__':
    # init db as necessary
    try:
        _dbcon.execute("""
                    CREATE TABLE IF NOT EXISTS groups (
                        user_id INTEGER NOT NULL,
                        group_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        group_name TEXT UNIQUE,
                        origin TEXT,
                        destination TEXT,
                        arrival_time DATETIME,
                        departure_time DATETIME,
                        seats INTEGER,
                        days CHAR (7),
                        FOREIGN KEY(user_id) REFERENCES users(user_id)
                    );
                    """)
        _dbcon.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        phone_number INTEGER NOT NULL UNIQUE,
                        salt CHAR (128),
                        hash CHAR (128)
                    );
                    """)
        _dbcon.commit()
    finally:
        _dbcon.rollback()
    
    # 1st arg => port number; 2nd arg => host
    if len(sys.argv) > 1:
        _port = int(sys.argv[1])
    if len(sys.argv) > 2:
        _host = sys.argv[2]
        
    # run that server
    run(host=_host,port=_port,)

	



