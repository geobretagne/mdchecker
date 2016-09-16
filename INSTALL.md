MDChecker quick install
===============

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
pip install -r mdchecker/requirements.txt
```

If you must get through a http proxy, use this instead

```
git config --global http.proxy http://addr:port/ 
git clone https://github.com/geobretagne/mdchecker.git mdchecker
pip install --proxy=http://addr:port/ -r mdchecker/requirements.txt
```

Then deploy application and get into the app dir :

```
cd mdchecker/app
python runserver.py
```

Point your browser to http://127.0.0.1:5000/

You can bind the embedded server to a specific interface using

```
python runserver.py --host 192.168.0.1 --port 4444
```

After first launch :

* if etc/app.json is not present, it will be created with application default values. Edit this file to set application according to your needs
* be sure to correctly set the proxy  in etc/app.json. If there's no proxy, set an empty string
* copy etc/server.cfg.DIST into etc/server.cfg, see http://flask.pocoo.org/docs/0.10/config/#builtin-configuration-values
* if mdchecker sits behind a reverse proxy, be sure to set SERVER_NAME accordingly
* run create_db.py once to create the local database
