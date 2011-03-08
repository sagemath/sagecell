import db

import sqlite3
import sqlalchemy
from sqlalchemy import create_engine, MetaData, Table

class DB(db.DB):
    def __init__(self, c):
        """c is a string that gives the filename of the connection."""
        self._filename = c
        self._c = create_engine('sqlite:///%s'%self._filename)
        meta = MetaData()
        meta.bind = self._c
        self._cells_table = Table('cells', meta, autoload=True)

    @property
    def c(self):
        if self._c is None:
            self._c = create_engine('sqlite:///%s'%self._filename)
            meta = MetaData()
            meta.bind = engine
            self._cells_table = Table('cells', meta, autoload=True)
        return self._c
        
    def create_cell(self, input):
        """
        Insert the input text into the database.
        """
        insert = self._cells_table.insert().values(input=input)
        print str(insert)
        result = self._c.execute(insert)
        return result.inserted_primary_key
        
    def get_unevaluated_cells(self, device_id, limit=None):
        """
        Get cells which still have yet to be evaluated.
        """
        t=self._cells_table
        query = t.select().where((t.output==None) & (t.device_id==None))
        if limit:
            query = query.limit(limit)
        results=[dict(_id=u, input=v) for u,v in query.execute()]
        t.update(t.c._id.in_(row["_id"] for row in results),t.c.device_id=device_id).execute()
        return results
        
    def get_evaluated_cells(self, id=None):
        """
        Get inputs and outputs which have been evaluated
        """
        import json
        cur = self.c.cursor()
        if id is None:
            cur.execute("""select ROWID, input, output from cells
                           where output is not null ORDER BY ROWID DESC;""")
            results = [dict(_id=u, input=v, output=w) for u,v,w in cur.fetchall()]
            return results
        else:
            cur.execute("""select ROWID, input, output from
                           cells where output is not null and ROWID = ? ORDER BY ROWID DESC;""",(id,))
            result=cur.fetchone()
            if result:
                results=dict(zip(["_id", "input", "output"], result))
                results['output']=json.loads(results['output'])
                return results
            else:
                return None

    def set_output(self, id, output):
        """
        """
        import json
        cur = self.c.cursor()
        cur.execute("update cells set output=? where ROWID=?;", (json.dumps(output), id))
        self.c.commit()

