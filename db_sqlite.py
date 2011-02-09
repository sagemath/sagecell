import db

import sqlite3
class DB(db.DB):
    def __init__(self, c):
        """c is a string that gives the filename of the connection."""
        self._filename = c
        self._c = None

    @property
    def c(self):
        if self._c is None:
            self._c = sqlite3.connect(self._filename)
        return self._c
        
    def create_cell(self, input):
        """
        Insert the input text into the database.
        """
        cur = self.c.cursor()
        cur.execute("insert into cells (input,output) values (?,null);", (input,))
        self.c.commit()
        return str(cur.lastrowid)
        
    def get_unevaluated_cells(self, device_id, limit=None):
        """
        Get cells which still have yet to be evaluated.
        """
        cur = self.c.cursor()
        if limit:
            cur.execute("""select ROWID, input from cells where output is null and device_id is null limit ?;""",(limit,))
        else:
            cur.execute("""select ROWID, input from cells where output is null and device_id is null""")
        results = [dict(_id=u, input=v) for u,v in cur.fetchall()]
        cur.executemany("""update cells set device_id = ? where ROWID = ?""",[(device_id, row['_id']) for row in results])
        self.c.commit()
        return results
        
    def get_evaluated_cells(self, id=None):
        """
        Get inputs and outputs which have been evaluated
        """
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
                return dict(zip(["_id", "input", "output"], result))
            else:
                return None

    def set_output(self, id, output):
        """
        """
        cur = self.c.cursor()
        cur.execute("update cells set output=? where ROWID=?;", (output, id))
        self.c.commit()
