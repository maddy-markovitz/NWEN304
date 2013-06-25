#
# NWEN 304 Project 3
# <insert project name here, when we've decided on it...>
# Server
#

# 1st arg => port number; 2nd arg => host

#
# IDEAS:
#   o   change db users.name to users.user_name (consistency)
#   o   remove extraneous 'get' from routes (not methods)
#
# TODO (features):
#   o   atm, 'driverOf' is a subset of 'passengerOf'. is this the desired behaviour?
#   o   user notification queue, group notifications
#   o   group gps broadcast (use notification queues?)
#
# TODO (other):
#   o   test pretty much everything
#   o   use 'with _dbcon:' to make changes to database
#
#

import json, sqlite3, sys, uuid, time, traceback, hashlib
from os import urandom
from bottle import route, run, template, get, post, delete, put, request, response, abort, HTTPError
from Levenshtein import distance
from Queue import PriorityQueue

# Backdoor user. If no session id is supplied in a request and this is enabled,
# a session for the user with id _BD_USER will be used.
# set _BD_USER to >= 0 to use
_BD_USER = 1
_BD_SESSION = None

_dataBasePath = "CarPool.db"
# default host: all interfaces
_host = "0.0.0.0"
_port = 8080

# db connection
# using ? in the SQL protects against injection
_dbcon = None

# seconds each session lasts for
_session_ttl = 3600
# dict of session ids to sessions
_sessions = {}

# tuples of db columns for returning in json. initialised in main.
_group_fields = None
_user_fields = None

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
        # sessions don't autorenew atm because client has to be able to deal with it anyway.\
        if s.expired():
            abort(401, 'Session expired.')
        return s
    except HTTPError:
        raise
    except:
        if _BD_USER >= 0:
            # prevent backdoor session from expiring
            if _BD_SESSION.expired():
                _BD_SESSION = Session(_BD_USER)
            return _BD_SESSION
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
        
        # create the group, add entry into usersToGroups
        try:
            _dbcon.execute('INSERT INTO groups VALUES(?,?,?,?,?,?,?,?,?)',
                (s.user_id, None, name, origin, destin, t_arr, t_dep, seats, days))
            # get group_id
            group_id = _dbcon.execute('SELECT * FROM groups WHERE group_name = ?', (name,)).fetchone()['group_id']
            # add to usersToGroups
            _dbcon.execute('INSERT INTO usersToGroups VALUES(?,?)', (s.user_id, group_id))
            _dbcon.commit()
        finally:
            _dbcon.rollback()
        
        # TODO return group info?
        return { }
        
    except HTTPError:
        raise
    except:
        print('Bad create group request.')
        traceback.print_exc()
        abort(400, 'Bad create group request.')

# API method to delete a goup
@delete('/group')
def deleteGroup():
    s = getSession()
    
    # TODO test this
    # also, do we need security on this?
    # ie, you can only delete a group if you own it
    
    try:
        group_id = request.json['group_id']
        try:
            # Delete group from groups table
            _dbcon.execute("DELETE FROM groups WHERE group_id = ?", (group_id))
            # Delete all entries from usersToGroups for group
            _dbcon.execute("DELETE FROM usersToGroups WHERE group_id = ?", (group_id))
            _dbcon.commit()
        finally:
            _dbcon.rollback()
    except HTTPError:
        raise
    except:
        print('Bad delete group request.')
        traceback.print_exc()
        abort(400, 'Bad delete group request.')

# API method to get everything for a group
@get('/group')
def getGroup():
    s = getSession()

    # TODO test this
    # TODO accept name aswell
    
    try:
        group_id = request.json['group_id']
        res = {}
        row = dbcon.execute("SELECT * FROM groups where group_id = ?", (group_id,)).fetchone()
        for g_field in _group_fields:
            res[g_field] = row[g_field]
        return res
    except HTTPError:
        raise
    except:
        print('Bad get group request.')
        traceback.print_exc()
        abort(400, 'Bad get group request.')

# API method to update stuff for a group
@put('/group')
def updateGroup():
    s = getSession()
    
    # TODO
    
    try:
        group_id = request.json['group_id']
        
    except HTTPError:
        raise
    except:
        print('Bad update group request.')
        traceback.print_exc()
        abort(400, 'Bad update group request.')

# API method to get groups user drives
# TODO rename route to 'driverGroups'
@get('/getDriverGroups')
def getDriverGroups():
    s = getSession()
    
    try:
        res = {}
        # find all groups owned by user
        for row in _dbcon.execute("SELECT * FROM groups WHERE user_id = ?", (s.user_id,)):
            group = {}
            for g_field in _group_fields:
                group[g_field] = row[g_field]
            res[group['group_id']] = group
        return res
    except HTTPError:
        raise
    except:
        print('Bad get driver groups request.')
        traceback.print_exc()
        abort(400, 'Bad get driver groups request.')

# API method to get groups user is a passenger (or driver) of
# TODO rename route to 'passengerGroups'
@get('/getPassengerGroups')
def getPassengerGroups():
    s = getSession()
    
    # TODO test this (properly)
    
    try:
        res = {}
        # use the junction table. join on group id, select by user id
        for row in _dbcon.execute("""
                                SELECT groups.* FROM groups
                                JOIN usersToGroups ON groups.group_id = usersToGroups.group_id
                                WHERE usersToGroups.user_id = ?
                                """, (s.user_id,)):
            group = {}
            for g_field in _group_fields:
                group[g_field] = row[g_field]
            res[group['group_id']] = group
        return res
    except HTTPError:
        raise
    except:
        print('Bad get passenger groups request.')
        traceback.print_exc()
        abort(400, 'Bad get passenger groups request.')

# API method to get passengers (including driver) of a specified group
# TODO rename route to 'passengers'
@get('/getPassengers')
def getPassengers():
    s = getSession()
    
    # TODO test this
    # also, do we need security on this?
    # ie you can't see passengers in a group if you're not in it
    
    try:
        group_id = request.json['group_id']
        res = {}
        # use the junction table. join on user id, select by group id
        for row in _dbcon.execute("""
                                SELECT users.* FROM users
                                JOIN usersToGroups ON users.user_id = usersToGroups.user_id
                                WHERE usersToGroups.group_id = ?
                                """, (group_id,)):
            user = {}
            for u_field in _user_fields:
                user[u_field] = row[u_field]
            res[user['user_id']] = user
        # check the requesting user is in the group
        if not s.user_id in res:
            # uncomment for security
            # abort(401, 'Only members of a group can view its passengers.')
            pass
        return res
    except HTTPError:
        raise
    except:
        print('Bad get passengers request.')
        traceback.print_exc()
        abort(400, 'Bad get passengers request.')

# API method to add a passenger to a group
@post('passengers')
def addPassenger():
    s = getSession()
    
    # TODO
    # also, do we need sucurity on this?
    # ie you can't add users to a group unless you own that group
    
    try:
        group_id = request.json['group_id']
        user_id = request.json['user_id']
        
    except HTTPError:
        raise
    except:
        print('Bad add passenger request.')
        traceback.print_exc()
        abort(400, 'Bad add passenger request.')

# API method to delete a passenger from a group. User id of -1 means 'delete me'.
@delete('passengers')
def deletePassenger():
    s = getSession()
    
    # TODO
    # also, do we need sucurity on this?
    # ie you can't delete users from a group unless you own that group or are the deletee
    
    try:
        group_id = request.json['group_id']
        user_id = request.json['user_id']
        # enable easy self-deletion. invalid id => delete me
        if user_id < 0:
            user_id = s.user_id
        
    except HTTPError:
        raise
    except:
        print('Bad delete passenger request.')
        traceback.print_exc()
        abort(400, 'Bad delete passenger request.')



# API method to search for a group by phone number or group name
@get('search')
def search():
    s = getSession()
    
    # TODO
    # test this function
    
    try:
        res = {}
        phone_number = request.json['phone_number']
        group_name = request.json['group_name']
        
        pq = PriorityQueue(0)
        
        
        #get all the groups whos drivers phone number matches the query exactly
        for row in _dbcon.execute("SELECT * FROM users WHERE phone_number  = ?", (phone_number,)):
            user = row[user_id]
            for row2 in _dbcon.execute("SELECT * FROM groups WHERE user_id  = ?", (user,)):
                #create group object from row
                group = {}
                for g_field in _group_fields:
                    group[g_field] = row[g_field]
                    
                #add group to priority queue with priority .1
                pq.add(.1,group)
        
        
        #get all the groups with a name resembles the query (2/3 of the characters match)
        for row in _dbcon.execute("SELECT * FROM groups"):
            #create group object from row
            group = {}
            for g_field in _group_fields:
                group[g_field] = row[g_field]
                
            #add group to priority queue with edit distance / length as their priority
            priority = distance(group['group_name'],group_name)
            ps.add(priority,group)
                
            #add the groups where 2/3 of the charatcers match
            count = 0
            while True:
                g = ps.get()
                if g[0] <= .75:
                    res[count] = g[1]
                    count = count+1     
        return res
    except HTTPError:
        raise
    except:
        print('Bad search request.')
        traceback.print_exc()
        abort(400, 'Bad search request.')

# API method to invite a user to your group
@get('invite')
def search():
    s = getSession()
    
    # TODO
    # everything
    
    try:
        res = {}
        phone_number = request.json['phone_number']
        group_name = request.json['group_name']
        
        #get the user with the given phone number
        user_id = _dbcon.execute("SELECT * FROM users WHERE phone_number  = ?", (phone_number,))[user_id]
        
        #add invitation to user with user_id's notifications
        
         
        return res
    except HTTPError:
        raise
    except:
        print('Bad invite request.')
        traceback.print_exc()
        abort(400, 'Bad invite request.')

# 'Main method' : this needs to be at the bottom
if __name__ == '__main__':
    # init db as necessary
    _dbcon = sqlite3.connect(_dataBasePath)
    _dbcon.row_factory = sqlite3.Row
    try:
        # these tuples are used for returning json, hence why 'salt' and 'hash' aren't in _user_fields.
        #
        # >> IF YOU CHANGE THE COLUMNS, CHANGE THE TUPLES !!!! <<
        #
        _group_fields = ('user_id', 'group_id', 'group_name', 'origin', 'destination', 'arrival_time', 'departure_time', 'seats', 'days')
        _user_fields = ('user_id', 'name', 'phone_number')
        # create tables if needed
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
        _dbcon.execute("""
                    CREATE TABLE IF NOT EXISTS usersToGroups (
                        user_id INTEGER NOT NULL,
                        group_id INTEGER NOT NULL,
                        PRIMARY KEY (user_id, group_id),
                        FOREIGN KEY (user_id) REFERENCES users(user_id),
                        FOREIGN KEY (group_id) REFERENCES groups(group_id)
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
    
    if _BD_USER >= 0:
        _BD_SESSION = Session(_BD_USER)
    
    # run that server
    run(host=_host,port=_port,)

# END.






























