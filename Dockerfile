FROM python:2.7

MAINTAINER Fabrice PHUNG "fabrice.phung@geobretagne.fr"

WORKDIR "/app"

RUN pip install \
    uwsgi \
    flask \
    flask_sqlalchemy \
    OWSLib \
    lxml \
    pyshp

COPY app /app

EXPOSE 5000

#~ RUN ["python", "/app/create_db.py"]
#~ ENTRYPOINT ["uwsgi"]
#~ CMD ["--socket", "0.0.0.0:5000", "--module", "mdchecker", "--chdir", "/app"]

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uwsgi", "--socket", "0.0.0.0:5000", "--module", "mdchecker", "--chdir", "/app"]