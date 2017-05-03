from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from reverse_proxied import ReverseProxied
import os

app = Flask(__name__)
app.wsgi_app = ReverseProxied(app.wsgi_app)
app.jinja_env.add_extension('jinja2.ext.do')

# http://flask.pocoo.org/docs/0.10/config/#builtin-configuration-values
app.config.update(dict(
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    DEBUG=os.getenv('MDCHECKER_DEBUG', 'False') == 'True',
    #SERVER_NAME=os.getenv('MDCHECKER_SERVER_NAME', 'mydomain.com'), # FIXME, issue with this (404 on all pages)
    SECRET_KEY=os.getenv('MDCHECKER_SECRET_KEY', 'NTVEUZTNEYHZVNTHZAONTZAOVNOAZIONV5HIOZA'),
    SQLALCHEMY_DATABASE_URI='sqlite:///{0}/mdchecker.db'.format(os.getenv('MDCHECKER_DB_PATH', '/tmp'))
))

# TODO:
# app.config.from_envvar('MDCHECKER_SETTINGS', silent=True)

db = SQLAlchemy(app)

import mdchecker.main
