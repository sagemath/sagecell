import db

# TODO: implement
#conn = sqlite3.connect('/tmp/example')
#c = conn.cursor()

#CREATE TABLE test1(input TEXT, output TEXT DEFAULT NULL);

class DB_sqlite(db.DB):    
    def create_cell(self, input):
        """
        Insert the input text into the database.
        """
        c=self.c.cursor()
        c.execute("""insert into cells (input,output) values (:input,null)""", 
                  {'input':input})
        
    def get_unevaluated_cells(self):
        """
        Get cells which still have yet to be evaluated.
        """
        c=self.c.cursor()
        c.execute("""select ROWID, input from cells where output is null;""")
        return [dict(_id=u, input=v) for u,v in c.fetchall()]
        
    def get_evaluated_cells(self):
        """
        Get inputs and outputs which have been evaluated
        """
        c=self.c.cursor()
        c.execute("""select ROWID, input, output from cells where output is not null;""")
        return [dict(_id=u, input=v, output=w) for u,v,w in c.fetchall()]

    def set_output(self, id, output):
        """
        """
        c=self.c.cursor()
        c.execute("""insert into cells (input) values (:input) where ROWID=:id""",
                  {'input': input, 'id': id})

