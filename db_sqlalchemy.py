import db

import sqlite3
import sqlalchemy
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, select

class DB(db.DB):
    def __init__(self, c):
        """c is a string that gives the filename of the connection."""
        self._filename = c
        self._c = create_engine('sqlite:///%s'%self._filename)
        meta = MetaData()
        meta.bind = self._c
        
        
        self._cells_table = Table('cells', meta,
                                 Column('_id', Integer, primary_key=True),
                                 Column('device_id', Integer),
                                 Column('input', String),
                                 Column('output', String))
        meta.create_all()

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

