# MDChecker install

Requirements:

- Linux
- Python 2.7
- the following python modules:
  - uwsgi
  - flask
  -flask_sqlalchemy
  - OWSLib
  - lxml
  - pyshp

## By hand
Instructions to get a working MDChecker instance, for dev & testing purpose only.

Install system libraries

```
sudo apt-get install libxslt1-dev
```

Deploy and activate a fresh python virtualenv

```
virtualenv venv
cd venv
source bin/activate
```

Install requirements and application inside venv

```
git clone https://github.com/geobretagne/mdchecker.git mdchecker
pip install -r mdchecker/app/requirements.txt
```

If you must get through a http proxy, use this instead

```
git config --global http.proxy http://addr:port/ 
git clone https://github.com/geobretagne/mdchecker.git mdchecker
pip install --proxy=http://addr:port/ -r mdchecker/requirements.txt
```

You may set the following environment variables with custom values:
- MDCHECKER_DEBUG: True or False
- MDCHECKER_SECRET_KEY
- MDCHECKER_DB_PATH: the path of the directory that should contain the SQLite
- http_proxy: the outgoing http proxy, if any
database file created by the create_db.py script. The default path for the database directory is /tmp

Then deploy mdchecker, get into the app dir and create the database:
```
cd mdchecker/app
python create_db.py
```

Launch mdchecker:

```
python runserver.py
```

Point your browser to http://127.0.0.1:5000/

You can bind the embedded server to a specific interface using

```
python runserver.py --host 192.168.0.1 --port 4444
```

You can activate debug mode (stacktrace output) using

```
python runserver.py --debug
```

Do not use in production !

After first launch:

* if etc/app.json is not present, it will be created with application default values. Edit this file to set application according to your needs
* be sure to correctly set the proxy  in etc/app.json. If there's no proxy, set an empty string
* copy etc/server.cfg.DIST into etc/server.cfg, see http://flask.pocoo.org/docs/0.10/config/#builtin-configuration-values
* if mdchecker sits behind a reverse proxy, be sure to set SERVER_NAME accordingly


## Using Docker
Clone or download the project.

Build and run the containers:
```
cd mdchecker
docker-compose up -d
```

Finally, open [http://localhost:8080/](http://localhost:8080/) in your browser
