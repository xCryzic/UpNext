import sqlite3
from flask import current_app

from config import Config


def ensure_database_directory():
    database_path().parent.mkdir(
        parents=True,
        exist_ok=True,
    )


def get_db():
    ensure_database_directory()

    connection = sqlite3.connect(
        database_path()
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


def database_path():
    try:
        return current_app.config["DATABASE_PATH"]
    except RuntimeError:
        return Config.DATABASE_PATH


def init_db(config=None):
    database_config = config or Config
    connection = get_db()

    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS creators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE,
                bio TEXT DEFAULT '',
                avatar TEXT DEFAULT '',
                location TEXT,
                website TEXT,
                is_public INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS social_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                username TEXT NOT NULL,
                profile_url TEXT NOT NULL,
                follower_count INTEGER,
                ownership_verified INTEGER NOT NULL DEFAULT 0,
                eligibility_verified INTEGER NOT NULL DEFAULT 0,
                verification_status TEXT NOT NULL DEFAULT 'unverified',
                provider_account_id TEXT,
                verified_at TEXT,
                last_checked_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (creator_id)
                    REFERENCES creators(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                type TEXT DEFAULT '',
                url TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (creator_id)
                    REFERENCES creators(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS creator_categories (
                creator_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                PRIMARY KEY (creator_id, category),
                FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS creator_skills (
                creator_id INTEGER NOT NULL,
                skill TEXT NOT NULL,
                PRIMARY KEY (creator_id, skill),
                FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS creator_looking_for (
                creator_id INTEGER NOT NULL,
                item TEXT NOT NULL,
                PRIMARY KEY (creator_id, item),
                FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_user_id INTEGER NOT NULL,
                creator_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                details TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reporter_user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS spotify_oauth_attempts (
                state TEXT PRIMARY KEY,
                social_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                claimed_user_id TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (social_id) REFERENCES social_accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            """
        )

        existing_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(creators)").fetchall()
        }
        if "created_at" not in existing_columns:
            connection.execute("ALTER TABLE creators ADD COLUMN created_at TEXT NOT NULL DEFAULT ''")
        if "updated_at" not in existing_columns:
            connection.execute("ALTER TABLE creators ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''")
        if "is_public" not in existing_columns:
            connection.execute("ALTER TABLE creators ADD COLUMN is_public INTEGER NOT NULL DEFAULT 1")

        social_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(social_accounts)").fetchall()
        }
        social_migrations = {
            "follower_count": "INTEGER",
            "ownership_verified": "INTEGER NOT NULL DEFAULT 0",
            "eligibility_verified": "INTEGER NOT NULL DEFAULT 0",
            "verification_status": "TEXT NOT NULL DEFAULT 'unverified'",
            "provider_account_id": "TEXT",
            "verified_at": "TEXT",
            "last_checked_at": "TEXT",
            "created_at": "TEXT NOT NULL DEFAULT ''",
            "updated_at": "TEXT NOT NULL DEFAULT ''",
        }
        for column, definition in social_migrations.items():
            if column not in social_columns:
                connection.execute(f"ALTER TABLE social_accounts ADD COLUMN {column} {definition}")

        project_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(projects)").fetchall()
        }
        for column in ("created_at", "updated_at"):
            if column not in project_columns:
                connection.execute(f"ALTER TABLE projects ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")

        report_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(reports)").fetchall()
        }
        if "status" not in report_columns:
            connection.execute("ALTER TABLE reports ADD COLUMN status TEXT NOT NULL DEFAULT 'open'")

        connection.execute("CREATE INDEX IF NOT EXISTS idx_creators_username ON creators(username)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_creators_updated_at ON creators(updated_at)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_social_accounts_creator ON social_accounts(creator_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_projects_creator ON projects(creator_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_reports_creator ON reports(creator_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_spotify_oauth_attempts_social ON spotify_oauth_attempts(social_id)")

        connection.commit()

    finally:
        connection.close()
