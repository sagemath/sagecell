"""
SQLAlchemy Database Adapter
---------------------------
"""
import db
import json
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from util import log

class DB(db.DB):
    """
    SQLAlchemy database adaptor
    
    :arg db_file str: the SQLAlchemy URI for a database file
    """
    def __init__(self, db_file=None):
        if db_file is not None:
            engine = create_engine(db_file)
            self.SQLSession = sessionmaker(bind=engine)
            Base.metadata.create_all(engine)
            self.new_context()

    def new_input_message(self, msg):
        """
        See :meth:`db.DB.new_input_message`
        """
        msg['timestamp'] = str(datetime.utcnow())
        message = InputMessage(json_message=json.dumps(msg))
        jsonMessageSync(message, False)
        m = self.dbsession.query(Session.device_id) \
                .filter_by(session_id=msg['header']['session']).first()
        message.device_id = m.device_id if m is not None else None
        message.evaluated = False
        jsonMessageSync(message, True)
        self.dbsession.add(message)
        self.dbsession.commit()

    def get_input_messages(self, device, limit=None):
        """
        See :meth:`db.DB.get_input_messages`
        """
        device_messages = self.dbsession.query(InputMessage).filter_by(device_id=device, evaluated=False).all()
        for row in device_messages:
            row.evaluated = True
            jsonMessageSync(row, True)
        if limit == 0:
            unassigned_messages = []
        else:
            q = self.dbsession \
                    .query(InputMessage).filter_by(device_id=None, evaluated=False)
            if limit is not None:
                q = q.limit(limit)
            unassigned_messages = q.all()
            for row in unassigned_messages:
                row.evaluated = True
                row.device_id = device
                jsonMessageSync(row, True)
            if len(unassigned_messages) > 0:
                log("DEVICE %s took SESSIONS %s"%(device,
                        [m.session_id for m in unassigned_messages]))
        self.dbsession.commit()
        device_messages = [json.loads(m.json_message) for m in device_messages]
        unassigned_messages = [json.loads(m.json_message) for m in unassigned_messages]
        self.dbsession.add_all([Session(session_id=m['header']['session'],
                                        device_id=device) for m in unassigned_messages])
        return device_messages + unassigned_messages

    def get_input_message_by_shortened(self, shortened):
        """
        See :meth:`db.DB.get_input_message_by_shortened`
        """
        msg = self.dbsession.query(InputMessage.code) \
                  .filter_by(shortened=shortened).first()
        return msg.code if msg is not None else ""

    def add_messages(self, messages):
        """
        See :meth:`db.DB.add_messages`
        """
        msgs = [Message(json_message=json.dumps(m)) for m in messages]
        for m in msgs:
            jsonMessageSync(m, False)
        self.dbsession.add_all(msgs)
        self.dbsession.commit()
        log("INSERTED: %s" % ('\n'.join(str(m) for m in messages),))

    def register_device(self, device, account, workers, pgid):
        """
        See :meth:`db.DB.register_device`
        """
        device = Device(device_id=device, account=account, workers=workers, pgid=pgid)
        self.dbsession.add(device)
        self.dbsession.commit()
        log("REGISTERED DEVICE: %s" % (device,))

    def delete_device(self, device):
        """
        See :meth:`db.DB.delete_device`
        """
        self.dbsession.query(DB.Device).filter(device_id=device).delete()
        self.dbsession.commit()


    def get_devices(self):
        """
        See :meth:`db.DB.get_devices`
        """
        return [{'device': row.device_id, 'account': row.account,
                 'pgid': row.pgid, 'workers': row.workers} for row in
                 self.dbsession.query(DB.Device)]

    def get_messages(self, session, sequence=0):
        """
        See :meth:`db.DB.get_messages`
        """
        messages = self.dbsession.query(Message.json_message) \
                       .filter_by(parent_session=session) \
                       .filter(Message.sequence >= sequence).all()
        return [json.loads(m.json_message) for m in messages]

    def close_session(self, device, session):
        """
        See :meth:`db.DB.close_session`
        """
        self.dbsession.query(Session).filter_by(session_id=session, device_id=device).delete()
        self.dbsession.commit()

    def new_context(self):
        """
        See :meth:`db.DB.new_context`
        """
        self.dbsession = self.SQLSession()

    def new_context_copy(self):
        """
        See :meth:`db.DB.new_context_copy`
        """
        new = type(self)()
        new.SQLSession = self.SQLSession
        new.new_context()
        return new

    valid_untrusted_methods=('get_input_messages', 'close_session', 'add_messages')

Base = declarative_base()

class Session(Base):
    """Table of Sage Cell sessions"""
    __tablename__ = 'sessions'
    session_id = Column(String, primary_key=True)
    device_id = Column(String)

class Device(Base):
    """Table of devices"""
    __tablename__ = 'devices'
    device_id = Column(String, primary_key=True)
    account = Column(String)
    workers = Column(Integer)
    pgid = Column(Integer)

class InputMessage(Base):
    """
    Table of input messages in JSON form. See :func:`jsonMessageSync`
    """
    __tablename__ = 'input_messages'
    equiv = {'device_id': ['device'], 'session_id': ['header', 'session'],
             'evaluated': ['evaluated'], 'shortened': ['shortened'],
             'code': ['content', 'code']}
    n = Column(Integer, primary_key = True)
    json_message = Column("json_message", String)
    device_id = Column(String)
    session_id = Column(String)
    evaluated = Column(Boolean)
    shortened = Column(String)
    code = Column(String)

class Message(Base):
    """
    Table of output messages in JSON form. See :func:`jsonMessageSync`
    """
    __tablename__ = 'messages'
    equiv = {'parent_session': ['parent_header', 'session'],
             'sequence': ['sequence']}
    n = Column(Integer, primary_key = True)
    json_message = Column("json_message", String)
    parent_session = Column(String)
    sequence = Column(Integer)

def jsonMessageSync(row, syncToJSON):
    """
    Synchronizes the values of the JSON message stored in a database row. These
    types have a single string field for the JSON message (so that the message
    can be stored without needing to store every field as a column), as well as 
    properties corresponding to a subset of the fields stored in the JSON object 
    or its sub-objects (so that these properties are searchable in the
    database). These types also have a property called ``equiv``, which is a
    :class:`dict` that maps the name of a column to the a list representing the
    "path" of the corresponding value in the JSON object.
    
    When one of the properties of a JSON message object is changed, this function
    should be called before committing. Its effect is to synchronize the
    value of the JSON-formatted string field with the database column and keep
    the two storage locations consistant with one another.
    
    :arg Base row: the database row to be synchronized
    :arg bool syncToJSON: if ``True``, modify the JSON object field to match the
        values of the column fields. If ``False``, modify the column fields to
        match the JSON object.
    """
    if not hasattr(row, 'json_message'):
        return
    for name, path in row.equiv.iteritems():
        if not syncToJSON or hasattr(row, name):
            json_dict = sub = json.loads(row.json_message)
            for i in range(0, len(path) - 1):
                if path[i] not in sub:
                    sub[path[i]] = {}
                sub = sub[path[i]]
            if syncToJSON:
                sub[path[-1]] = getattr(row, name)
            elif path[-1] in sub:
                setattr(row, name, sub[path[-1]])
    if syncToJSON:
        row.json_message = json.dumps(json_dict)
