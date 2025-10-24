MMEC Chatbot — SQLite database guide

This project can use a lightweight SQLite database to store histories, users, and settings.

Files:
 - data/mmec.db         <-- SQLite database (created by migration script)
 - data/histories/*.json  <-- legacy JSON history files (migrated)
 - data/settings.json   <-- persisted settings (migrated into settings table)

How to migrate existing JSON histories into SQLite:

1. Run the migration script (Python 3.8+ required):

   python scripts/migrate_histories_to_sqlite.py

2. The script creates `data/mmec.db`. To inspect it:

   - With sqlite3 CLI (Windows PowerShell):
     sqlite3.exe data/mmec.db
       Then at the sqlite prompt run: .tables  or  SELECT count(*) FROM histories;

   - Or with DB Browser for SQLite (GUI): Open `data/mmec.db` and browse tables.

Admin: updating data and accessing DB

 - To update histories: use SQL INSERT or DELETE against the `histories` table.
 - To change settings: UPDATE the `settings` table or use the admin UI to toggle `allow_external_queries` which will be mirrored to the DB when migration is run.
 - Production note: For concurrency or multi-user production use, migrate to PostgreSQL/MySQL and update `app.py` to use SQLAlchemy.

If you want, I can add optional admin endpoints to read/write these tables directly from the web UI (requires Admin auth).
