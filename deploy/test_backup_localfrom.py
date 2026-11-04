"""Credential handling and backup scope checks; no real database or restic calls."""
import importlib.util
from pathlib import Path
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location('localfrom_backup', Path(__file__).with_name('backup_localfrom.py'))
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


class BackupSafetyTests(unittest.TestCase):
    def values(self, **changes):
        return {'DB_NAME': 'localfrom', 'DB_USER': 'localfrom_app',
                'DB_HOST': '127.0.0.1', 'DB_PASSWORD': 'synthetic-only', **changes}

    def test_credentials_are_quoted_against_option_file_injection(self):
        result = backup.client_options(self.values(DB_PASSWORD='synthetic"\\\nuser=other\t'))
        self.assertEqual(len(result.splitlines()), 5)
        self.assertIn('password="synthetic\\"\\\\\\nuser=other\\t"', result)

    def test_credentials_are_not_passed_in_process_arguments(self):
        arguments = backup.dump_arguments('/private/options')
        self.assertEqual(arguments[1], '--defaults-extra-file=/private/options')
        self.assertNotIn('synthetic-only', ' '.join(arguments))
        self.assertIn('--single-transaction', arguments)
        self.assertNotIn('--databases', arguments)
        self.assertEqual(arguments[-1], 'localfrom')

    def test_unexpected_database_and_remote_host_fail_closed(self):
        for changes in ({'DB_NAME': 'other'}, {'DB_USER': 'root'},
                        {'DB_HOST': 'remote.example'}, {'DB_PASSWORD': ''}):
            with self.subTest(changes=list(changes)), self.assertRaises(backup.BackupError):
                backup.client_options(self.values(**changes))
        with self.assertRaises(backup.BackupError):
            backup.client_options(self.values(DB_PASSWORD='synthetic\x00only'))

    def test_only_root_private_regular_credential_files_are_accepted(self):
        path = Mock()
        for mode, owner in ((stat.S_IFREG | 0o600, 0), (stat.S_IFREG | 0o400, 0)):
            path.lstat.return_value = SimpleNamespace(st_mode=mode, st_uid=owner)
            backup.private_file(path)
        for mode, owner in ((stat.S_IFREG | 0o644, 0), (stat.S_IFREG | 0o600, 1000),
                            (stat.S_IFLNK | 0o777, 0)):
            path.lstat.return_value = SimpleNamespace(st_mode=mode, st_uid=owner)
            with self.assertRaises(backup.BackupError):
                backup.private_file(path)

    def test_backup_includes_private_media_and_config_but_never_its_decryption_password(self):
        arguments = backup.backup_arguments()
        sources = list(map(str, backup.SOURCES))
        self.assertIn(str(backup.ENVIRONMENT), sources)
        self.assertIn(str(Path('/srv/localfrom/storage')), sources)
        self.assertIn(str(Path('/etc/letsencrypt')), sources)
        self.assertNotIn(str(backup.PASSWORD), sources)
        self.assertNotIn(str(Path('/etc/localfrom')), sources)
        self.assertNotIn(str(backup.REPOSITORY), sources)
        self.assertIn('--password-file', arguments)
        self.assertFalse(any(word in arguments for word in ('forget', 'prune', 'restore')))


if __name__ == '__main__':
    unittest.main()
