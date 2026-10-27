import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from clean_install import setup_home, end_maintenance
from clean_snapshot import Snapshot


class GuardAdb:
    def __init__(self):
        self.guard = {'keep_adb': True, 'stock': True, 'enabled': False}
        self.calls = []
    def identity(self):
        return {'device': 'f' * 64, 'model': 'MiTV-MFTR0', 'firmware': 'OS3.0.101.0.UFTMATV'}
    def shell(self, *args):
        self.calls.append(args)
        if args[:5] == ('settings', '--user', '0', 'list', 'secure'):
            return 'enabled_accessibility_services=other/.Reader'
        return ''
    def exchange(self, command, data=None):
        if command == 'guard_restore': self.guard = copy.deepcopy(data)
        return copy.deepcopy(self.guard)


class PublicMaintenanceTests(unittest.TestCase):
    def setup_guard(self, keep_adb=None):
        adb = GuardAdb()
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(Snapshot, 'capture'), patch.object(Snapshot, 'record'):
                if keep_adb is None: setup_home(adb, Path(folder))
                else: setup_home(adb, Path(folder), keep_adb=keep_adb)
        return adb
    def test_default_disables_existing_keep_adb_preference_without_changing_stock_choice(self):
        adb = self.setup_guard()
        self.assertFalse(adb.guard['keep_adb'])
        self.assertTrue(adb.guard['stock'])
        self.assertTrue(adb.guard['enabled'])
        self.assertFalse(any('adb_enabled' in call for call in adb.calls))
    def test_explicit_maintenance_opt_in(self):
        self.assertTrue(self.setup_guard(True).guard['keep_adb'])
    def test_end_maintenance_preserves_other_guard_fields_and_connection(self):
        adb = GuardAdb(); original = dict(adb.guard)
        end_maintenance(adb)
        original['keep_adb'] = False
        self.assertEqual(original, adb.guard)
        self.assertEqual([], adb.calls)
    def test_end_maintenance_must_read_back_saved_state(self):
        adb = GuardAdb()
        adb.exchange = lambda command, data=None: {'keep_adb': True}
        with self.assertRaisesRegex(RuntimeError, 'did not settle'):
            end_maintenance(adb)


if __name__ == '__main__': unittest.main()
