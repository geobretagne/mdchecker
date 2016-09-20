import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('mdchecker')

sys.path.append(os.getcwd())
from mdchecker.main import db


if __name__ == '__main__':

    logger.info(u"Creation of the database: {0}".format(db.app and db.app.config['SQLALCHEMY_DATABASE_URI'] or None))
    db.create_all()
    if not db.engine.has_table('test_session'):
        logger.error(u"Database creation failed")
    else:
        logger.info(u"Database creation succeeded")
