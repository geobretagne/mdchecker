from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_pyfile('conf/server.cfg', silent=True)
app.jinja_env.add_extension('jinja2.ext.do')
db = SQLAlchemy(app)

import mdchecker.main
