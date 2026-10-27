import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from clean_tv import Cleaner, SAVER, atomic_json
from clean_snapshot import Snapshot, merge_owned_list, settings_map, PACKAGE, restore_notification_list
from clean_install import install, setup_home


class FakeAdb:
    def __init__(self, state=0):
        self.state = state
        self.writes = []
        self.device = {'device': 'a' * 64, 'model': 'TV', 'firmware': 'v1'}
        self.fail_after_write = False

    def identity(self): return dict(self.device)
    def package_state(self): return self.state
    def set_package(self, value):
        self.state = value
        self.writes.append(value)
        if self.fail_after_write: raise RuntimeError('Connection lost after command')


class CleanerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.adb = FakeAdb()
        self.cleaner = Cleaner(self.adb, self.tmp.name)

    def test_full_restore_preserves_default_state_not_explicit_enable(self):
        self.assertEqual('applied', self.cleaner.apply('one'))
        self.assertEqual('restored', self.cleaner.restore())
        self.assertEqual([3, 0], self.adb.writes)

    def test_explicit_enabled_restores_one(self):
        self.adb.state = 1
        self.cleaner.apply('one'); self.cleaner.restore()
        self.assertEqual(1, self.adb.state)

    def test_previously_disabled_never_owned_or_reenabled(self):
        for value in (2, 3, 4):
            self.adb.state = value
            self.assertEqual('unchanged', self.cleaner.apply('one'))
            self.assertFalse(self.cleaner.can_restore())
            self.assertEqual('unchanged', self.cleaner.restore())
        self.assertEqual([], self.adb.writes)

    def test_repeated_apply_keeps_first_snapshot(self):
        self.cleaner.apply('one')
        original = self.cleaner.load()
        self.cleaner.apply('two')
        self.assertEqual(original['before'], self.cleaner.load()['before'])
        self.assertEqual(original['id'], self.cleaner.load()['id'])
        self.assertEqual([3], self.adb.writes)

    def test_external_change_is_not_overwritten(self):
        self.cleaner.apply('one'); self.adb.state = 2
        self.assertEqual('conflict', self.cleaner.restore())
        self.assertEqual(2, self.adb.state)

    def test_disconnect_after_write_can_be_restored(self):
        self.adb.fail_after_write = True
        with self.assertRaises(RuntimeError): self.cleaner.apply('one')
        self.assertEqual('failed', self.cleaner.load()['state'])
        self.adb.fail_after_write = False
        self.cleaner.restore()
        self.assertEqual(0, self.adb.state)

    def test_firmware_change_blocks_restore(self):
        self.cleaner.apply('one'); self.adb.device['firmware'] = 'v2'
        with self.assertRaises(RuntimeError): self.cleaner.restore()
        self.assertEqual([3], self.adb.writes)

    def test_journal_cannot_target_stock_home(self):
        self.cleaner.apply('one')
        data = self.cleaner.load(); data['target'] = 'com.mitv.tvhome'
        atomic_json(self.cleaner.path, data)
        with self.assertRaises(RuntimeError): self.cleaner.restore()

    def test_new_cycle_archives_previous_snapshot(self):
        self.cleaner.apply('one'); old = self.cleaner.load()['id']
        self.cleaner.restore(); self.adb.state = 1; self.cleaner.apply('two')
        self.assertEqual(1, self.cleaner.load()['before'])
        self.assertTrue(self.cleaner.path.with_name('history-' + old + '.json').exists())

    def test_journal_is_durable_before_mutation(self):
        def verify_before(value):
            data = json.loads(self.cleaner.path.read_text())
            self.assertEqual('applying', data['state'])
            self.assertEqual(0, data['before'])
            self.adb.state = value
        self.adb.set_package = verify_before
        self.cleaner.apply('one')


class SnapshotAdb(FakeAdb):
    def __init__(self):
        super().__init__()
        self.values = {'setting:secure:screensaver_components': None,
                       'setting:secure:enabled_accessibility_services': 'other/.Service',
                       'setting:secure:enabled_notification_listeners': None,
                       'setting:secure:accessibility_enabled': '1',
                       'op:SYSTEM_ALERT_WINDOW': 'ignore',
                       'guard': {'keep_adb': None, 'own_screensaver': None, 'clean_restore_hold': None}}

    def exchange(self, command, data=None):
        if command == 'guard_hold':
            self.values['guard'] = {'keep_adb': False, 'own_screensaver': False, 'clean_restore_hold': True}
        return {}

    def shell(self, *args):
        if args[:2] == ('am', 'force-stop'):
            key = 'setting:secure:enabled_accessibility_services'
            self.values[key] = ':'.join(x for x in (self.values[key] or '').split(':') if not x.startswith(PACKAGE + '/'))
        return ''


class FakeSnapshot(Snapshot):
    def state(self): return copy.deepcopy(self.adb.values)
    def write(self, key, value):
        self.adb.writes.append((key, value))
        self.adb.values[key] = value


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.adb = SnapshotAdb(); self.snap = FakeSnapshot(self.adb, self.tmp.name)

    def change(self):
        self.adb.values['setting:secure:screensaver_components'] = PACKAGE + '/.dream.AerialDream'
        self.adb.values['setting:secure:enabled_accessibility_services'] += ':' + PACKAGE + '/.guard.HomeGuardService'
        self.adb.values['op:SYSTEM_ALERT_WINDOW'] = 'allow'
        self.adb.values['guard']['own_screensaver'] = True

    def test_null_missing_and_literal_null_are_distinct(self):
        self.assertEqual({'a': 'null', 'b': '', 'c': 'one=two'}, settings_map('a=null\nb=\nc=one=two'))
        self.assertIsNone(settings_map('a=null').get('absent'))

    def test_exact_original_values_restored(self):
        before = self.snap.state(); self.snap.capture(); self.change(); self.snap.record(); self.snap.restore()
        self.assertEqual(before, self.snap.state())
        self.assertEqual('restored', self.snap.load()['status'])

    def test_repeated_snapshot_retains_original(self):
        before = self.snap.state(); self.snap.capture(); self.change(); self.snap.capture()
        self.assertEqual(before, self.snap.load()['before'])

    def test_later_accessibility_service_preserved(self):
        self.snap.capture(); self.change(); self.snap.record()
        key = 'setting:secure:enabled_accessibility_services'
        self.adb.values[key] += ':new/.Service'
        self.snap.restore()
        self.assertEqual('other/.Service:new/.Service', self.adb.values[key])

    def test_nonlist_conflict_pauses_before_any_write(self):
        self.snap.capture(); self.change(); self.snap.record()
        self.adb.values['op:SYSTEM_ALERT_WINDOW'] = 'deny'
        with self.assertRaises(RuntimeError): self.snap.restore()
        self.assertEqual([], self.adb.writes)

    def test_interrupted_capture_requires_review(self):
        self.snap.capture(); self.change()
        with self.assertRaises(RuntimeError): self.snap.restore()
        self.assertEqual([], self.adb.writes)

    def test_no_change_does_not_stop_existing_guard(self):
        self.snap.capture(); self.snap.record(); before = self.snap.state(); self.snap.restore()
        self.assertEqual(before, self.snap.state()); self.assertEqual([], self.adb.writes)

    def test_list_merge_restores_original_null(self):
        self.assertIsNone(merge_owned_list(None, PACKAGE + '/.Guard', PACKAGE + '/.Guard'))

    def test_literal_null_accessibility_state_restores_exactly(self):
        self.adb.values['setting:secure:enabled_accessibility_services'] = 'null'
        self.adb.values['setting:secure:accessibility_enabled'] = '0'
        before = self.snap.state(); self.snap.capture()
        self.adb.values['setting:secure:enabled_accessibility_services'] = PACKAGE + '/.guard.HomeGuardService'
        self.adb.values['setting:secure:accessibility_enabled'] = '1'
        self.snap.record(); self.snap.restore()
        self.assertEqual(before, self.snap.state())

    def test_restore_retry_after_partial_failure(self):
        self.snap.capture(); self.change(); self.snap.record()
        real_write = self.snap.write
        count = 0
        def fail_once(key, value):
            nonlocal count
            count += 1
            real_write(key, value)
            if count == 2: raise RuntimeError('Disconnected')
        self.snap.write = fail_once
        with self.assertRaises(RuntimeError): self.snap.restore()
        self.snap.write = real_write
        self.snap.restore()
        self.assertEqual(self.snap.load()['before'], self.snap.state())


class InstallerTests(unittest.TestCase):
    def test_unsupported_firmware_cannot_change_home(self):
        adb = FakeAdb()
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(RuntimeError): setup_home(adb, folder)
            self.assertEqual([], list(Path(folder).rglob('*')))

    def test_failed_snapshot_blocks_permission_changes(self):
        adb = FakeAdb()
        adb.device.update(model='MiTV-MFTR0', firmware='OS3.0.101.0.UFTMATV')
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(Snapshot, 'capture', side_effect=RuntimeError('Disk full')):
                with self.assertRaisesRegex(RuntimeError, 'Disk full'): setup_home(adb, folder)
        self.assertEqual([], adb.writes)

    def test_install_conflict_does_not_uninstall_or_start(self):
        class ConflictAdb(FakeAdb):
            def run(self, *args, **kwargs):
                self.writes.append(args)
                return 'Failure [INSTALL_FAILED_UPDATE_INCOMPATIBLE]'
        adb = ConflictAdb()
        with tempfile.TemporaryDirectory() as folder:
            apk = Path(folder) / 'app.apk'; apk.write_bytes(b'fixture')
            with self.assertRaises(RuntimeError): install(adb, apk)
        self.assertEqual(1, len(adb.writes))
        self.assertEqual(('install', '-r'), adb.writes[0][:2])


class NotificationRestoreTests(unittest.TestCase):
    def test_authoritative_grant_is_revoked_and_other_listener_is_kept(self):
        class Notifications:
            value = 'other/.Listener:' + PACKAGE + '/' + PACKAGE + '.GuardRevival'
            calls = []
            def shell(self, *args):
                self.calls.append(args)
                if args[:5] == ('settings','--user','0','list','secure'):
                    return 'enabled_notification_listeners=' + self.value
                if args[:3] == ('cmd','notification','disallow_listener'):
                    self.value = 'other/.Listener'
                return ''
        adb=Notifications()
        restore_notification_list(adb,'other/.Listener')
        self.assertIn(('cmd','notification','disallow_listener',PACKAGE+'/'+PACKAGE+'.GuardRevival','0'),adb.calls)
        self.assertFalse(any(x[:3]==('cmd','notification','disallow_listener') and x[3].startswith('other/') for x in adb.calls))

    def test_short_and_full_names_do_not_cause_a_second_grant(self):
        class Notifications:
            calls=[]
            def shell(self,*args):
                self.calls.append(args)
                return 'enabled_notification_listeners='+PACKAGE+'/'+PACKAGE+'.GuardRevival' if args[3:5]==('list','secure') else ''
        adb=Notifications();restore_notification_list(adb,PACKAGE+'/.GuardRevival')
        self.assertFalse(any(x[0]=='cmd' for x in adb.calls))


if __name__ == '__main__': unittest.main()
