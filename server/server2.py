#
# NWEN 304 Project 3
# <insert project name here, when we've decided on it...>
# Server
#

# 1st arg => port number; 2nd arg => host

#
# Shiny new code: Group and User classes, with db caching.
#
# RENAMES:
#   o   POST /createGroup -> POST /group
#   o   GET /getDriverGroups -> GET /driverGroups
#   o   GET /getPassengerGroups -> GET /passengerGroups
#   o   GET /getPassengers -> GET /passengers
#
#   o   DB user.name -> users.user_name (also in JSON responses)
#
# OTHER CHANGES:
#   o   JSON for createGroup() no longer wrapped in a 'group' object
#   o   added NOT NULL to all db columns
#   o   json field tuples no longer used
#

#
# IDEAS:
#
# TODO (features):
#   o   atm, 'driverOf' is a subset of 'passengerOf'. is this the desired behaviour?
#   o   user notification queue, group notifications
#   o   group gps broadcast (use notification queues?)
#
# TODO (other):
#   o   TEST EVERYTHING
#   o   use 'with _dbcon:' to make changes to database
#
#

import json, sqlite3, sys, uuid, time, traceback, hashlib
from os import urandom
from bottle import route, run, template, get, post, delete, put, request, response, abort, HTTPError

# Backdoor user. If no session id is supplied in a request and this is enabled,
# a session for the user with id _BD_USER_ID will be used.
# set _BD_USER_ID to >= 0 to use
_BD_USER_ID = 1
_BD_SESSION = None

_dataBasePath = "CarPool.db"
# default host: all interfaces
_host = "0.0.0.0"
_port = 8080

# db connection
# using ? in the SQL protects against injection
_dbcon = sqlite3.connect(_dataBasePath)
_dbcon.row_factory = sqlite3.Row

# Reset
ColorOff="\033[0m"

# Regular Colors
Black="\033[0;30m"
Red="\033[0;31m"
Green="\033[0;32m"
Yellow="\033[0;33m"
Blue="\033[0;34m"
Purple="\033[0;35m"
Cyan="\033[0;36m"
White="\033[0;37m"

# Bold
BBlack="\033[1;30m"
BRed="\033[1;31m"
BGreen="\033[1;32m"
BYellow="\033[1;33m"
BBlue="\033[1;34m"
BPurple="\033[1;35m"
BCyan="\033[1;36m"
BWhite="\033[1;37m"

class NoSuchUserError(Exception):
    def __init__(self, user_id=None, phone=None):
        if user_id != None:
            self.message = 'No user found with id=%d.' % int(user_id)
        elif phone != None:
            self.message = 'No user found with phone_number=%d.' % int(phone)
        else:
            self.message = 'No arguments supplied.'

class User(object):
    """ A user. Persistent (at least in memory, ie. doesn't die with or rely on a session).
    do not use constructor directly, call User.forID() or User.forPhone()."""
    
    # dict of user ids to users
    _by_id = {}
    # dict of phone numbers to users
    _by_phone = {}
    
    @classmethod
    def forAny(cls, user_id=None, phone=None):
        """ Gets a user by id or phone. """
        if user_id != None:
            return User.forID(user_id)
        elif phone != None:
            return User.forPhone(phone)
    
    @classmethod
    def forID(cls, user_id):
        """ Get a user by id. Throws NoSuchUserError. """
        user_id = int(user_id)
        try:
            return cls._by_id[user_id]
        except KeyError:
            # this may throw NoSuchUserError
            user = User(user_id=user_id)
            cls._by_id[user.id] = user
            cls._by_phone[user.phone] = user
            return user
    
    @classmethod
    def forPhone(cls, phone):
        """ Get a user by phone number. Throws NoSuchUserError. """
        phone = int(phone)
        try:
            return cls._by_phone[phone]
        except KeyError:
            # this may throw NoSuchUserError
            user = User(phone=phone)
            cls._by_id[user.id] = user
            cls._by_phone[user.phone] = user
            return user
    
    @classmethod
    def create(cls, phone, name, password):
        """ Create a user. Throws if phone not unique (DB check)."""
        
        # TODO sanity check ?
        
        pwd_salt = hashlib.sha512(urandom(128)).hexdigest()
        pwd_hash = hashlib.sha512(pwd_salt + password).hexdigest()
        try:
            _dbcon.execute('INSERT INTO users VALUES(?, ?, ?, ?, ?)', (None, name, phone, pwd_salt, pwd_hash))
            _dbcon.commit()
        finally:
            _dbcon.rollback()
        user = User.forPhone(phone)
        print 'User.create() : %s' % user
        return user
    
    def __init__(self, user_id=None, phone=None):
        # get appropriate row from db
        row = None
        if user_id != None:
            row = _dbcon.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
        elif phone != None:
            row = _dbcon.execute('SELECT * FROM users WHERE phone_number = ?', (phone,)).fetchone()
        # throw error if not found
        if not row:
            raise NoSuchUserError(user_id=user_id, phone=phone)
        self.id = row['user_id']
        self.name = row['user_name']
        self.phone = row['phone_number']
        self.pwd_salt = row['salt']
        self.pwd_hash = row['hash']
        # init notification queue. poll from index 0
        self._notifications = []
    
    def authenticate(self, password):
        """ Authenticate a user by password. Returns True iff successfull. """
        return hashlib.sha512(self.pwd_salt + password).hexdigest() == self.pwd_hash
    
    def pollNotification(self):
        """ Return the next queued notification, or None. """
        try:
            return _notifications.pop(0)
        except IndexError:
            return None
    
    def __str__(self):
        return 'User[id=%d,name=%s]' % (self.id, self.name)
    
    def toDict(self):
        """ Create a dict representation for returning as JSON. """
        d = {}
        d['user_id'] = self.id
        d['user_name'] = self.name
        d['phone_number'] = self.phone
        return d

class Notification(object):
    """ TODO """
    
    def __init__(self):
        pass

class NoSuchGroupError(Exception):
    def __init__(self, group_id=None, group_name=None):
        if group_id != None:
            self.message = 'No group found with id=%d.' % int(group_id)
        elif group_name != None:
            self.message = 'No group found with name=%s.' % group_name
        else:
            self.message = 'No arguments supplied.'

class Group(object):
    """ A carpool group. Persistent. Do not call constructor directly, use Group.forID(), Group.forName()
        Group.forUser() or Group.forOwner(). """
    
    # groups by id
    _by_id = {}
    # groups by name
    _by_name = {}
    # groups by owner, user_id -> tuple of groups
    _by_owner_id = {}
    # groups by user, user_id -> tuple of groups
    _by_user_id = {}
    
    @classmethod
    def forAny(cls, group_id=None, group_name=None):
        """ Gets a group by id or name. """
        if group_id != None:
            return Group.forID(group_id)
        elif group_name != None:
            return Group.forName(group_name)
    
    @classmethod
    def forID(cls, group_id):
        """ Get a group by id. Throws NoSuchGroupError. """
        group_id = int(group_id)
        try:
            return cls._by_id[group_id]
        except KeyError:
            # this may throw NoSuchGroupError
            group = Group(group_id=group_id)
            cls._by_id[group.id] = group
            cls._by_name[group.name] = group
            return group
    
    @classmethod
    def forName(cls, group_name):
        """ Get a group by name. Throws NoSuchGroupError. """
        group_name = str(group_name)
        try:
            return cls._by_name[group_name]
        except KeyError:
            # this may throw NoSuchGroupError
            group = Group(group_name=group_name)
            cls._by_id[group.id] = group
            cls._by_name[group.name] = group
            return group
    
    @classmethod
    def forUser(cls, user):
        """ Gets a tuple of all groups a user is in. """
        if not user:
            return ()
        try:
            return cls._by_user_id[user.id]
        except KeyError:
            groups = []
            # don't even need the fancy junction table command
            for row in _dbcon.execute('SELECT * FROM usersToGroups WHERE user_id = ?', (user.id,)):
                group_id = row['group_id']
                try:
                    groups.append(Group.forID(group_id))
                except NoSuchGroupError:
                    print Red + 'DBCHECK: %s is in non-existent group with id=%d.' % (user, group_id) + ColorOff
            groups = tuple(groups)
            cls._by_user_id[user.id] = groups
            return groups
    
    @classmethod
    def forOwner(cls, owner):
        """ Gets a tuple of all groups owned by a user. """
        if not owner:
            return ()
        try:
            return cls._by_owner_id[owner.id]
        except KeyError:
            groups = []
            for row in _dbcon.execute("SELECT * FROM groups WHERE user_id = ?", (owner.id,)):
                groups.append(Group.forID(row['group_id']))
            groups = tuple(groups)
            cls._by_owner_id[owner.id] = groups
            return groups
    
    @classmethod
    def create(cls, owner, name, origin, destination, arrival, departure, seats, days):
        """ Create a group. Throws if name isn't unique (DB check). """
        if not owner:
            raise Exception('Owner must not be None.')
        
        # TODO sanity check
        
        # create the group, add entry into usersToGroups
        try:
            _dbcon.execute('INSERT INTO groups VALUES(?,?,?,?,?,?,?,?,?)',
                (owner.id, None, name, origin, destination, arrival, departure, seats, days))
            # get group_id
            group_id = _dbcon.execute('SELECT * FROM groups WHERE group_name = ?', (name,)).fetchone()['group_id']
            # add to usersToGroups
            _dbcon.execute('INSERT INTO usersToGroups VALUES(?,?)', (owner.id, group_id))
            _dbcon.commit()
        finally:
            _dbcon.rollback()
        group = Group.forName(name)
        print 'Group.create(): %s' % group
        # cache coherence
        cls._by_user_id.pop(owner.id, None)
        cls._by_owner_id.pop(owner.id, None)
        return group
    
    def __init__(self, group_id=None, group_name=None):
        # get appropriate row from db
        g_row = None
        if group_id != None:
            g_row = _dbcon.execute('SELECT * FROM groups WHERE group_id = ?', (group_id,)).fetchone()
        elif group_name != None:
            g_row = _dbcon.execute('SELECT * FROM groups WHERE group_name = ?', (group_name,)).fetchone()
        # error if it doesn't exist
        if not g_row:
            raise NoSuchGroupError(group_id=group_id, group_name=group_name)
        self._owner = User.forID(g_row['user_id'])
        self._id = g_row['group_id']
        self._name = g_row['group_name']
        self._origin = g_row['origin']
        self._destination = g_row['destination']
        self._arrival = g_row['arrival_time']
        self._departure = g_row['departure_time']
        self._seats = g_row['seats']
        self._days = g_row['days']
        self._users = None
    
    def update(self, name=None, origin=None, destination=None, arrival=None, departure=None, seats=None, days=None):
        """ Update any subset of the editable group parameters. """
        # skip empty updates
        if (name, origin, destination, arrival, departure, seats, days) == (None,) * 7:
            return
        # TODO sanity check? relying on db constraints atm
        # updating the name will fail if not unique because of this
        try:
            _dbcon.execute("""
                        UPDATE groups
                        SET group_name = ?, origin = ?, destination = ?,
                        arrival_time = ?, departure_time = ?, seats = ?, days = ?
                        WHERE group_id = ?
                        """,
                        (name if name != None else self._name,
                        origin if origin != None else self._origin,
                        destination if destination != None else self._destination,
                        arrival if arrival != None else self._arrival,
                        departure if departure != None else self._departure,
                        seats if seats != None else self._seats,
                        days if days != None else self._days,
                        self.id))
            _dbcon.commit()
        finally:
            _dbcon.rollback()
        # db update succeeded, update fields
        g_row = _dbcon.execute('SELECT * FROM groups WHERE group_id = ?', (self.id,)).fetchone()
        self._name = g_row['group_name']
        self._origin = g_row['origin']
        self._destination = g_row['destination']
        self._arrival = g_row['arrival_time']
        self._departure = g_row['departure_time']
        self._seats = g_row['seats']
        self._days = g_row['days']
    
    @property
    def owner(self):
        return self._owner
    
    @property
    def id(self):
        return self._id
    
    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, name):
        self.update(name=name)
    
    @property
    def users(self):
        if not self._users:
            users = []
            # pull from db
            for row in _dbcon.execute('SELECT * FROM usersToGroups WHERE group_id = ?', (self.id,)):
                user_id = row['user_id']
                try:
                    users.append(User.forID(user_id))
                except NoSuchUserError:
                    print Red + 'DBCHECK: %s has non-existent user with id=%d.' % (self, user_id) + ColorOff
            if not self.owner in users:
                users.append(self.owner)
                print Yellow + 'DBCHECK: Owner of %s is not in its users. Fixing.' % self + ColorOff
                try:
                    # add to db
                    _dbcon.execute('INSERT INTO usersToGroups VALUES(?,?)', (self.owner.id, self.id))
                    _dbcon.commit()
                except:
                    _dbcon.rollback()
                    print Red + 'DBCHECK: Error fixing %s.' % self + ColorOff
                    traceback.print_exc()
            self._users = tuple(users)
        return self._users
    
    @property
    def origin(self):
        return self._origin
    
    @origin.setter
    def origin(self, origin):
        self.update(origin=origin)
    
    @property
    def destination(self):
        return self._destination
    
    @destination.setter
    def destination(self, destination):
        self.update(destination=destination)
    
    @property
    def arrival(self):
        return self._arrival
    
    @arrival.setter
    def arrival(self, arrival):
        self.update(arrival=arrival)
    
    @property
    def departure(self):
        return self._departure
    
    @departure.setter
    def departure(self, departure):
        self.update(departure=departure)
    
    @property
    def seats(self):
        return self._seats
    
    @seats.setter
    def seats(self, seats):
        self.update(seats=seats)
    
    @property
    def days(self):
        return self._days
    
    @days.setter
    def days(self, days):
        self.update(days=days)
    
    def __contains__(self, user):
        """ True iff user is in this group (driver or passenger). """
        return user in self.users
    
    def __len__(self):
        """ Return the number of users in this group. """
        return len(self.users)
    
    def addUser(self, user):
        """ Add a user to this group. """
        if not user:
            raise Exception('User must not be None.')
        if user in self:
            return
        try:
            # add to db
            # this appears to fail silently if self.id is no longer in the groups table
            _dbcon.execute('INSERT INTO usersToGroups VALUES(?,?)', (user.id, self.id))
            _dbcon.commit()
        finally:
            _dbcon.rollback()
        # cache coherence
        self._users = None
        Group._by_user_id.pop(user.id, None)
    
    def __iadd__(self, user):
        self.addUser(user)
        return self
    
    def deleteUser(self, user):
        """ Remove a user from this group. Throws if user is the owner. """
        if not user in self:
            return
        if user == self.owner:
            raise Exception('Cannot delete the owner of a group.')
        try:
            # remove from db
            _dbcon.execute('DELETE FROM usersToGroups WHERE user_id = ? AND group_id = ?', (user.id, self.id))
            _dbcon.commit()
        except:
            _dbcon.rollback()
        # cache coherence
        self._users = None
        Group._by_user_id.pop(user.id, None)
    
    def __isub__(self, user):
        self.deleteUser(user)
        return self
    
    def delete(self):
        """ Delete this group. """
        # need this later to uncache for these users
        users = self.users
        try:
            # Delete group from groups table
            _dbcon.execute("DELETE FROM groups WHERE group_id = ?", (self.id,))
            # Delete all entries from usersToGroups for group
            _dbcon.execute("DELETE FROM usersToGroups WHERE group_id = ?", (self.id,))
            _dbcon.commit()
        finally:
            _dbcon.rollback()
        # cache coherence
        Group._by_id.pop(self.id, None)
        Group._by_name.pop(self.name, None)
        Group._by_owner_id.pop(self.owner.id, None)
        self._users = None
        for user in users:
            Group._by_user_id.pop(user.id, None)
    
    def __iter__(self):
        """ Returns an iterator over the users in this group. """
        return self.users.__iter__()
    
    def __str__(self):
        return 'Group[id=%d,owner=%d,name=%s]' % (self.id, self.owner.id, self.name)
    
    def toDict(self):
        """ Create a dict representation for returning as JSON. """
        d = {}
        d['user_id'] = self.owner.id
        d['group_id'] = self.id
        d['group_name'] = self.name
        d['origin'] = self.origin
        d['destination'] = self.destination
        d['arrival_time'] = self.arrival
        d['departure_time'] = self.departure
        d['seats'] = self.seats
        d['days'] = self.days
        return d

class NoSuchSessionError(Exception):
    def __init__(self, session_id):
        self.message = 'No session found with session_id=%s.' % session_id

class Session(object):
    """ A user session. Do not call constructor directly, use Session.forUser(). """
    
    # seconds each session lasts for
    _ttl = 3600
    # dict of session ids to sessions
    _by_id = {}
    # dict of users to sessions
    _by_user = {}
    
    @classmethod
    def forID(cls, session_id):
        """ Get a session by session_id. """
        try:
            return cls._by_id[uuid.UUID(session_id)]
        except KeyError:
            raise NoSuchSessionError(session_id)
    
    @classmethod
    def forUser(cls, user):
        """ Get a session for a user. CREATES THE SESSION IF IT DOESN'T EXIST! """
        try:
            return cls._by_user[user]
        except KeyError:
            return Session(user)
    
    def __init__(self, user):
        if not user:
            raise Exception('User must not be None.')
        self.id = uuid.uuid4()
        self.user = user
        self.created = long(time.time())
        self.expires = self.created + Session._ttl
        # add to dicts
        Session._by_id[self.id] = self
        Session._by_user[self.user] = self
    
    @property
    def ttl(self):
        """ Get the time in seconds until this session expires. """
        return self.expires - long(time.time())
    
    @property
    def expired(self):
        """ Return True iff this session has expired. """
        return long(time.time()) >= self.expires
    
    def expire(self):
        """ Expire this session. """
        self.expires = long(time.time()) - 1
    
    def renew(self):
        """ Reset the expiry of this session as if it was created now. """
        self.expires = long(time.time()) + Session._ttl
    
    def __str__(self):
        return 'Session[user=%s,ttl=%d]' % (self.user, self.ttl)
    
    def toDict(self):
        """ Create a dict representation for returning as JSON. """
        return { 'session_id' : self.id.hex, 'session_expires' : self.expires }

def getSession():
    """ Get the session object for the current request, or abort HTTP 401. """
    try:
        s = Session.forID(request.json['session_id'])
        # sessions don't autorenew atm because client has to be able to deal with it anyway.
        if s.expired:
            abort(401, 'Session expired.')
        return s
    except HTTPError:
        raise
    except:
        if _BD_USER_ID >= 0:
            # prevent backdoor session from expiring
            _BD_SESSION.renew()
            return _BD_SESSION
        print 'Invalid session id.'
        traceback.print_exc()
        abort(401, 'Invalid session id.')

# API method to register a new user
@post('/register')
def register():
    try:
        phone = int(request.json['phone_number'])
        name = request.json['name']
        password = request.json['password']
        
        if User.forPhone(phone):
            print 'register(): phone %d in use.' % phone
            abort(400, 'Phone number already in use.')
        
        user = User.create(phone, name, password)
        s = Session.forUser(user)
        
        # return session 'cookie'
        return s.toDict()
        
    except KeyError:
        abort(400, 'Missing parameter')
    except HTTPError:
        raise
    except:
        print Red + 'Error in register():' + ColorOff
        traceback.print_exc();
        raise

# API method to login a user
@post('/login')
def login():
    try:
        phone = request.json['phone_number']
        password = request.json['password']
        
        # authenticate
        try:
            user = User.forPhone(phone)
            if not user.authenticate(password):
                print 'Invalid login : %s' % user
                abort(401, 'Invalid user or password.')
        except NoSuchUserError:
            abort(401, 'Invalid user or password.')
        
        # init session
        s = Session.forUser(user)
        # renew session (if previously logged in)
        s.renew()
        
        # return session 'cookie'
        return s.toDict()
        
    except KeyError:
        abort(400, 'Missing parameter')
    except HTTPError:
        raise
    except:
        print Red + 'Error in login():' + ColorOff
        traceback.print_exc()
        raise

@post('/logout')
def logout():
    s = getSession()
    try:
        s.expire()
        # return something useful?
        return {}
    except HTTPError:
        raise
    except:
        print Red + 'Error in logout():' + ColorOff
        traceback.print_exc()
        raise

# API method to create a group
@post('/group')
def createGroup():
    s = getSession()
    try:
        name = request.json['name']
        origin = request.json['origin']
        destin = request.json['destination']
        t_arr = request.json['arrival_time']
        t_dep = request.json['departure_time']
        seats = request.json['seats']
        days = request.json['days']
        
        # check the group doesn't already exist
        if Group.forName(name):
            print('createGroup() : group %s already exists.' % name)
            abort(400, 'A group by that name already exists.')
        
        # TODO sanity check (properly)
        if None in (name, origin, destin, t_arr, t_dep, seats, days):
            abort(400, 'All group fields apart from id must be supplied.')
        
        group = Group.create(s.user, name, origin, destin, t_arr, t_dep, seats, days)
        
        return group.toDict()
        
    except KeyError:
        abort(400, 'Missing parameter')
    except HTTPError:
        raise
    except:
        print Red + 'Error in createGroup():' + ColorOff
        traceback.print_exc()
        raise

# API method to delete a group
@delete('/group')
def deleteGroup():
    s = getSession()
    
    # TODO test this
    
    try:
        group = Group.forID(request.json['group_id'])
        if not s.user == group.owner:
            abort(403, 'Only the owner can delete a group.')
        group.delete()
        # TODO return something useful?
        return {}
        
    except NoSuchGroupError as e:
        abort(400, e.message)
    except KeyError:
        abort(400, 'Missing parameter')
    except HTTPError:
        raise
    except:
        print Red + 'Error in deleteGroup():' + ColorOff
        traceback.print_exc()
        raise

# API method to get everything for a group
@get('/group')
def getGroup():
    s = getSession()

    # TODO test this
    
    try:
        # using get gives None instead of a KeyError
        group_id = request.json.get('group_id')
        group_name = request.json.get('group_name')
        group = Group.forAny(group_id=group_id, group_name=group_name)
        return group.toDict()
        
    except NoSuchGroupError as e:
        abort(400, e.message)
    except KeyError:
        abort(400, 'Missing parameter')
    except HTTPError:
        raise
    except:
        print Red + 'Error in getGroup():' + ColorOff
        traceback.print_exc()
        raise

# API method to update stuff for a group
@put('/group')
def updateGroup():
    s = getSession()
    
    # TODO
    
    try:
        name = request.json.get('name')
        origin = request.json.get('origin')
        destin = request.json.get('destination')
        t_arr = request.json.get('arrival_time')
        t_dep = request.json.get('departure_time')
        seats = request.json.get('seats')
        days = request.json.get('days')
        group = Group.forID(request.json['group_id'])
        
        return group.toDict()
        
    except NoSuchGroupError as e:
        abort(400, e.message)
    except KeyError:
        abort(400, 'Missing parameter')
    except HTTPError:
        raise
    except:
        print Red + 'Error in updateGroup():' + ColorOff
        traceback.print_exc()
        raise

# API method to get groups user drives
@get('/driverGroups')
def getDriverGroups():
    s = getSession()
    
    # TODO test this
    
    try:
        res = {}
        for group in Group.forOwner(s.user):
            res[group.id] = group.toDict()
        return res
        
    except HTTPError:
        raise
    except:
        print Red + 'Error in getDriverGroups():' + ColorOff
        traceback.print_exc()
        raise

# API method to get groups user is a passenger (or driver) of
@get('/passengerGroups')
def getPassengerGroups():
    s = getSession()
    
    # TODO test this
    
    try:
        res = {}
        for group in Group.forUser(s.user):
            res[group.id] = group.toDict()
        return res
        
    except HTTPError:
        raise
    except:
        print Red + 'Error in getPassengerGroups():' + ColorOff
        traceback.print_exc()
        raise

# API method to get passengers (including driver) of a specified group
@get('/passengers')
def getPassengers():
    s = getSession()
    
    # TODO test this
    
    try:
        group = Group.forID(request.json['group_id'])
        # check the requesting user is in the group
        if not s.user in group:
            abort(403, 'Only members of a group can view its passengers.')
        res = {}
        for user in group:
            res[user.id] = user.toDict()
        return res
        
    except NoSuchGroupError as e:
        abort(400, e.message)
    except KeyError:
        abort(400, 'Missing parameter')
    except HTTPError:
        raise
    except:
        print Red + 'Error in getPassengers():' + ColorOff
        traceback.print_exc()
        raise

# API method to add a passenger to a group
@post('passengers')
def addPassenger():
    s = getSession()
    
    # TODO test this
    
    try:
        group = Group.forID(request.json['group_id'])
        user = User.forID(request.json['user_id'])
        if not s.user == group.owner:
            abort(403, 'Only the owner of a group can add users.')
        group += user
        # TODO return something useful?
        return {}
        
    except (NoSuchUserError, NoSuchGroupError) as e:
        abort(400, e.message)
    except KeyError:
        abort(400, 'Missing parameter')
    except HTTPError:
        raise
    except:
        print Red + 'Error in addPassenger():' + ColorOff
        traceback.print_exc()
        raise

# API method to delete a passenger from a group. Absent or less than 0 means 'delete me'.
@delete('passengers')
def deletePassenger():
    s = getSession()
    
    # TODO test this
    
    try:
        user_id = request.json.get('user_id')
        group = Group.forID(request.json['group_id'])
        user = User.forID(user_id) if user_id >= 0 else s.user
        # can't delete users from a group unless you own that group or are the deletee
        if not s.user in (group.owner, user):
            abort(403, 'Only the owner or the deletee can delete a user.')
        if user == group.owner:
            abort(400, 'Cannot delete the owner from the group.')
        group -= user
        # TODO return something useful?
        return {}
    
    except (NoSuchUserError, NoSuchGroupError) as e:
        abort(400, e.message)
    except KeyError:
        abort(400, 'Missing parameter')
    except HTTPError:
        raise
    except:
        print Red + 'Error in deletePassenger():' + ColorOff
        traceback.print_exc()
        raise

# 'Main method' : this needs to be at the bottom
if __name__ == '__main__':
    try:
        # create tables if needed
        _dbcon.execute("""
                    CREATE TABLE IF NOT EXISTS groups (
                        user_id INTEGER NOT NULL,
                        group_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        group_name TEXT NOT NULL UNIQUE,
                        origin TEXT NOT NULL,
                        destination TEXT NOT NULL,
                        arrival_time DATETIME NOT NULL,
                        departure_time DATETIME NOT NULL,
                        seats INTEGER NOT NULL,
                        days CHAR (7) NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES users(user_id)
                    );
                    """)
        _dbcon.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        user_name TEXT NOT NULL,
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
    
    if _BD_USER_ID >= 0:
        _BD_SESSION = Session(User.forID(_BD_USER_ID))
        print ''
        print Red + '\t\t**** BACKDOOR OPEN ****' + ColorOff
        print Red + '\tBackdoor: %s' % _BD_SESSION + ColorOff
        print ''
    
    # run that server
    run(host=_host,port=_port,)

# END.






























