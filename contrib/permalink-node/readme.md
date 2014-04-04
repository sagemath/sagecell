node install
node app # port 3000

Table structure

- ident: short string, primary key
- code: string (limited to perhaps 5k?)
- language: string
- interacts: string (will be json, but we dont have to inist on it
- created: datetime
- last_access: datetime (for purging old data when it gets too large
- requested: integer -- how many times it has been requested



Setting up Cassandra:

    create keyspace cellserver with replication={'class':'SimpleStrategy','replication_factor':1};
    USE cellserver;
    CREATE TABLE permalinks (
      ident varchar PRIMARY KEY,
      code varchar,
      language varchar,
      interacts varchar,
      created timestamp,
      last_access timestamp,
    );
    CREATE TABLE permalink_count (
      ident varchar PRIMARY KEY,
      requested counter
    );

When creating an entry:

- make up random short ident
- insert into database (IF NOT EXISTS) -- if error, then retry
- return ident

When retrieving an entry

- select on ident; return error if ident is not found
- update last_access record
- update permalink_count record
- return code, language, interacts fields
