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
        
    def get_input_messages(self, device_id, limit=None):
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
        
    def set_output(self, id, output):
        """
        """
        import json
        cur = self.c.cursor()
        cur.execute("update cells set output=? where ROWID=?;", (json.dumps(output), id))
        self.c.commit()

