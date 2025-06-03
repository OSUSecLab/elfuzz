E
VACUUM;
PRAGMA foreign_key_check=TRUE;
PRAGMA list=TRUE;
PRAGMA cache_size=1000;
	CREATE TABLE IF NOT EXISTS th (
		ch TEXT,
		dh TEXT,
		eh TEXT,
		PRIMARY KEY (ch, dh)
	);
	INSERT INTO th VALUES ('C', 'q4', '');
	INSERT INTO th VALUES ('', '8', '');
	INSERT INTO th VALUES ('', '', '_D');
	INSERT INTO th VALUES ('A~', '@,6', '|');
	INSERT INTO th VALUES ('', '', '');
	DELETE FROM th WHERE ch='	F' AND ch='uk' AND ch='';
	DELETE FROM th WHERE ch='CyV' AND ch='B' AND ch='b';
	DELETE FROM th WHERE ch='$' AND ch='!
X' AND ch='U[l';
	DELETE FROM th WHERE ch='.' AND ch='$' AND ch='/';
	DELETE FROM th WHERE ch='uP' AND ch='' AND ch='';
	UPDATE th SET dh='H', eh=' ', ch='X' WHERE ch='H' AND ch=' ' AND ch='X';
	UPDATE th SET dh='`dZ', eh='$', ch='O}
' WHERE ch='`dZ' AND ch='$' AND ch='O}
';
	UPDATE th SET dh='', eh='', ch='I' WHERE ch='' AND ch='' AND ch='I';
	UPDATE th SET dh='', eh='i', ch='l' WHERE ch='' AND ch='i' AND ch='l';
	UPDATE th SET dh='2Q', eh='', ch='xO' WHERE ch='2Q' AND ch='' AND ch='xO';
	SELECT  FROM th  ORDER BY ch, dh  OFFSET 9;
	SELECT dh FROM th   LIMIT 4 OFFSET 9;
	SELECT eh FROM th WHERE ch LIKE '=%' AND dh=')'   ;
	SELECT  FROM th  ORDER BY ch, dh LIMIT 2 OFFSET 8;
	SELECT ch, dh, eh FROM th WHERE ch LIKE 'd%' AND dh=''  LIMIT 9 ;
	SELECT * FROM th;
	DELETE FROM th WHERE ch=?;
	UPDATE th SET dh=? WHERE ch=?;
	CREATE TRIGGER IF NOT EXISTS trigh AFTER INSERT ON th BEGIN SELECT RAISE(ABORT,'This is an error message!'); END;
	DROP TRIGGER IF EXISTS trigh;
	CREATE VIEW IF NOT EXISTS viewh AS SELECT * FROM th;
	DROP VIEW IF EXISTS viewh;
	CREATE INDEX IF NOT EXISTS idxh ON th (ch, dh, eh);
	DROP INDEX IF EXISTS idxh;
	COMMIT TRANSACTION;
