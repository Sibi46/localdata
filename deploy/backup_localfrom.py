#!/srv/localfrom/venv/bin/python
"""Root-only local encrypted backup. Never restores or prunes production data."""
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

from dotenv import dotenv_values

ENVIRONMENT = Path('/etc/localfrom/localfrom.env')
PASSWORD = Path('/etc/localfrom/restic-password')
REPOSITORY = Path('/var/backups/localfrom-restic')
WORK = Path('/var/lib/localfrom-backup')
CACHE = Path('/var/cache/localfrom-backup')
APP = Path('/srv/localfrom/app')
SOURCES = (
    WORK / 'payload', Path('/srv/localfrom/storage'), APP, ENVIRONMENT,
    Path('/etc/nginx'), Path('/etc/letsencrypt'),
    Path('/etc/systemd/system/localfrom.service'),
    Path('/etc/systemd/system/localfrom-backup.service'),
    Path('/etc/systemd/system/localfrom-backup.timer'),
    Path('/etc/mysql/conf.d/zz-localfrom.cnf'), Path('/etc/redis/redis.conf'),
)


class BackupError(Exception):
    pass


def private_file(path):
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != 0 or metadata.st_mode & 0o077:
        raise BackupError('Backup credentials must be root-owned private regular files.')


def option_value(value):
    value = str(value)
    if '\x00' in value:
        raise BackupError('Invalid database option value.')
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace(
        '\n', '\\n').replace('\r', '\\r').replace('\t', '\\t') + '"'


def client_options(values):
    if (values.get('DB_NAME') != 'localfrom' or values.get('DB_USER') != 'localfrom_app'
            or values.get('DB_HOST') != '127.0.0.1' or not values.get('DB_PASSWORD')):
        raise BackupError('Unexpected database configuration; backup stopped.')
    return '[client]\n' + ''.join(
        f'{key}={option_value(value)}\n' for key, value in (
            ('host', values['DB_HOST']), ('port', int(values.get('DB_PORT', '3306'))),
            ('user', values['DB_USER']), ('password', values['DB_PASSWORD']),
        )
    )


def dump_arguments(options_file):
    return [
        '/usr/bin/mysqldump', '--defaults-extra-file=' + str(options_file),
        '--single-transaction', '--quick', '--no-tablespaces',
        '--set-gtid-purged=OFF', '--routines', '--events', 'localfrom',
    ]


def backup_arguments():
    return [
        '/usr/bin/restic', '-r', str(REPOSITORY), '--password-file', str(PASSWORD),
        '--cache-dir', str(CACHE), 'backup', '--tag', 'localfrom',
        '--exclude', str(APP / '.git'),
        '--exclude', '/srv/localfrom/storage/cache',
        '--exclude', '/srv/localfrom/storage/static',
        *map(str, SOURCES),
    ]


def main():
    if os.geteuid() != 0:
        raise BackupError('Run this backup as root.')
    os.umask(0o077)
    private_file(ENVIRONMENT)
    private_file(PASSWORD)
    if not (REPOSITORY / 'config').is_file():
        raise BackupError('Encrypted backup repository is not initialized.')
    for directory in (WORK, WORK / 'payload', CACHE):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    for path in SOURCES:
        if not path.exists():
            raise BackupError('A required backup source is missing; inspect the backup configuration.')
    if shutil.disk_usage(WORK).free < 1024 ** 3:
        raise BackupError('Less than 1 GiB free: backup stopped; inspect disk usage.')

    import fcntl
    with (WORK / 'backup.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise BackupError('Another LocalFrom backup is already running.') from None
        options = client_options(dotenv_values(ENVIRONMENT))
        # Credentials stay in a root-private temporary file, never argv or logs.
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=WORK,
                                         prefix='.mysql-options-') as credentials:
            credentials.write(options)
            credentials.flush()
            with tempfile.NamedTemporaryFile(dir=WORK, prefix='.database-') as dump:
                subprocess.run(dump_arguments(credentials.name), stdout=dump, check=True)
                dump.flush()
                if os.fstat(dump.fileno()).st_size == 0:
                    raise BackupError('Database dump is empty; backup stopped.')
                # Copy only a completed dump into the stable snapshot path.
                # The payload remains root-private; old snapshots are untouched.
                dump.seek(0)
                with (WORK / 'payload' / 'localfrom.sql').open('wb') as payload:
                    shutil.copyfileobj(dump, payload)
        commit = subprocess.check_output(
            ['/usr/bin/git', '-C', str(APP), 'rev-parse', 'HEAD'], text=True,
        ).strip()
        (WORK / 'payload' / 'application-commit.txt').write_text(commit + '\n')
        subprocess.run(backup_arguments(), check=True)
        print('LOCALFROM ENCRYPTED BACKUP COMPLETE', flush=True)


if __name__ == '__main__':
    try:
        main()
    except BackupError as error:
        sys.exit(str(error))
    except subprocess.CalledProcessError as error:
        sys.exit('Backup command failed: ' + Path(error.cmd[0]).name
                 + '. No successful backup is confirmed; inspect its error output.')
    except OSError as error:
        sys.exit('Backup filesystem/process failure: ' + type(error).__name__)
