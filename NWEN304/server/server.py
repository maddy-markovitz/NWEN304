import json, sqlite3, sys, uuid, time, traceback, hashlib
from os import urandom
from bottle import route, run, template, get, post, delete, put, request, response, abort, HTTPError

#
# TODO am i dealing with the db connection / cursor correctly?
#
# TODO protect against SQL injection
#
# TODO link groups with their passengers
#

_dataBasePath = "CarPool.db"
# default host: all interfaces
_host = "0.0.0.0"
_port = 8080


_session_ttl = 3600
_sessions = {}

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

def authenticate(user, pword):
    try:
        con = sqlite3.connect(_dataBasePath)
        with con:
            cur = con.cursor()
            cur.execute('SELECT * FROM users WHERE phone_number = ?', (int(user),))
            row = cur.fetchone()
            salt = row[3]
            hash = row[4]
            if hashlib.sha256(salt + pword).hexdigest() == hash:
                return True
    except:
        print('Failure in authenticate()')
        traceback.print_exc()
    return False

def userID(user):
    try:
        con = sqlite3.connect(_dataBasePath)
        with con:
            cur = con.cursor()
            cur.execute('SELECT * FROM users WHERE phone_number = ?', (int(user),))
            return cur.fetchone()[0]
    except:
        return -1

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
        
        salt = hashlib.sha256(urandom(64)).hexdigest()
        hash = hashlib.sha256(salt + pword).hexdigest()
        
        con = sqlite3.connect(_dataBasePath)
        with con:
            cur = con.cursor()
            cur.execute('INSERT INTO users(name, phone_number, salt, hash) VALUES(?, ?, ?, ?)', (name, phone, salt, hash))
        
        # init session
        s = Session(userID(user))
        _sessions[s.id] = s
        
        # return session 'cookie'
        return { 'session_id' : s.id.hex, 'session_expires' : s.expires }
        
    except:
        print('Bad register request:')
        traceback.print_exc();
        abort(400, 'Bad register request.')

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
        
        con = sqlite3.connect(_dataBasePath)
        with con:
            cur = con.cursor()
            cur.execute('SELECT * FROM groups WHERE group_name = ?', (name,))
            if len(cur.fetchall()) > 0:
                print('createGroup() : group %s already exists.' % name)
                abort(400, 'A group by that name already exists.')
            cur.execute('INSERT INTO groups VALUES(?,?,?,?,?,?,?,?,?)',
                (s.user_id, None, name, origin, destin, t_arr, t_dep, seats, days))
        
        # TODO return { group : {...} }
        return { }
        
    except HTTPError:
        raise
    except:
        print('Bad create group request.')
        traceback.print_exc()
        abort(400, 'Bad create group request.')

@delete('/group')
def deleteGroup():
    s = getSession()
    try:
        # TODO deletion by name (or id?)
        
        pass
    except:
        print('Bad delete group request.')
        traceback.print_exc()
        abort(400, 'Bad delete group request.')

@get('/group')
def getGroup():
    s = getSession()
    # TODO

@put('/group')
def updateGroup():
    s = getSession()
    # TODO

@get('/getDriverGroups')
def getDriverGroups():
    s = getSession()
    # TODO
        name = group['name']
        con = sqlite3.connect(_dataBasePath)
        with con:
            cur = con.cursor()
          for row in  cur.execute('SELECT * FROM groups WHERE user_id = ?', (name,)):
		print row

        
        # TODO return { group : {...} }
        return { }
    return {'Key' : ':D'}

@get('/getPassengerGroups')
def getPassengerGroups():
    s = getSession()
    # TODO
    return {'Key' : ':P'}

# this needs to be at the bottom
if __name__ == '__main__':
    # init db as necessary
    con = sqlite3.connect(_dataBasePath)
    with con:
        cur = con.cursor()
        cur.execute("""
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
        cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        phone_number INTEGER NOT NULL UNIQUE,
                        salt CHAR (64),
                        hash CHAR (64)
                    );
                    """)
    
    # 1st arg => port number; 2nd arg => host
    if len(sys.argv) > 1:
        _port = int(sys.argv[1])
    if len(sys.argv) > 2:
        _host = sys.argv[2]
        
    # run that server
    run(host=_host,port=_port,)

	



