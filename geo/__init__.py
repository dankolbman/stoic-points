import os
import subprocess
from flask import Flask, jsonify
from flask_profile import Profiler
from flask_cqlalchemy import CQLAlchemy
from flask_restplus import Api
from flask_jwt import JWT
from celery import Celery
from config import config

db = CQLAlchemy()
profiler = Profiler()

CELERY_TASK_LIST = [
    'geo.tasks',
]


def authenticate(username, password):
    """ We will never authenticate a user from this sevice """
    return None


def identity(payload):
    return payload['identity']


def create_celery_app(app=None):
    """
    Create a new Celery object and tie together the Celery config to the app's
    config. Wrap all tasks in the context of the application.
    From: https://github.com/nickjj/build-a-saas-app-with-flask
    """
    app = app or create_app(os.getenv('FLASK_CONFIG') or 'default')

    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'],
                    include=CELERY_TASK_LIST)
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)
    profiler.init_app(app)
    from geo.api import api
    api.init_app(app)
    jwt = JWT(app, authenticate, identity)

    @app.route('/status')
    def status():
        return jsonify({
            "version": (subprocess.check_output(
                        ['git', 'rev-parse', '--short', 'HEAD'])
                        .decode('utf-8').strip()),
            "status": 200})

    return app
