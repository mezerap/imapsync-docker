import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('migration', Path(__file__).resolve().parents[1] / 'migrate.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def account(identifier, enabled=False):
    endpoint = {'host': 'mail.example.com', 'user': 'test@example.com', 'password_file': 'test.txt'}
    return {'id': identifier, 'enabled': enabled, 'source': endpoint.copy(), 'target': endpoint.copy(),
            'folder_map': {'Trash/2023': 'trash'}}


class CliTests(unittest.TestCase):
    def setUp(self):
        self.accounts = [account('one'), account('two', True), account('three', True)]

    def test_multiple_selection_preserves_json_order_and_deduplicates(self):
        self.assertEqual(m.parse_selection('3, 1 3', self.accounts), [self.accounts[0], self.accounts[2]])
        self.assertEqual(m.parse_selection('vše', self.accounts), self.accounts)
        for value in ('0', '4', '-1', '', 'one'):
            with self.assertRaises(ValueError):
                m.parse_selection(value, self.accounts)

    def test_each_mode_has_expected_effect(self):
        for mode in m.MODES:
            command = m.build_command(self.accounts[0], mode)
            self.assertEqual('--dry' in command, mode in ('plan', 'dry-run', 'folders-dry-run'))
            self.assertEqual('--justfolders' in command, mode in ('folders', 'folders-dry-run'))
            self.assertEqual('--justlogin' in command, mode == 'check')
            self.assertEqual('--justfoldersizes' in command, mode == 'sizes')
            self.assertIn('Trash/2023=trash', command)
            self.assertIn('--nosyncduplicates', command)
            self.assertNotIn('--delete1', command)
            self.assertNotIn('--delete2', command)

    def test_writing_mode_requires_affirmative_answer(self):
        for mode in m.WRITING_MODES:
            with patch('builtins.input', return_value=''), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(m.Cancelled):
                    m.review_selection([self.accounts[0]], mode)

    def test_wizard_default_is_dry_run_and_retry_invalid_account(self):
        with patch('builtins.input', side_effect=['99', '1,2', '']), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(m.select_interactively(self.accounts), self.accounts[:2])
            self.assertEqual(m.select_mode(), 'dry-run')

    def test_cancelled_wizard_cannot_start_docker(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / 'accounts.json'
            config.write_text(json.dumps(self.accounts))
            with patch('sys.argv', ['migrate.py', '--config', str(config)]), patch.object(m.sys.stdin, 'isatty', return_value=True), patch('builtins.input', side_effect=['1', '6', '']), patch.object(m.subprocess, 'run') as run, contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(m.Cancelled):
                    m.main()
                run.assert_not_called()

    def test_all_excludes_disabled_but_explicit_account_is_one_time(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / 'accounts.json'
            original = json.dumps(self.accounts)
            config.write_text(original)
            with patch('sys.argv', ['migrate.py', '--config', str(config), '--all']), patch.object(m, 'run_accounts', return_value=0) as run:
                self.assertEqual(m.main(), 0)
                run.assert_called_once_with(self.accounts[1:], 'plan')
            with patch('sys.argv', ['migrate.py', '--config', str(config), '--account', 'one', '--mode', 'check']), patch.object(m, 'run_accounts', return_value=0) as run:
                self.assertEqual(m.main(), 0)
                run.assert_called_once_with([self.accounts[0]], 'check')
            self.assertEqual(config.read_text(), original)

    def test_lock_prevents_parallel_runs_and_releases(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(m, 'ROOT', Path(folder)):
            with m.migration_lock():
                with self.assertRaises(ValueError):
                    with m.migration_lock():
                        self.fail('Second run acquired the lock')
            with m.migration_lock():
                pass


if __name__ == '__main__':
    unittest.main()
