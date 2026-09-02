"""Create a consistent SQLite backup using SQLite's online backup API."""

import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Back up an UpNext SQLite database safely.")
    parser.add_argument("database", type=Path, help="Absolute path to the source SQLite database")
    parser.add_argument("backup_directory", type=Path, help="Directory where the backup will be created")
    args = parser.parse_args()
    source_path = args.database.expanduser().resolve()
    if not source_path.is_file():
        raise SystemExit(f"Database does not exist: {source_path}")
    backup_directory = args.backup_directory.expanduser().resolve()
    backup_directory.mkdir(parents=True, exist_ok=True)
    target_path = backup_directory / f"upnext-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.db"
    with sqlite3.connect(source_path) as source, sqlite3.connect(target_path) as target:
        source.backup(target)
    print(target_path)


if __name__ == "__main__":
    main()
