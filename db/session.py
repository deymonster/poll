from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import logging
from core import config
from core.local_config import settings


# logging.basicConfig()
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
engine = create_engine(config.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
