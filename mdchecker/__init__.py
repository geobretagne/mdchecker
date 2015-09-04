from flask import Flask
app = Flask(__name__)
app.config.from_pyfile('conf/server.cfg', silent=True)

import mdchecker.main
