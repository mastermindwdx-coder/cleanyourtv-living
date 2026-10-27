"""First-write installation snapshot and conflict-aware restore for the custom build.

Called after APK installation but BEFORE upstream permission/home changes. APK installation
and application data are not undone. Package cleanup has its own independent journal.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time
from clean_tv import Adb, PACKAGE, atomic_json, single_instance

SETTINGS = {'secure': ['screensaver_components', 'screensaver_enabled',
                       'enabled_accessibility_services', 'accessibility_enabled', 'enabled_notification_listeners'],
            'global': ['adb_enabled']}
OPS = ['SYSTEM_ALERT_WINDOW', 'WRITE_SETTINGS', 'REQUEST_INSTALL_PACKAGES',
       'GET_USAGE_STATS', 'APP_AUTO_START', 'APP_ASSOC_START']
PERMISSIONS = ['android.permission.ACCESS_FINE_LOCATION', 'android.permission.WRITE_SECURE_SETTINGS']
PROPERTY = 'persist.vt.use_home_pkg'
UNSUPPORTED = {'unsupported': True}


def settings_map(text):
    return dict(line.split('=', 1) for line in text.splitlines() if '=' in line)


def notification_members(value):
    def canonical(entry):
        package, component = entry.split('/', 1)
        return package + '/' + (package + component if component.startswith('.') else component)
    return {canonical(x) for x in (value or '').split(':') if '/' in x}


def restore_notification_list(adb, value):
    """Update NotificationManager's persistent grants too, not just its Settings projection."""
    key = 'enabled_notification_listeners'
    current = settings_map(adb.shell('settings', '--user', '0', 'list', 'secure')).get(key)
    before, wanted = notification_members(current), notification_members(value)
    for component in sorted(before - wanted):
        if component.startswith(PACKAGE + '/'):
            adb.shell('cmd', 'notification', 'disallow_listener', component, '0')
    for component in sorted(wanted - before):
        if component.startswith(PACKAGE + '/'):
            adb.shell('cmd', 'notification', 'allow_listener', component, '0')
    for _ in range(20):
        observed = settings_map(adb.shell('settings', '--user', '0', 'list', 'secure')).get(key)
        if notification_members(observed) == wanted:
            adb.shell('settings', '--user', '0', 'delete' if value is None else 'put',
                      'secure', key, *([] if value is None else [value]))
            return
        time.sleep(0.1)
    raise RuntimeError('Notification listener grant restoration has not settled')


def merge_owned_list(before, after, current):
    """Reverse our membership delta without discarding services added by someone else."""
    if current == after:
        return before
    parts = lambda value: [] if value in (None, '', 'null') else [x for x in value.split(':') if x]
    old, new, now = parts(before), parts(after), parts(current)
    ours = lambda value: value.startswith(PACKAGE + '/')
    added = [x for x in new if x not in old and ours(x)]
    removed = [x for x in old if x not in new and ours(x)]
    result = [x for x in now if x not in added]
    result.extend(x for x in removed if x not in result)
    return ':'.join(result) if result else (None if before is None else '')


class Snapshot:
    def __init__(self, adb, directory):
        self.adb = adb
        self.identity = adb.identity()
        self.path = Path(directory) / self.identity['device'][:20] / 'installation.json'

    def state(self):
        result = {}
        for table, keys in SETTINGS.items():
            values = settings_map(self.adb.shell('settings', '--user', '0', 'list', table))
            for key in keys:
                result[f'setting:{table}:{key}'] = values.get(key)
        for op in OPS:
            try:
                text = self.adb.shell('appops', 'get', '--user', '0', PACKAGE, op)
                match = re.search(r'\b(?:' + op + r'|android:get_usage_stats):\s*(allow|ignore|deny|default|foreground)\b', text)
                if match:
                    value = match.group(1)
                elif 'No operations' in text:
                    value = 'default'
                else:
                    raise RuntimeError('Unknown app-op output')
            except RuntimeError as error:
                if re.search(r'unknown (operation|op)|invalid operation|not a valid op', str(error), re.I):
                    value = UNSUPPORTED
                else:
                    raise
            result['op:' + op] = value
        dump = self.adb.shell('dumpsys', 'package', PACKAGE)
        for permission in PERMISSIONS:
            matches = re.findall(re.escape(permission) + r': granted=(true|false)', dump)
            if not matches:
                raise RuntimeError('Cannot determine original permission: ' + permission)
            result['permission:' + permission] = matches[-1] == 'true'
        result['property:' + PROPERTY] = self.adb.shell('getprop', PROPERTY)
        home = self.adb.shell('cmd', 'package', 'resolve-activity', '--brief', '--user', '0',
                              '-a', 'android.intent.action.MAIN', '-c', 'android.intent.category.HOME').splitlines()[-1]
        if not re.fullmatch(r'[A-Za-z0-9_.]+/[A-Za-z0-9_.$]+', home):
            raise RuntimeError('No unambiguous original Home; snapshot cannot guarantee recovery')
        result['home'] = home
        result['guard'] = self.adb.exchange('guard_state')
        return result

    def load(self):
        data = json.loads(self.path.read_text(encoding='utf-8'))
        if data['identity'] != self.adb.identity():
            raise RuntimeError('Snapshot belongs to another device or firmware')
        return data

    def capture(self):
        if self.path.exists():
            data = self.load()
            if data['status'] != 'restored':
                print('Retaining the original installation snapshot.')
                return
            atomic_json(self.path.with_name('installation-' + str(data['created']) + '.json'), data)
        atomic_json(self.path, {'schema': 1, 'identity': self.identity, 'created': int(time.time()),
                               'status': 'prepared', 'before': self.state(), 'after': None})

    def record(self):
        data = self.load()
        data['after'] = self.state()
        data['status'] = 'recorded'
        atomic_json(self.path, data)

    def write(self, key, value):
        parts = key.split(':', 2)
        if key == 'setting:secure:enabled_notification_listeners':
            restore_notification_list(self.adb, value)
        elif parts[0] == 'setting' and parts[1] in SETTINGS and parts[2] in SETTINGS[parts[1]]:
            self.adb.shell('settings', '--user', '0', 'delete' if value is None else 'put',
                           parts[1], parts[2], *([] if value is None else [value]))
        elif parts[0] == 'op' and parts[1] in OPS:
            self.adb.shell('appops', 'set', '--user', '0', PACKAGE, parts[1], value)
        elif parts[0] == 'permission' and parts[1] in PERMISSIONS:
            self.adb.shell('pm', 'grant' if value else 'revoke', '--user', '0', PACKAGE, parts[1])
        elif key == 'property:' + PROPERTY:
            self.adb.shell('setprop', PROPERTY, value)
        elif key == 'home':
            self.adb.shell('cmd', 'package', 'set-home-activity', '--user', '0', value)
        elif key == 'guard':
            self.adb.exchange('guard_restore', value)
        else:
            raise ValueError('Unknown restore target')

    def restore(self):
        data = self.load()
        if data['status'] == 'restored':
            return
        if data['after'] is None:
            raise RuntimeError('Installation was interrupted before its receipt; review live state before restoring')
        before, after, current = data['before'], data['after'], self.state()
        targets, conflicts = {}, []
        for key, original in before.items():
            if original == UNSUPPORTED or original == after[key]:
                continue
            now = current[key]
            if now == original:
                continue
            if key.endswith(':enabled_accessibility_services') or key.endswith(':enabled_notification_listeners'):
                targets[key] = merge_owned_list(original, after[key], now)
            elif now == after[key]:
                targets[key] = original
            else:
                conflicts.append(key)
        # Do not switch accessibility off while another service still needs it.
        service_key = 'setting:secure:enabled_accessibility_services'
        enabled_key = 'setting:secure:accessibility_enabled'
        services = targets.get(service_key, current[service_key])
        if services not in (None, '', 'null') and targets.get(enabled_key, '1') != '1':
            conflicts.append(enabled_key)
            targets.pop(enabled_key, None)
        if data['status'] in ('restoring', 'restore_failed') and 'restore_targets' in data:
            # Resume the durable plan rather than treating our temporary hold as a user change.
            targets = data['restore_targets']
            conflicts = []
            observed = data['restore_observed']
            for key, wanted in targets.items():
                now = current[key]
                if now in (wanted, observed[key]):
                    continue
                if key == 'guard' and now.get('clean_restore_hold') is True:
                    continue
                if key.endswith(':enabled_accessibility_services'):
                    remaining = ':'.join(x for x in (observed[key] or '').split(':') if x and not x.startswith(PACKAGE + '/'))
                    if (now or '') == remaining:
                        continue
                conflicts.append(key)
        else:
            data['restore_observed'] = current
        data['restore_targets'] = targets
        data['conflicts'] = conflicts
        data['status'] = 'restoring'
        atomic_json(self.path, data)
        if conflicts:
            data['status'] = 'needs_review'
            atomic_json(self.path, data)
            raise RuntimeError('Restore paused before changes: ' + ', '.join(conflicts))
        if not targets:
            data['status'] = 'needs_review' if conflicts else 'restored'
            atomic_json(self.path, data)
            if conflicts:
                raise RuntimeError('Restore needs review: ' + ', '.join(conflicts))
            return
        # force-stop may remove our accessibility entry even when it predates this install.
        targets.setdefault(service_key, current[service_key])
        targets.setdefault('setting:secure:enabled_notification_listeners', current['setting:secure:enabled_notification_listeners'])
        targets.setdefault('guard', current['guard'])
        data['restore_targets'] = targets
        atomic_json(self.path, data)
        # Keep the app from rewriting the values while the snapshot is restored.
        self.adb.exchange('guard_hold')
        self.adb.shell('am', 'force-stop', '--user', '0', PACKAGE)
        try:
            for key, value in targets.items():
                if key != 'guard':
                    self.write(key, value)
            # Preserve a later user change in guard settings too.
            self.write('guard', targets.get('guard', current['guard']))
            verified = self.state()
            mismatches = [key for key, value in targets.items() if verified[key] != value]
            data['mismatches'] = mismatches
            data['status'] = 'restored' if not conflicts and not mismatches else 'needs_review'
            atomic_json(self.path, data)
            if conflicts or mismatches:
                raise RuntimeError('Restore needs review: ' + ', '.join(conflicts + mismatches))
        except Exception:
            if data['status'] == 'restoring':
                data['status'] = 'restore_failed'
                atomic_json(self.path, data)
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['snapshot', 'record', 'restore'])
    parser.add_argument('--serial', default=os.environ.get('ANDROID_SERIAL'))
    parser.add_argument('--adb', default='adb')
    parser.add_argument('--port', type=int, default=int(os.environ.get('ANDROID_ADB_SERVER_PORT', '5037')))
    parser.add_argument('--state-dir', type=Path, default=Path(__file__).resolve().parent.parent / 'local/clean-backups')
    args = parser.parse_args()
    if not args.serial:
        parser.error('--serial or ANDROID_SERIAL is required')
    snapshot = Snapshot(Adb(args.adb, args.serial, args.port), args.state_dir)
    with single_instance(snapshot.path.parent):
        {'snapshot': snapshot.capture, 'record': snapshot.record, 'restore': snapshot.restore}[args.command]()
    print('Installation snapshot:', args.command, 'finished')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Stopped:', error, file=sys.stderr)
        sys.exit(1)
