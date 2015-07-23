from application import app
import kombu
from kombu.common import maybe_declare
import sys
import logging


def setup_messaging():
    host = "amqp://{}:{}@{}:{}".format(
        app.config['MQ_USERNAME'], app.config['MQ_PASSWORD'], app.config['MQ_HOSTNAME'],
        app.config['MQ_PORT'])
    logging.debug("Connect to " + host)
    connection = kombu.Connection(hostname=host)
    channel = connection.channel()
    exchange = kombu.Exchange(type="topic", name="new.bankruptcy")
    exchange.maybe_bind(channel)
    maybe_declare(exchange, channel)
    prod = kombu.Producer(channel, exchange=exchange, routing_key='simple', serializer='json')
    logging.info("Producer started")
    sys.stdout.flush()
    return prod


def publish_new_bankruptcy(producer, data):
    logging.info("Sending: {}".format(data))
    producer.publish(data)