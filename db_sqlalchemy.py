"""
SQLAlchemy Database Adapter
---------------------------
"""

import string, random
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

import db


Base = declarative_base()

class ExecMessage(Base):
    """
    Table of input messages in JSON form.
    """
    __tablename__ = "permalinks"
    ident = Column(String, primary_key=True, index=True)
    code = Column(String)
    language = Column(String)
    interacts = Column(String)
    created = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    requested = Column(Integer, default=0)


class DB(db.DB):
    """
    SQLAlchemy database adapter

    :arg db_file str: the SQLAlchemy URI for a database file
    """

    def __init__(self, db_file):
        self.engine = create_engine(db_file)
        self.SQLSession = sessionmaker(bind = self.engine)
        Base.metadata.create_all(self.engine)
        self.dbsession = self.SQLSession()

    def new_exec_msg(self, code, language, interacts, callback):
        """
        See :meth:`db.DB.new_exec_msg`
        """
        while True:
            ident = "".join(random.choice(string.lowercase) for _ in range(6))
            message = ExecMessage(
                ident=ident, code=code, language=language, interacts=interacts)
            try:
                self.dbsession.add(message)
                self.dbsession.commit()
            except IntegrityError:
                # ident was used before
                self.dbsession.rollback()
            else:
                break
        callback(ident)

    def get_exec_msg(self, key, callback):
        """
        See :meth:`db.DB.get_exec_msg`
        """
        msg = self.dbsession.query(ExecMessage).filter_by(ident=key).first()
        if msg:
            msg.requested = ExecMessage.requested + 1
            self.dbsession.commit()
        if msg is None:
            raise LookupError
        callback(msg.code, msg.language, msg.interacts)
