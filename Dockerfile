FROM python:2.7.12

RUN apt-get update && apt-get install -y \
    uwsgi-plugin-python \
    nginx supervisor
COPY flask.conf /etc/nginx/sites-available/
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY app /var/www/app

RUN mkdir -p /var/log/nginx/app /var/log/uwsgi/app /var/log/supervisor \
    && rm /etc/nginx/sites-enabled/default \
    && ln -s /etc/nginx/sites-available/flask.conf /etc/nginx/sites-enabled/flask.conf \
    && echo "daemon off;" >> /etc/nginx/nginx.conf

RUN pip install -r /var/www/app/requirements.txt

RUN chown -R www-data:www-data /var/www/app \
    && chown -R www-data:www-data /var/log

RUN ["python", "/var/www/app/create_db.py"]

CMD ["/usr/bin/supervisord"]