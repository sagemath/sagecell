"""
SQLAlchemy Database Adapter
---------------------------
"""

"""
System library imports
"""
import json, uuid
from datetime import datetime

"""
SQLAlchemy imports
"""
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

"""
Generic database adapter import
"""
import db

class DB(db.DB):
    """
    SQLAlchemy database adapter

    :arg db_file str: the SQLAlchemy URI for a database file
    """

    def __init__(self, db_file):
        self.db_file = db_file
        self.engine = create_engine(db_file)
        self.SQLSession = sessionmaker(bind = self.engine)
        Base.metadata.create_all(self.engine)
        self.dbsession = self.SQLSession()

    def new_exec_msg(self, msg):
        """
        See :meth:`db.DB.new_exec_msg`
        """
        message = ExecMessage()
        message.ident = str(uuid.uuid4())
        message.timestamp = str(datetime.utcnow())

        retval = None
        try:
            message.code = str(msg["content"]["code"])
            message.json_message = json.dumps(msg)
            self.dbsession.add(message)
            self.dbsession.commit()
            retval = message.ident
        except:
            pass

        return retval

    def get_exec_msg(self, ident):
        """
        See :meth:`db.DB.get_exec_msg`
        """
        msg = self.dbsession.query(ExecMessage.code).filter_by(ident = ident).first()
        return msg.code if msg is not None else ""



Base = declarative_base()

class ExecMessage(Base):
    """
    Table of input messages in JSON form.
    """
    __tablename__ = "exec_messages"
    n = Column(Integer, primary_key = True)
    ident = Column(String)
    code = Column(String)
