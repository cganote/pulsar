try:
    import kombu
    from kombu import pools
    from kombu.common import eventloop
except ImportError:
    kombu = None

import socket
import logging
log = logging.getLogger(__name__)


KOMBU_UNAVAILABLE = "Attempting to bind to AMQP message queue, but kombu dependency unavailable"

DEFAULT_EXCHANGE_NAME = "lwr"
DEFAULT_EXCHANGE_TYPE = "direct"
DEFAULT_TIMEOUT = 0.2


class LwrExchange(object):

    def __init__(self, url, manager_name, timeout=DEFAULT_TIMEOUT):
        if not kombu:
            raise Exception(KOMBU_UNAVAILABLE)
        self.__url = url
        self.__manager_name = manager_name
        self.__exchange = kombu.Exchange(DEFAULT_EXCHANGE_NAME, DEFAULT_EXCHANGE_TYPE)
        self.__timeout = timeout

    def connection(self, connection_string, **kwargs):
        return kombu.Connection(connection_string, **kwargs)

    def consume(self, queue_name, callback, check=True, connection_kwargs={}):
        queue = self.__queue(queue_name)
        with self.connection(self.__url, **connection_kwargs) as connection:
            with kombu.Consumer(connection, queues=[queue], callbacks=[callback], accept=['json']):
                while check:
                    try:
                        connection.drain_events(timeout=self.__timeout)
                    except socket.timeout:
                        pass

    def publish(self, name, payload):
        with self.connection(self.__url) as connection:
            with pools.producers[connection].acquire() as producer:
                key = self.__queue_name(name)
                producer.publish(
                    payload,
                    serializer='json',
                    exchange=self.__exchange,
                    declare=[self.__exchange],
                    routing_key=key,
                )

    def __queue(self, name):
        queue_name = self.__queue_name(name)
        queue = kombu.Queue(queue_name, self.__exchange, routing_key=queue_name)
        return queue

    def __queue_name(self, name):
        key_prefix = self.__key_prefix()
        queue_name = '%s_%s' % (key_prefix, name)
        return queue_name

    def __key_prefix(self):
        if self.__manager_name == "_default_":
            key_prefix = "lwr_"
        else:
            key_prefix = "lwr_%s_" % self.__manager_name
        return key_prefix
