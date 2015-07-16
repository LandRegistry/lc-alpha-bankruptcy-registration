import os


class Config(object):
    DEBUG = False


class DevelopmentConfig(object):
    DEBUG = True
    DATABASE_NAME = 'landcharges'
    DATABASE_USER = 'landcharges'
    DATABASE_PASSWORD = 'lcalpha'
    DATABASE_HOST = 'localhost'
    MQ_USERNAME = 'mquser'
    MQ_PASSWORD = 'mqpassword'
    MQ_HOSTNAME = 'localhost'
    MQ_PORT = '5672'


class PreviewConfig(object):
    DEBUG = False
    DATABASE_NAME = 'landcharges'
    DATABASE_USER = 'landcharges'
    DATABASE_PASSWORD = 'lcalpha'
    DATABASE_HOST = 'localhost'
    MQ_USERNAME = 'mquser'
    MQ_PASSWORD = 'mqpassword'
    MQ_HOSTNAME = 'localhost'
    MQ_PORT = '5672'