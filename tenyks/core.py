""" Core of tenyks. Contains Robot and IRC/Redis Lines"""
import gevent.monkey
gevent.monkey.patch_all()

from datetime import datetime
import json
import os
import sys

import logging
logger = logging.getLogger('tenyks')

import gevent
from gevent import queue
import redis

from tenyks.banner import startup_banner
from tenyks.commandmapping import command_parser
from tenyks.config import settings, collect_settings
from tenyks.connection import Connection
from tenyks.utils import pubsub_factory
from tenyks.middleware import CORE_MIDDLEWARE


if hasattr(settings, 'MIDDLEWARE'):
    CORE_MIDDLEWARE += settings.MIDDLEWARE


class Robot(object):
    """
    Design Rules:

    * The Robot has access to services to handle commands.
    * Services send and receive data.
    * The Robot's brain is, effectively, the services.
    * The Robot will forever ONLY relay data to and from platforms (IRC, Email)
      to and from services and handle connection to platforms.
    * The Robot will never handle commands sent from platforms or services.
    * _Almost_ everything is evented.
    """

    def __init__(self):
        self.broadcast_queue = queue.Queue()
        gevent.spawn(self.broadcast_loop)
        gevent.spawn(self.handle_incoming_redis_messages)

        self.prepare_environment()

        self.connections = {}
        self.bootstrap_connections()

    def prepare_environment(self):
        # TODO FIX THIS MESS
        try:
            os.mkdir(settings.WORKING_DIR)
        except OSError:
            # Already exists
            pass
        try:
            os.mkdir(settings.DATA_WORKING_DIR)
        except OSError:
            # Already exists
            pass

    def bootstrap_connections(self):
        for name, connection in settings.CONNECTIONS.iteritems():
            conn = Connection(name, **connection)
            self.connections[name] = conn
            conn.connect()
            success = self.wait_for_success(conn)
            if success:
                self.handshake(conn)
            else:
                logger.error('{conn} failed to connect or we did not get a response'.format(
                    conn=conn.name))
                continue

    def wait_for_success(self, connection):
        """
        This will look for something that represents a successful connection
        to the server. If it doesn't see one in 5 seconds, it times out and
        the connection is considered unsuccessful.
        """
        with gevent.Timeout(5, False):
            data = connection.socket.recv(1024).decode('utf-8')
            if data:
                return True
        return False

    def handshake(self, connection):
        if 'password' in connection.config and connection.config['password']:
            connection.send('PASS {password}'.format(
                password=connection.config['password']))
        connection.send('NICK {nick}'.format(
            nick=connection.config['nick']))
        connection.send('USER {ident} {host} bla :{realname}'.format(
            ident=connection.config['ident'],
            host=connection.config['host'],
            realname=connection.config['realname']))
        connection.post_connect()

    def join_channels(self, connection):
        for channel in connection.config['channels']:
            self.join(connection, channel)

    def run_command(self, connection, command):
        connection.send(command_parser(command))

    def join(self, connection, channel):
        """
        join a irc channel
        """
        password = ''
        if ',' in channel:
            channel, password = channel.split(',')
        chan = '{channel} {password}'.format(
                channel=channel, password=password)
        connection.send('JOIN {channel}'.format(
            channel=chan.strip()))

    def say(self, connection, message, channels=[]):
        for channel in channels:
            message = 'PRIVMSG {channel} :{message}\r\n'.format(
                    channel=channel, message=message)
            connection.send(message)

    def broadcast_loop(self):
        """
        Pop things off the broadcast_queue and create jobs for them.
        """
        while True:
            data = self.broadcast_queue.get()
            gevent.spawn(self.broadcast_worker, data)

    def broadcast_worker(self, data):
        """
        This worker will broadcast a message to the service broadcast channel
        """
        r = redis.Redis(**settings.REDIS_CONNECTION)
        broadcast_channel = getattr(settings, 'BROADCAST_TO_SERVICES_CHANNEL',
            'tenyks.services.broadcast_to')
        r.publish(broadcast_channel, json.dumps(data))

    def handle_incoming_redis_messages(self):
        """
        {
            'payload': 'this is a message to IRC',
            'target': '#test',
            'command': 'PRIVMSG',
            'connection': 'freenode',
        }
        """
        broadcast_channel = getattr(settings, 'BROADCAST_TO_ROBOT_CHANNEL',
            'tenyks.robot.broadcast_to')
        pubsub = pubsub_factory(broadcast_channel)
        for raw_redis_message in pubsub.listen():
            logger.info('Robot <- {data}'.format(
                data=json.dumps(raw_redis_message)))
            try:
                if raw_redis_message['data'] != 1L:
                    message = json.loads(raw_redis_message['data'])
                    if message['command'].lower() == 'privmsg':
                        self.say(message['connection'],
                                    message['payload'],
                                    channels=[message['target']])
            except ValueError:
                logger.info('Robot Pubsub: invalid JSON. Ignoring message.')

    def middleware_message(self, connection, data):
        for middleware in CORE_MIDDLEWARE:
            data = middleware(self, connection, data)
        return data

    def connection_worker(self, connection):
        while True:
            if connection.user_disconnect:
                break
            needs_reconnect = connection.needs_reconnect
            ping_delta = datetime.now() - connection.last_ping
            no_ping = ping_delta.seconds > 5 * 60
            if needs_reconnect or no_ping:
                connection.reconnect()
                success = self.wait_for_success(connection)
                if success:
                    self.handshake(connection)
                else:
                    logger.error('{conn} failed to connect or we did not get a response'.format(
                        conn=connection.name))
                    continue
            try:
                raw_line = connection.input_queue.get(timeout=5)
            except queue.Empty:
                continue
            data = self.middleware_message(connection, raw_line)
            if data:
                self.broadcast_queue.put(data)
        logger.info('{connection} Connection Worker: worker shutdown'.format(
            connection=connection.name))

    def run(self):
        try:
            while True:
                self.workers = []
                for name, connection in self.connections.iteritems():
                    self.workers.append(
                            gevent.spawn(self.connection_worker, connection))
                gevent.joinall(self.workers)
                break
        except KeyboardInterrupt:
            logger.info('Robot: shutting down: user disconnect')
            for name, connection in self.connections.iteritems():
                connection.close()
        finally:
            for name, connection in self.connections.iteritems():
                connection.send('QUIT :{message}'.format(
                            message=getattr(self, 'exit_message', 'I\'m out!')))
                connection.close()
            sys.exit('Bye.')


def main():
    collect_settings()
    print(startup_banner())
    robot = Robot()
    robot.run()


if __name__ == '__main__':
    main()
