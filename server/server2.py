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

import json, sqlite3, sys, os, uuid, time, traceback, hashlib, re
from Queue import PriorityQueue
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

# Bold Colors
BBlack="\033[1;30m"
BRed="\033[1;31m"
BGreen="\033[1;32m"
BYellow="\033[1;33m"
BBlue="\033[1;34m"
BPurple="\033[1;35m"
BCyan="\033[1;36m"
BWhite="\033[1;37m"

#
# ================================
# Users
# ================================
#

class NoSuchUserError(Exception):
    def __init__(self, user_id=None, phone=None, message=None):
        if user_id != None:
            Exception.__init__(self, 'No user found with id=%s.' % str(user_id))
        elif phone != None:
            Exception.__init__(self, 'No user found with phone_number=%s.' % str(phone))
        elif message != None:
            Exception.__init__(self, message)
        else:
            Exception.__init__(self, 'No arguments supplied.')

class UserSanityError(Exception):
    def __init__(self, field=None, message=None):
        if message != None:
            Exception.__init__(self, message)
        elif field != None:
            Exception.__init__(self, 'User field %s was not valid.' % field)
        else:
            Exception.__init__(self, 'No arguments supplied.')

class User(object):
    """ A user. Persistent (at least in memory, ie. doesn't die with or rely on a session).
    do not use constructor directly, call User.forID() or User.forPhone()."""
    
    # dict of user ids to users
    _by_id = {}
    # dict of phone numbers to users
    _by_phone = {}
    
    @classmethod
    def validatePhone(cls, phone, noneval=None):
        if phone == None:
            return noneval
        try:
            phone = str(long(phone))
            # TODO fancier phone validity?
            if not re.match(r'^[0-9]+$', phone):
                raise UserSanityError(message='User phone must look like 0223456789.')
            return long(phone)
        except UserSanityError:
            raise
        except:
            raise UserSanityError(field='phone')
    
    @classmethod
    def validateName(cls, name, noneval=None):
        if name == None:
            return noneval
        try:
            name = unicode(name)
            if len(name) < 3:
                raise UserSanityError(message='User name must be at least 3 characters.')
            if not re.match(r'^[a-zA-Z0-9 -_+=.]*$', name):
                raise UserSanityError(message='User name must consist on only [a-zA-Z0-9 -_+=.].')
            return name
        except UserSanityError:
            raise
        except:
            raise UserSanityError(field='name')
    
    @classmethod
    def validatePassword(cls, password, noneval=None):
        if password == None:
            return noneval
        try:
            password = unicode(password)
            if len(password) < 6:
                raise UserSanityError(message='User password must be at least 6 characters.')
            # TODO is a char check necessary?
            return password
        except UserSanityError:
            raise
        except:
            raise UserSanityError(field='password')
    
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
        try:
            user_id = int(user_id)
            return cls._by_id[user_id]
        except ValueError:
            raise NoSuchUserError(user_id=user_id)
        except KeyError:
            # this may throw NoSuchUserError
            user = User(user_id=user_id)
            cls._by_id[user.id] = user
            cls._by_phone[user.phone] = user
            return user
    
    @classmethod
    def forPhone(cls, phone):
        """ Get a user by phone number. Throws NoSuchUserError. """
        try:
            phone = long(phone)
            return cls._by_phone[phone]
        except ValueError:
            raise NoSuchUserError(phone=phone)
        except KeyError:
            # this may throw NoSuchUserError
            user = User(phone=phone)
            cls._by_id[user.id] = user
            cls._by_phone[user.phone] = user
            return user
    
    @classmethod
    def create(cls, phone, name, password):
        """ Create a user. Throws if phone not unique (DB check)."""
        phone = cls.validatePhone(phone)
        name = cls.validateName(name)
        password = cls.validatePassword(password)
        try:
            User.forPhone(phone)
            raise UserSanityError(message='Phone not unique.')
        except NoSuchUserError:
            # good, user doesn't exist
            pass
        # generate a secure random salt and hash the password with it
        pwd_salt = hashlib.sha512(os.urandom(128)).hexdigest()
        pwd_hash = hashlib.sha512(pwd_salt + password).hexdigest()
        # create user
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
        self.id = int(row['user_id'])
        self.name = unicode(row['user_name'])
        self.phone = long(row['phone_number'])
        self.pwd_salt = str(row['salt'])
        self.pwd_hash = str(row['hash'])
        # init notification queue. poll from index 0
        self._notifications = []
    
    def authenticate(self, password):
        """ Authenticate this user by password. Returns True iff successfull. """
        return hashlib.sha512(self.pwd_salt + password).hexdigest() == self.pwd_hash
    
    def pollNotification(self):
        """ Return the next queued notification, or None. """
        try:
            return self._notifications.pop(0)
        except IndexError:
            return None
    
    def pushNotification(self, notification):
        """ Enqueue a notification for this user. THIS IS CALLED AUTOMAGICALLY BY THE NOTIFICATION CONSTRUCTOR. """
        self._notifications.append(notification)
    
    def __str__(self):
        return 'User[id=%d,name=%s]' % (self.id, self.name)
    
    def toDict(self):
        """ Create a dict representation for returning as JSON. """
        d = {}
        d['user_id'] = self.id
        d['user_name'] = self.name
        d['phone_number'] = self.phone
        return d

#
# ================================
# Invites and Requests
# ================================
#

class NoSuchGroupInviteError(Exception):
    def __init__(self, invite_id):
        Exception.__init__(self, 'No invite found with id=%s.' % str(invite_id))

class GroupInvite(object):
    """ An invitation to join a group. Do not call the constructor directly, use GroupInvite.create(). """
    
    # invitations by uuid
    _by_id = {}
    
    @classmethod
    def forID(cls, invite_id):
        """ Get an invitation by id. May throw NoSuchGroupInviteError. """
        try:
            return cls._by_id[uuid.UUID(str(invite_id))]
        except KeyError:
            raise NoSuchGroupInviteError(invite_id)
    
    @classmethod
    def create(cls, user, group):
        """ Create an invite. """
        ginv = GroupInvite(user, group)
        cls._by_id[ginv.id] = ginv
        return ginv
    
    def __init__(self, user, group):
        self.id = uuid.uuid4()
        self.user = user
        self.group = group
        # send notification
        GroupInviteNotification(self)
    
    def accept(self):
        """ Accept this invitation, i.e. add the user this invitation is for to the group it is for. """
        # notification is sent by group
        self.group += self.user
        GroupInvite._by_id.pop(self.id, None)
    
    def decline(self):
        """ Decline this invitation. """
        # send notification
        GroupInviteDeclineNotification(self)
        GroupInvite._by_id.pop(self.id, None)
    
    def withdraw(self):
        """ Withdraw this invitation. """
        # send notification
        GroupInviteWithdrawNotification(self)
        GroupInvite._by_id.pop(self.id, None)
    
    def toDict(self):
        """ Create a dict representation for returning as JSON. """
        d = {}
        d['invite_id'] = self.id.hex
        d['user'] = self.user.toDict()
        d['group'] = self.group.toDict()
        return d

class NoSuchGroupRequestError(Exception):
    def __init__(self, request_id):
        Exception.__init__(self, 'No request found with id=%s.' % str(request_id))

class GroupRequest(object):
    """ A request to join a group. Do not call the constructor directly, use GroupRequest.create(). """
    
    # requests by id
    _by_id = {}
    
    @classmethod
    def forID(cls, request_id):
        """ Get a request by id. May throw NoSuchGroupRequestError. """
        try:
            return cls._by_id[uuid.UUID(str(request_id))]
        except KeyError:
            raise NoSuchGroupRequestError(request_id)
    
    @classmethod
    def create(cls, user, group):
        """ Create a request. """
        greq = GroupRequest(user, group)
        cls._by_id[greq.id] = greq
        return greq
    
    def __init__(self, user, group):
        self.id = uuid.uuid4()
        self.user = user
        self.group = group
        # send notification
        GroupRequestNotification(self)
    
    def accept(self):
        """ Accept this request, i.e. add the user this request is from to the group it is for. """
        # notification is sent by group
        self.group += self.user
        GroupRequest._by_id.pop(self.id, None)
    
    def decline(self):
        """ Decline this request. """
        # send notification
        GroupRequestDeclineNotification(self)
        GroupRequest._by_id.pop(self.id, None)
    
    def withdraw(self):
        """ Withdraw this request. """
        # send notification
        GroupRequestWithdrawNotification(self)
        GroupRequest._by_id.pop(self.id, None)
    
    def toDict(self):
        """ Create a dict representation for returning as JSON. """
        d = {}
        d['request_id'] = self.id.hex
        d['user'] = self.user.toDict()
        d['group'] = self.group.toDict()
        return d

#
# ================================
# Notifications
# ================================
#

class Notification(object):
    def __init__(self, tag, to, message):
        self.created = long(time.time())
        self.tag = tag
        self.to = to
        self.message = message
        self.to.pushNotification(self)
    
    def toDict(self):
        """ Create a dict representation for returning as JSON. """
        d = {}
        d['created'] = self.created
        d['to'] = self.to.toDict()
        d['tag'] = self.tag
        d['message'] = self.message
        return d
    
    def __str__(self):
        return self.message

class GroupDeleteNotification(Notification):
    def __init__(self, to, group):
        Notification.__init__(self, 'group_delete', to, 'Group %s was deleted.' % group.name)
        self.group = group
    
    def toDict(self):
        d = Notification.toDict(self)
        d['group'] = self.group.toDict()
        return d

class GroupUserNotification(Notification):
    def __init__(self, tag, to, user, group, message):
        Notification.__init__(self, tag, to, message)
        self.user = user
        self.group = group
    
    def toDict(self):
        d = Notification.toDict(self)
        d['group'] = self.group.toDict()
        d['user'] = self.user.toDict()
        return d

class GroupUserAddNotification(GroupUserNotification):
    def __init__(self, to, user, group):
        if to == user:
            message = 'You were added to group %s.' % group.name
        else:
            message = '%s was added to group %s.' % (user.name, group.name)
        GroupUserNotification.__init__(self, 'group_user_add', to, user, group, message)

class GroupUserDeleteNotification(GroupUserNotification):
    def __init__(self, to, user, group):
        if to == user:
            message = 'You were deleted from group %s.' % group.name
        else:
            message = '%s was deleted from group %s.' % (user.name, group.name)
        GroupUserNotification.__init__(self, 'group_user_delete', to, user, group, message)

class GroupInviteNotification(GroupUserNotification):
    def __init__(self, ginv):
        message = '%s has invited you to group %s.' % (ginv.group.owner.name, ginv.group.name)
        GroupUserNotification.__init__(self, 'group_invite', ginv.user, ginv.user, ginv.group, message)
        self.ginv = ginv
    
    def toDict(self):
        d = GroupUserNotification.toDict(self)
        d['invite_id'] = self.ginv.id.hex
        return d

class GroupRequestNotification(GroupUserNotification):
    def __init__(self, greq):
        message = '%s has requested to join group %s.' % (greq.user.name, greq.group.name)
        GroupUserNotification.__init__(self, 'group_request', greq.group.owner, greq.user, greq.group, message)
        self.greq = greq
    
    def toDict(self):
        d = GroupUserNotification.toDict(self)
        d['request_id'] = self.greq.id.hex
        return d

class GroupInviteDeclineNotification(GroupUserNotification):
    def __init__(self, ginv):
        message = '%s has declined your invitation to group %s.' % (ginv.user.name, ginv.group.name)
        GroupUserNotification.__init__(self, 'group_invite_decline', ginv.group.owner, ginv.user, ginv.group, message)
        self.ginv = ginv

class GroupRequestDeclineNotification(GroupUserNotification):
    def __init__(self, greq):
        message = '%s has declined your request to join group %s.' % (greq.group.owner.name, greq.group.name)
        GroupUserNotification.__init__(self, 'group_request_decline', greq.user, greq.user, greq.group, message)
        self.greq = greq

class GroupInviteWithdrawNotification(GroupUserNotification):
    def __init__(self, ginv):
        message = '%s has withdrawn their invitation to group %s.' % (ginv.group.owner.name, ginv.group.name)
        GroupUserNotification.__init__(self, 'group_invite_withdraw', ginv.user, ginv.user, ginv.group, message)
        self.ginv = ginv

class GroupRequestWithdrawNotification(GroupUserNotification):
    def __init__(self, greq):
        message = '%s has withdrawn their request to join group %s.' % (greq.user.name, greq.group.name)
        GroupUserNotification.__init__(self, 'group_request_withdraw', greq.group.owner, greq.user, greq.group, message)
        self.greq = greq

class GroupGPSNotification(Notification):
    def __init__(self, to, group, latitude, longitude):
        Notification.__init__(self, 'group_gps', to, '-- group gps update --')
        self.group = group
        self.latitude = latitude
        self.longitude = longitude
    
    def toDict(self):
        d = Notification.toDict(self)
        d['group'] = self.group.toDict()
        d['latitude'] = self.latitude
        d['longitude'] = self.longitude
        return d

#
# ================================
# Groups
# ================================
#

class NoSuchGroupError(Exception):
    def __init__(self, group_id=None, group_name=None, message=None):
        if group_id != None:
            Exception.__init__(self, 'No group found with id=%s.' % str(group_id))
        elif group_name != None:
            Exception.__init__(self, 'No group found with name=%s.' % str(group_name))
        elif message != None:
            Exception.__init__(self, message)
        else:
            Exception.__init__(self, 'No arguments supplied.')

class GroupSanityError(Exception):
    def __init__(self, field=None, message=None):
        if message != None:
            Exception.__init__(self, message)
        elif field != None:
            Exception.__init__(self, 'Group field %s was not valid.' % field)
        else:
            Exception.__init__(self, 'No arguments supplied.')

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
    def validateName(cls, name, noneval=None):
        if name == None:
            return noneval
        try:
            name = unicode(name)
            if len(name) < 3:
                raise GroupSanityError(message='Group name must be at least 3 characters.')
            if not re.match(r'^[a-zA-Z0-9 -_+=.]*$', name):
                raise GroupSanityError(message='Group name must consist on only [a-zA-Z0-9 -_+=.].')
            return name
        except GroupSanityError:
            raise
        except:
            raise GroupSanityError(field='name')
    
    @classmethod
    def validateOrigin(cls, origin, noneval=None):
        if origin == None:
            return noneval
        try:
            origin = unicode(origin)
            # TODO ?
            return origin
        except GroupSanityError:
            raise
        except:
            raise GroupSanityError(field='origin')
    
    @classmethod
    def validateDestination(cls, destination, noneval=None):
        if destination == None:
            return noneval
        try:
            destination = unicode(destination)
            # TODO ?
            return destination
        except GroupSanityError:
            raise
        except:
            raise GroupSanityError(field='destination')
    
    @classmethod
    def validateArrival(cls, arrival, noneval=None):
        if arrival == None:
            return noneval
        try:
            arrival = str(arrival)
            if not re.match(r'[0-2][0-9]:[0-5][0-9]:[0-5][0-9]', arrival):
                raise GroupSanityError(message='Group arrival must look like 13:54:00.')
            return arrival
        except GroupSanityError:
            raise
        except:
            raise GroupSanityError(field='arrival')
    
    @classmethod
    def validateDeparture(cls, departure, noneval=None):
        if departure == None:
            return noneval
        try:
            departure = str(departure)
            if not re.match(r'[0-2][0-9]:[0-5][0-9]:[0-5][0-9]', departure):
                raise GroupSanityError(message='Group departure must look like 13:54:00.')
            return departure
        except GroupSanityError:
            raise
        except:
            raise GroupSanityError(field='departure')
    
    @classmethod
    def validateSeats(cls, seats, noneval=None):
        if seats == None:
            return noneval
        try:
            seats = int(seats)
            if seats < 1:
                raise GroupSanityError(message='Group seats must be at least 1.')
            return seats
        except GroupSanityError:
            raise
        except:
            raise GroupSanityError(field='seats')
    
    @classmethod
    def validateDays(cls, days, noneval=None):
        if days == None:
            return noneval
        try:
            days = str(days)
            if len(days) != 7:
                raise GroupSanityError(message='Group days must be of length 7.')
            if not re.match(r'^[01]*$', days):
                raise GroupSanityError(message='Group days must only consist of 0s and 1s.')
            return days
        except GroupSanityError:
            raise
        except:
            raise GroupSanityError(field='days')
    
    @classmethod
    def _levenshtein(cls, a, b):
        """ Calculates the Levenshtein distance between a and b.
        From: http://hetland.org/coding/python/levenshtein.py """
        n, m = len(a), len(b)
        if n > m:
            # Make sure n <= m, to use O(min(n,m)) space
            a,b = b,a
            n,m = m,n
        current = range(n+1)
        for i in range(1,m+1):
            previous, current = current, [i]+[0]*n
            for j in range(1,n+1):
                add, delete = previous[j]+1, current[j-1]+1
                change = previous[j-1]
                if a[j-1] != b[i-1]:
                    change = change + 1
                current[j] = min(add, delete, change)
        return current[n]
    
    @classmethod
    def search(cls, query, results=10):
        """ Search for groups, by group name, owner phone or owner name.
        Returns a list in order from best match to worst. """
        query = unicode(query)
        # skip empty search
        if len(query) < 1:
            return []
        # rank groups that match, return best n
        pq = PriorityQueue()
        # get all groups where group name resembles query
        # priority: (edit distance / length)
        for row in _dbcon.execute('SELECT group_name FROM groups'):
            group_name = row[0]
            edist = cls._levenshtein(query, group_name)
            # TODO tune this thing
            if edist < len(group_name):
                pq.put((edist / len(query), Group.forName(group_name)))
        # get all groups where owner phone number matches exactly
        # priority: 0.01
        try:
            for g in Group.forOwner(User.forPhone(query)):
                pq.put((0.02337, g))
        except NoSuchUserError:
            # no user with that phone
            pass
        # dequeue best n
        res = []
        while len(res) < results and not pq.empty():
            res += [pq.get()[1]]
        return res
    
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
        try:
            group_id = int(group_id)
            return cls._by_id[group_id]
        except ValueError:
            raise NoSuchGroupError(group_id=group_id)
        except KeyError:
            # this may throw NoSuchGroupError
            group = Group(group_id=group_id)
            cls._by_id[group.id] = group
            cls._by_name[group.name] = group
            return group
    
    @classmethod
    def forName(cls, group_name):
        """ Get a group by name. Throws NoSuchGroupError. """
        try:
            group_name = unicode(group_name)
            return cls._by_name[group_name]
        except ValueError:
            raise NoSuchGroupError(group_name=group_name)
        except KeyError:
            # this may throw NoSuchGroupError
            group = Group(group_name=group_name)
            cls._by_id[group.id] = group
            cls._by_name[group.name] = group
            return group
    
    @classmethod
    def forUser(cls, user):
        """ Gets a tuple of all groups a user is in. """
        if not isinstance(user, User):
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
        if not isinstance(owner, User):
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
        if not isinstance(owner, User):
            raise Exception('Owner must be an instance of User.')
        if None in (name, origin, destination, arrival, departure, seats, days):
            raise Exception('All parameters must be not None.')
        # sanity check
        name = cls.validateName(name)
        origin = cls.validateOrigin(origin)
        destination = cls.validateDestination(destination)
        arrival = cls.validateArrival(arrival)
        departure = cls.validateDeparture(departure)
        seats = cls.validateSeats(seats)
        days = cls.validateDays(days)
        try:
            Group.forName(name)
            raise GroupSanityError(message='Group name is not unique.')
        except NoSuchGroupError:
            # good, group doesn't exist
            pass
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
        self._id = int(g_row['group_id'])
        self._name = unicode(g_row['group_name'])
        self._origin = unicode(g_row['origin'])
        self._destination = unicode(g_row['destination'])
        self._arrival = str(g_row['arrival_time'])
        self._departure = str(g_row['departure_time'])
        self._seats = int(g_row['seats'])
        self._days = str(g_row['days'])
        self._users = None
    
    def update(self, name=None, origin=None, destination=None, arrival=None, departure=None, seats=None, days=None):
        """ Update any subset of the editable group parameters. """
        # skip empty updates
        if all([x == None for x in (name, origin, destination, arrival, departure, seats, days)]):
            return
        # sanity check, and sub in non-updating values
        name = cls.validateName(name, self._name)
        origin = cls.validateOrigin(origin, self._origin)
        destination = cls.validateDestination(destination, self._destination)
        arrival = cls.validateArrival(arrival, self._arrival)
        departure = cls.validateDeparture(departure, self._departure)
        seats = cls.validateSeats(seats, self._seats)
        days = cls.validateDays(days, self._days)
        try:
            # update the entire row because that's easier
            # you can't do multiple updates in 1 commit
            _dbcon.execute("""
                        UPDATE groups
                        SET group_name = ?, origin = ?, destination = ?,
                        arrival_time = ?, departure_time = ?, seats = ?, days = ?
                        WHERE group_id = ?
                        """,
                        (name, origin, destination, arrival, departure, seats, days, self.id))
            _dbcon.commit()
        finally:
            _dbcon.rollback()
        # db update succeeded, update fields
        self._name = name
        self._origin = origin
        self._destination = destination
        self._arrival = arrival
        self._departure = departure
        self._seats = seats
        self._days = days
    
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
        if not isinstance(user, User):
            raise Exception('User must be an instance of User.')
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
        # send notifications
        for u in self.users:
            GroupUserAddNotification(u, user, self)
    
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
        # send notifications
        for u in self.users:
            GroupUserDeleteNotification(u, user, self)
    
    def __isub__(self, user):
        self.deleteUser(user)
        return self
    
    def delete(self):
        """ Delete this group. """
        # need this later to uncache and notify
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
        # send notifications
        for u in users:
            GroupDeleteNotification(u, self)
    
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

#
# ================================
# Sessions
# ================================
#

class NoSuchSessionError(Exception):
    def __init__(self, session_id=None, user_id=None):
        if session_id != None:
            Exception.__init__(self, 'No session found with session_id=%s.' % str(session_id))
        elif user_id != None:
            Exception.__init__(self, 'No session found for user_id=%s.' % str(user_id))
        else:
            Exception.__init__(self, 'No parameters supplied.')

class Session(object):
    """ A user session. Do not call constructor directly, use Session.create(). """
    
    # seconds each session lasts for
    _ttl = 3600
    # dict of session ids to sessions
    _by_id = {}
    # dict of users to sessions
    _by_user_id = {}
    
    @classmethod
    def forID(cls, session_id):
        """ Get a session by session_id. """
        try:
            return cls._by_id[uuid.UUID(str(session_id))]
        except KeyError:
            raise NoSuchSessionError(session_id=session_id)
    
    @classmethod
    def forUser(cls, user):
        """ Get a session for a user. """
        try:
            return cls._by_user_id[user.id]
        except KeyError:
            raise NoSuchSessionError(user_id=user.id)
    
    @classmethod
    def create(cls, user):
        """ Create a new session for a user, deletes any old one. """
        try:
            Session.forUser(user).delete()
        except NoSuchSessionError:
            # ok, no session for this user
            pass
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
        Session._by_user_id[self.user.id] = self
    
    @property
    def ttl(self):
        """ Get the time in seconds until this session expires. """
        return self.expires - long(time.time())
    
    @property
    def expired(self):
        """ Return True iff this session has expired. """
        return long(time.time()) >= self.expires
    
    def delete(self):
        """ Delete this session. """
        Session._by_id.pop(self.id, None)
        Session._by_user_id.pop(self.user.id, None)
    
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

#
# ================================
# Web API
# ================================
#

# API method to register a new user
@post('/register')
def register():
    try:
        phone = request.json['phone_number']
        name = request.json['name']
        password = request.json['password']
        
        # this handles the uniqueness check
        user = User.create(phone, name, password)
        # create new session
        s = Session.create(user)
        
        # return session 'cookie'
        return s.toDict()
        
    except UserSanityError as e:
        abort(400, e.message)
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
        user = User.forPhone(phone)
        if not user.authenticate(password):
            print 'Invalid login : %s' % user
            abort(401, 'Invalid user or password.')
        # re-init session
        s = Session.create(user)
        
        # return session 'cookie'
        return s.toDict()
        
    except NoSuchUserError:
        abort(401, 'Invalid user or password.')
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
        s.delete()
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
        
        if None in (name, origin, destin, t_arr, t_dep, seats, days):
            abort(400, 'All group fields apart from id must be supplied.')
        
        # this handles the uniqueness check
        group = Group.create(s.user, name, origin, destin, t_arr, t_dep, seats, days)
        
        return group.toDict()
        
    except GroupSanityError as e:
        abort(400, e.message)
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
        
        group.update(name=name, origin=origin, destination=destin, arrival=t_arr, departure=t_dep, seats=seats, days=days)
        
        return group.toDict()
        
    except GroupSanityError as e:
        abort(400, e.message)
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
@post('/passengers')
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
@delete('/passengers')
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

# API method to get user's notifications
@get('/notifications')
def getNotifications():
    s = getSession()
    try:
        nl = []
        n = s.user.pollNotification()
        # get notifications until none left
        while n != None:
            nl += [n.toDict()]
            n = s.user.pollNotification()
        # return as a json array
        res = { 'notifications' : nl }
        return res
        
    except HTTPError:
        raise
    except:
        print Red + 'Error in getNotifications():' + ColorOff
        traceback.print_exc()
        raise

# API method to invite a user to a group
@post('/groupinvite')
def createGroupInvite():
    s = getSession()
    
    # TODO test this
    
    try:
        user_id = request.json.get('user_id')
        phone = request.json.get('phone_number')
        user = User.forAny(user_id=user_id, phone=phone)
        group = Group.forID(request.json['group_id'])
        # can only create an invite if you own the group
        if s.user != group.owner:
            abort(403, 'Only the group owner can invite users.')
        # can only invite someone who isn't in the group
        if user in group:
            abort(400, 'Can only invite users who are not in the group.')
        # create invite
        ginv = GroupInvite.create(user, group)
        return ginv.toDict()
        
    except (NoSuchUserError, NoSuchGroupError) as e:
        abort(400, e.message)
    except KeyError:
        abort(400, 'Missing parameter')
    except HTTPError:
        raise
    except:
        print Red + 'Error in createGroupInvite():' + ColorOff
        traceback.print_exc()
        raise

# API method to request to join a group
@post('/grouprequest')
def createGroupRequest():
    s = getSession()
    
    # TODO test this
    
    try:
        group = Group.forID(request.json['group_id'])
        # can only request if you aren't in the group
        if s.user in group:
            abort(400, 'Can only request to join a group you are not in.')
        # create request
        greq = GroupRequest.create(s.user, group)
        return greq.toDict()
        
    except NoSuchGroupError as e:
        abort(400, e.message)
    except KeyError:
        abort(400, 'Missing parameter')
    except HTTPError:
        raise
    except:
        print Red + 'Error in createGroupRequest():' + ColorOff
        traceback.print_exc()
        raise

# API method to withdraw an invite
@delete('/groupinvite')
def deleteGroupInvite():
    s = getSession()
    
    # TODO test this
    
    try:
        ginv = GroupInvite.forID(request.json['invite_id'])
        # can only withdraw if you issued the invite
        if s.user != ginv.group.owner:
            abort(403, 'Only the group owner can withdraw an invite.')
        # withdraw
        ginv.withdraw()
        return {}
        
    except NoSuchGroupInviteError as e:
        abort(400, e.message)
    except KeyError:
        abort(400, 'Missing parameter')
    except HTTPError:
        raise
    except:
        print Red + 'Error in deleteGroupInvite():' + ColorOff
        traceback.print_exc()
        raise

# API method to withdraw a request
@delete('/grouprequest')
def deleteGroupRequest():
    s = getSession()
    
    # TODO test this
    
    try:
        greq = GroupRequest.forID(request.json['request_id'])
        # can only withdraw if you issued the request
        if s.user != greq.user:
            abort(403, 'Only the requesting user can withdraw a request.')
        # withdraw
        greq.withdraw()
        return {}
        
    except NoSuchGroupRequestError as e:
        abort(400, e.message)
    except KeyError:
        abort(400, 'Missing parameter')
    except HTTPError:
        raise
    except:
        print Red + 'Error in deleteGroupRequest():' + ColorOff
        traceback.print_exc()
        raise

# API method to accept an invitation to a group
@post('/acceptgroupinvite')
def acceptGroupInvite():
    s = getSession()
    
    # TODO test this
    
    try:
        ginv = GroupInvite.forID(request.json['invite_id'])
        # can only accept if invite was issued to you
        if s.user != ginv.user:
            abort(403, 'Only the invited user can accept an invite.')
        # accept
        ginv.accept()
        return {}
        
    except NoSuchGroupInviteError as e:
        abort(400, e.message)
    except KeyError:
        abort(400, 'Missing parameter')
    except HTTPError:
        raise
    except:
        print Red + 'Error in acceptGroupInvite():' + ColorOff
        traceback.print_exc()
        raise

# API method to accept a request to join a group
@post('/acceptgrouprequest')
def acceptGroupRequest():
    s = getSession()
    
    # TODO test this
    
    try:
        greq = GroupRequest.forID(request.json['request_id'])
        # can only accept request if owner
        if s.user != greq.group.owner:
            abort(403, 'Only the group owner can accept a request.')
        # accept
        greq.accept()
        return {}
        
    except NoSuchGroupRequestError as e:
        abort(400, e.message)
    except KeyError:
        abort(400, 'Missing parameter')
    except HTTPError:
        raise
    except:
        print Red + 'Error in acceptGroupRequest():' + ColorOff
        traceback.print_exc()
        raise

# API method to decline an invitation to a group
@post('/declinegroupinvite')
def declineGroupInvite():
    s = getSession()
    
    # TODO test this
    
    try:
        ginv = GroupInvite.forID(request.json['invite_id'])
        # can only decline if invite was issued to you
        if s.user != ginv.user:
            abort(403, 'Only the invited user can decline an invite.')
        # decline
        ginv.decline()
        return {}
        
    except NoSuchGroupInviteError as e:
        abort(400, e.message)
    except KeyError:
        abort(400, 'Missing parameter')
    except HTTPError:
        raise
    except:
        print Red + 'Error in declineGroupInvite():' + ColorOff
        traceback.print_exc()
        raise

# API method to decline a request to join a group
@post('/declinegrouprequest')
def declineGroupRequest():
    s = getSession()
    
    # TODO test this
    
    try:
        greq = GroupRequest.forID(request.json['request_id'])
        # can only decline request if owner
        if s.user != greq.group.owner:
            abort(403, 'Only the group owner can decline a request.')
        # decline
        greq.decline()
        return {}
        
    except NoSuchGroupRequestError as e:
        abort(400, e.message)
    except KeyError:
        abort(400, 'Missing parameter')
    except HTTPError:
        raise
    except:
        print Red + 'Error in declineGroupRequest():' + ColorOff
        traceback.print_exc()
        raise

# API method to search for groups. WARNING: this isn't google - lower your expectations.
@get('/search')
def searchGroups():
    s = getSession()
    
    # TODO test this
    
    try:
        query = request.json['search_query']
        groups = Group.search(query)
        return { 'groups' : [g.toDict() for g in groups] }
        
    except KeyError:
        abort(400, 'Missing parameter')
    except HTTPError:
        raise
    except:
        print Red + 'Error in searchGroups():' + ColorOff
        traceback.print_exc()
        raise

# API method to update the location of a group's driver
@put('/gps')
def updateGroupGPS():
    s = getSession()
    
    # TODO test this
    
    try:
        group = Group.forID(request.json['group_id'])
        latitude = float(request.json['latitude'])
        longitude = float(request.json['longitude'])
        # can only update location if group owner
        if s.user != group.owner:
            abort(403, 'Only the group owner (==driver) can update group location.')
        # send notification to each user in the group
        for user in group:
            GroupGPSNotification(user, group, latitude, longitude)
        return {}
        
    except ValueError as e:
        abort(400, e.message)
    except NoSuchGroupError as e:
        abort(400, e.message)
    except KeyError:
        abort(400, 'Missing parameter')
    except HTTPError:
        raise
    except:
        print Red + 'Error in updateGroupGPS():' + ColorOff
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
        _BD_SESSION = Session.create(User.forID(_BD_USER_ID))
        print ''
        print Red + '\t\t**** BACKDOOR OPEN ****' + ColorOff
        print Red + '\tBackdoor: %s' % _BD_SESSION + ColorOff
        print ''
    
    # run that server
    run(host=_host,port=_port,)

# END.






























