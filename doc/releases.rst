05 Aug 2013: commit 831f5d
--------------------------

* [gh-422] Upgrade to jQuery 2.0.3
* [gh-422] Fix bug where interact control labels did not render with MathJax
* [377b7] Implement readonly and locations attributes for interacts
* [56f50] If output=False for an interact, disable the red rectangle highlight

15 Aug 2013
-----------

* [471930] Added many more python packages: pandas, scikit-learn,
    statsmodels, patsy, numexpr, scikits-image, scimath, Shapely, SimPy, pyproj,
    bitarray, basemap, PyTables, netcdf4, h5py
* [gh-426] Fix bug that prevented the iOS app and Safari from working
* Turned on the required agreement to the terms of service
* Implemented Google Analytics tracking
* Moved development over to sage-on-git and updated distribution
  methods
* Made progress on collecting statistics and logging use besides
  Google Analytics

27 Aug 2013
-----------

* Bookmarks for interacts.  This requires a database upgrade:

BEGIN TRANSACTION;
ALTER TABLE permalinks RENAME TO permalinksOld;
DROP INDEX ix_permalinks_ident;
CREATE TABLE permalinks (
	ident VARCHAR NOT NULL,
	code VARCHAR,
	language VARCHAR,
	interacts VARCHAR,
	created TIMESTAMP,
	last_accessed TIMESTAMP,
	requested INTEGER,
	PRIMARY KEY (ident)
);
INSERT INTO permalinks (ident, code, language, created, last_accessed, requested)
SELECT ident, code, language, created, last_accessed, requested FROM permalinksOld;
CREATE INDEX ix_permalinks_ident ON permalinks (ident);
COMMIT;

Check to make sure it works, then do

DROP TABLE permalinksOld;
