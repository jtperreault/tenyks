CONNECTIONS = {
    'network1': {
        'host': 'localhost',
        'port': 6667,
        'password': None,
        'nick': 'tenyks',
        'ident': 'tenyks',
        'realname': 'tenyks IRC bot',
        'admins': ['vhost-',],
        'ssl': False,
        'channels': ['#test',], # if your channel has a password: '#thechannel, thepassword'
    },
    #'network2': {
    #    'host': 'localhost',
    #    'port': 6667,
    #    'password': None,
    #    'nick': 'tenyks',
    #    'ident': 'tenyks',
    #    'realname': 'tenyks IRC bot',
    #    'admins': ['vhost-',],
    #    'ssl': False,
    #    'channels': [],
    #}
}

REDIS_CONNECTION = {
    'host': 'localhost',
    'port': 6379,
    'db': 0,
    'password': None,
}

# SERVICES_SET_KEY = 'tenyks.services'
# SERVICES_KEY = 'tenyks.services.%s'
# SERVICES_PING_RESPONSE_KEY = 'tenyks.services.%s.ping_response'
BROADCAST_TO_SERVICES_CHANNEL = 'tenyks.services.broadcast_to'
BROADCAST_TO_ROBOT_CHANNEL = 'tenyks.robot.broadcast_to'
# WORKING_DIR
# LOGGING_DIR