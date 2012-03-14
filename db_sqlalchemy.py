import db

from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, DateTime, text, select

class DB(db.DB):
    def __init__(self, c):
        """c is a string that gives the filename of the connection."""
        self._filename = c
        self._c = create_engine('sqlite:///%s'%self._filename)
        meta = MetaData(bind=self._c)
        self._messages = Table('messages', meta,
                                 Column('_id', Integer, primary_key=True),
                                 Column('session', String, index=True),
                                 Column('sequence', Integer, index=True),
                                 Column('message', String))
        self._input_messages = Table('input_messages', meta,
                                     Column('_id', Integer, primary_key=True),
                                     Column('message', String),
                                     Column('evaluated', Boolean, index=True),
                                     Column('device', String, nullable=True),
                                     Column('shortened', String,nullable=True),
            Column('timestamp', DateTime))
            #, server_default=text('NOW()')))
        self._devices = Table('devices', meta,
                                    Column('_id', Integer, primary_key=True),
                                    Column('session', String, index=True),
                                    Column('device', String, index=True))
        #not used
        self._ipython_port_table = Table('ipython_port', meta,
                                         Column('_id', Integer, primary_key=True),
                                         Column('pid', Integer),
                                         Column('xreq', Integer),
                                         Column('sub', Integer),
                                         Column('rep', Integer))
        meta.create_all()


    def new_input_message(self, msg):
        # look up the device corresponding to the session id
        # look up device; None means a device has not yet been assigned
        # Note that this makes it easy for an attacker to inject messages into a session
        # if they can snoop the session ID
        t=self._devices
        query = select([t.c.device]).where(t.c.session==msg['header']['session']).limit(1)
        row=query.execute().fetchone()
        if row:
            device = row[t.c.device]
            row.close()
        else:
            device = None
        self._input_messages.insert().execute(message=json.dumps(msg), evaluated=False, device=device)

    def get_input_message_by_shortened(self, shortened):
        """
        Retrieve the input code for a shortened field
        """
        raise NotImplementedError
        doc=self.database.input_messages.find_one({'shortened': shortened}, {'content.code': 1})
        if doc is not None:
            return doc['content']['code']
        else:
            return ""

    def get_input_messages(self, device, limit=None):
        """
        See :meth:`db.DB.get_input_messages`
        """
        t=self._devices
        m=self._input_messages
        # find the non-evaluated messages for sessions already on this device
        c=self._c.connect()
        with c.begin():
            # we use a transaction so that the select and update happen together
            r=c.execute(select([m.c._id,m.c.message]).where(and_(m.c.device==device,m.c.evaluated==False)))
            p=c.execute(update(m).values(evaluated=True).where(and_(m.c.device==device,m.c.evaluated==False)))

        device_messages = [row[m.c.message] for row in r]
        # Now get new messages that aren't assigned to a device
        # if limit is 0, don't do the query (just return empty list)
        # if limit is None or negative, do the query without limit
        # otherwise do the query with the specified limit

        if limit==0:
            unassigned_messages=[]
        else:
            q=self.database.input_messages.find({'device':None,
                                          'evaluated':False})
            if limit is not None and limit>=0:
                q=q.limit(limit)
            
            unassigned_messages=list(q)
            if len(unassigned_messages)>0:
                self.database.input_messages.update({'_id': {'$in': [i['_id'] for i in unassigned_messages]}, 
                                              '$atomic':True}, 
                                             {'$set': {'device': device, 'evaluated':True}}, multi=True)
                self.database.sessions.insert([{'session':m['header']['session'], 'device':device} 
                                        for m in unassigned_messages])
                log("DEVICE %s took SESSIONS %s"%(device,
                                                    [m['header']['session']
                                                     for m in unassigned_messages]))
        return device_messages+unassigned_messages

    def close_session(self, device, session):
        """
        See :meth:`db.DB.close_session`
        """
        # remove the device/session record from the sessions table
        pass
    
    def get_messages(self, session, sequence=0):
        """
        See :meth:`db.DB.get_messages`
        """
        # get all messages from self._messages with the given session id that also
        # has a sequence number >= the given sequence number
        # order by sequence number ascending
        return messages

    def add_messages(self, messages):
        """
        See :meth:`db.DB.add_messages`
        """
        # insert the list of messages into self._messages.  Extract the sequence and parent_header['session']
        # to be able to insert that information into the appropriate columns
        pass
        log("INSERTED: %s"%('\n'.join(str(m) for m in messages),))

    def register_device(self, device, account, workers, pgid):
        """
        See :meth:`db.DB.register_device`
        """
        # Insert into self._devices the record with the device, account, workers, and pgid info
        log("REGISTERED DEVICE: %s"%doc)

    def delete_device(self, device):
        """
        See :meth:`db.DB.delete_device`
        """
        # delete the device record from self._devices
        self.database.device.remove({'device': device})

    def get_devices(self):
        """
        See :meth:`db.DB.get_devices`
        """
        # get all self._devices
        pass

    def new_context(self):
        """
        Reconnect to the database. This function should be
        called before the first database access in each new process.
        """
        # should anything be done here to connect?  I don't think we need to do anything

    valid_untrusted_methods=('get_input_messages', 'close_session', 'add_messages')

    # The following is old code that may or may not be useful in getting the idea of how to write queries
    # it can be deleted once the code for the above functions is working

    def set_ipython_ports(self, kernel):
        """
        See :meth:`db.DB.set_ipython_ports`
        """
        pass
    
    def get_ipython_port(self, channel):
        """
        See :meth:`db.DB.get_ipython_port`
        """
        pass

    def create_cell(self, input):
        """
        Insert the input text into the database.
        """
        t=self._cells_table
        result = t.insert().values(input=input).execute()
        return result.inserted_primary_key[0]
        
    def get_unevaluated_cells(self, device_id, limit=None):
        """
        Get cells which still have yet to be evaluated.
        """
        t=self._cells_table
        query = select([t.c._id,t.c.input], (t.c.output==None) & (t.c.device_id==None))
        if limit:
            query = query.limit(limit)
        results=[dict(_id=u, input=v) for u,v in query.execute()]
        if len(results)!=0:
            t.update().where(t.c._id.in_(row["_id"] for row in results)).values(device_id=device_id).execute()
        return results
        
    def get_evaluated_cells(self, id=None):
        """
        Get inputs and outputs which have been evaluated
        """
        import json
        t=self._cells_table
        query = select([t.c._id, t.c.input, t.c.output]).where(t.c.output!=None).order_by(t.c._id.desc())
        if id is None:
            results = [dict(_id=u, input=v, output=w) for u,v,w in query.execute()]
            return results
        else:
            result = query.where(t.c._id==id).execute().first()
            if result is not None:
                results=dict(zip(["_id", "input", "output"], result))
                results['output']=json.loads(results['output'])
                return results
            else:
                return None

    def set_output(self, id, output):
        """
        """
        import json
        t=self._cells_table
        t.update().where(t.c._id==id).values(output=json.dumps(output)).execute()

