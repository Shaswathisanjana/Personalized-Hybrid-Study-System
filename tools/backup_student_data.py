"""Create a consistent SQLite backup without changing the source database."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]


def backup_database(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not source.is_file():
        raise FileNotFoundError('Source database does not exist.')
    if source == destination:
        raise ValueError('Backup destination must differ from source.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents overwriting any existing destination.
    with destination.open('xb'):
        pass
    try:
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as original:
            with closing(sqlite3.connect(destination)) as target:
                original.backup(target)
                if target.execute('PRAGMA integrity_check').fetchone() != ('ok',):
                    raise RuntimeError('Backup integrity check failed.')
    except Exception:
        # Retain the failed artifact for inspection; never remove existing data.
        raise RuntimeError('Backup failed; destination may be incomplete. Source was not modified.') from None
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'data/student_state/phss.sqlite3')
    parser.add_argument('--destination', type=Path)
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destination = args.destination or ROOT / 'data/student_state/backups' / f'phss-{stamp}.sqlite3'
    try:
        saved = backup_database(args.source, destination)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, str(exc) + '\n')
    print(f'Consistent backup created: {saved}')


if __name__ == '__main__':
    main()
