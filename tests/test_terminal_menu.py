from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import terminal_menu as menu
import migrate


class Screen:
    def __init__(self, keys):
        self.keys = iter(keys)
    def keypad(self, value): pass
    def erase(self): pass
    def refresh(self): pass
    def getmaxyx(self): return (12, 100)
    def addnstr(self, *args): pass
    def get_wch(self): return next(self.keys)


class MenuTests(unittest.TestCase):
    def run_menu(self, keys, **options):
        screen = Screen(keys)
        with patch.object(menu.curses, 'wrapper', side_effect=lambda fn, *args: fn(screen, *args)):
            return menu.choose('Test', ['one', 'two', 'three'], **options)

    def test_arrows_and_space_select_multiple(self):
        self.assertEqual(self.run_menu([menu.curses.KEY_DOWN, ' ', menu.curses.KEY_UP, ' ', '\n'], multiple=True), [0, 1])

    def test_enter_selects_focused_account(self):
        self.assertEqual(self.run_menu([menu.curses.KEY_DOWN, '\n'], multiple=True), [1])

    def test_select_all_and_toggle_off(self):
        self.assertEqual(self.run_menu(['a', '\n'], multiple=True), [0, 1, 2])
        self.assertEqual(self.run_menu(['a', 'a', '\n'], multiple=True), [0])

    def test_defaults_and_cancel(self):
        self.assertEqual(self.run_menu(['\n'], default=2), 2)
        for key in ('q', '\x1b'):
            with self.assertRaises(menu.MenuCancelled): self.run_menu([key])

    def test_writing_confirmation_defaults_to_cancel(self):
        account = {'id': 'test', 'source': {'host': 'old.example.com'}, 'target': {'host': 'new.example.com'}}
        with patch.object(migrate, 'use_arrow_menu', return_value=True), patch.object(migrate, 'arrow_choice', return_value=0) as choose:
            with self.assertRaises(migrate.Cancelled): migrate.review_selection([account], 'sync')
            self.assertEqual(choose.call_args.kwargs['default'], 0)


if __name__ == '__main__':
    unittest.main()
