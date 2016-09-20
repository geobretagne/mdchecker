import os
import sys
import logging
import sqlalchemy.exc

logging.basicConfig(level=logging.INFO)

sys.path.append(os.getcwd())
from mdchecker.main import db


if __name__ == '__main__':

    logging.info(u"Creation of the database: {0}".format(db.app and db.app.config['SQLALCHEMY_DATABASE_URI'] or None))

    try:
        db.create_all()

        if db.engine.has_table('test_session'):
            logging.info(u"Database creation succeeded")

    except sqlalchemy.exc.OperationalError as e:
        msg = u"Database creation failed - {0} - {1}".format(
            type(e),
            e.message
        )
        logging.error(msg)
        logging.info(u"Check the path of the database file that should have been created")
