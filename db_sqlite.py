import db

import sqlite3
class DB(db.DB):    
    def create_cell(self, input):
        """
        Insert the input text into the database.
        """
        conn=sqlite3.connect(self.c)
        c=conn.cursor()
        c.execute("insert into cells (input,output) values (?,null);", (input,))
        conn.commit()
        conn.close()
        
    def get_unevaluated_cells(self):
        """
        Get cells which still have yet to be evaluated.
        """
        conn=sqlite3.connect(self.c)
        c=conn.cursor()
        c.execute("""select ROWID, input from cells where output is null;""")
        results=[dict(_id=u, input=v) for u,v in c.fetchall()]
        conn.close()
        return results
        
    def get_evaluated_cells(self):
        """
        Get inputs and outputs which have been evaluated
        """
        conn=sqlite3.connect(self.c)
        c=conn.cursor()
        c.execute("""select ROWID, input, output from cells where output is not null ORDER BY ROWID DESC;""")
        results=[dict(_id=u, input=v, output=w) for u,v,w in c.fetchall()]
        conn.close()
        return results

    def set_output(self, id, output):
        """
        """
        conn=sqlite3.connect(self.c)
        conn.cursor().execute("update cells set output=? where ROWID=?;", (output, id))
        conn.commit()
        conn.close()
