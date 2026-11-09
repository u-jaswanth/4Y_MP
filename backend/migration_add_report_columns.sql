-- Run this once against your existing Postgres database.
-- There's no Alembic/migration tool in this project, so new columns
-- have to be added by hand (SQLAlchemy's Base.metadata isn't wired
-- up to auto-create/alter tables here either).

ALTER TABLE reports ADD COLUMN IF NOT EXISTS report_name VARCHAR;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS report_type VARCHAR;
