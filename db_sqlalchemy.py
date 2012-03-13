import db

from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, select

class DB(db.DB):
    def __init__(self, c):
        """c is a string that gives the filename of the connection."""
        self._filename = c
        self._c = create_engine('sqlite:///%s'%self._filename)
        meta = MetaData(bind=self._c)
        self._messages_table = Table('cells', meta,
                                 Column('_id', Integer, primary_key=True),
                                 Column('device_id', Integer),
                                 Column('input', String),
                                 Column('output', String))
        self._devices_table = Table('devices', meta,
                                    Column('_id', Integer, primary_key=True),
                                    Column('session', Integer),
                                    Column('device', Integer))
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
        t=self._devices_table
        query = select([t.c._id,t.c.device], (t.c.session==msg['header']['session'])).limit(1)
        results=[dict(_id=u, input=v) for u,v in query.execute()]
        if len(results)!=0:
            msg['device'] = results[0]['device']
 
        msg['evaluated']=False
        import datetime
        msg['timestamp']=datetime.datetime.utcnow()
        t.self._messages.insert(...)

    def get_input_message_by_shortened(self, shortened):
        """
        Retrieve the input code for a shortened field
        """
        doc=self.database.input_messages.find_one({'shortened': shortened}, {'content.code': 1})
        if doc is not None:
            return doc['content']['code']
        else:
            return ""

    def get_input_messages(self, device, limit=None):
        """
        See :meth:`db.DB.get_input_messages`
        """
        # find the sessions for this device
        device_messages=list(self.database.input_messages.find({'device':device, 'evaluated':False }))
        if len(device_messages)>0:
            self.database.input_messages.update({'_id':{'$in': [i['_id'] for i in device_messages]},
                                          '$atomic':True},
                                         {'$set': {'evaluated':True}}, multi=True)

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
        self.database.sessions.remove({'session':session, 'device':device})    

    def get_messages(self, session, sequence=0):
        """
        See :meth:`db.DB.get_messages`
        """
        messages=list(self.database.messages.find({'parent_header.session':session,
                                            'sequence':{'$gte':sequence}}))
        #TODO: just get the fields we want instead of deleting the ones we don't want
        for m in messages:
            del m['_id']
        return messages

    def add_messages(self, messages):
        """
        See :meth:`db.DB.add_messages`
        """
        self.database.messages.insert(messages)
        log("INSERTED: %s"%('\n'.join(str(m) for m in messages),))

    def register_device(self, device, account, workers, pgid):
        """
        See :meth:`db.DB.register_device`
        """
        doc={"device":device, "account":account, "workers": workers, "pgid":pgid}
        self.database.device.insert(doc)
        log("REGISTERED DEVICE: %s"%doc)

    def delete_device(self, device):
        """
        See :meth:`db.DB.delete_device`
        """
        self.database.device.remove({'device': device})

    def get_devices(self):
        """
        See :meth:`db.DB.get_devices`
        """
        return list(self.database.device.find())

    def set_ipython_ports(self, kernel):
        """
        See :meth:`db.DB.set_ipython_ports`
        """
        self.database.ipython.remove()
        self.database.ipython.insert({"pid":kernel[0].pid, "xreq":kernel[1], "sub":kernel[2], "rep":kernel[3]})
    
    def get_ipython_port(self, channel):
        """
        See :meth:`db.DB.get_ipython_port`
        """
        return self.database.ipython.find().next()[channel]

    def new_context(self):
        """
        Reconnect to the database. This function should be
        called before the first database access in each new process.
        """
        self.database=pymongo.database.Database(self.c, mongo_config['mongo_db'])
        uri=mongo_config['mongo_uri']
        if '@' in uri:
            # strip off optional mongodb:// part
            if uri.startswith('mongodb://'):
                uri=uri[len('mongodb://'):]
            result=self.database.authenticate(uri[:uri.index(':')],uri[uri.index(':')+1:uri.index('@')])
            if result==0:
                raise Exception("MongoDB authentication problem")

    valid_untrusted_methods=('get_input_messages', 'close_session', 'add_messages')
        

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

