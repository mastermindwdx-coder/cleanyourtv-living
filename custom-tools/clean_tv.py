"""CleanYourTV Local companion. Authorized ADB only; one allowlisted system-package action.

The desktop journal is authoritative. Never infer a restore target from a TV UI receipt.
No package removal, stock-launcher modification, root, DNS or network listener.
"""
import argparse
import base64
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
import uuid

PACKAGE = 'com.gathin.tvhome'
SAVER = 'com.xiaomi.mitv.hyper.screensaver'
RESTORE_VERBS = {0: 'default-state', 1: 'enable', 2: 'disable', 3: 'disable-user', 4: 'disable-until-used'}


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    with temporary.open('w', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


@contextlib.contextmanager
def single_instance(folder):
    """OS lock is released on crashes; the persistent lock file is harmless."""
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / '.lock').open('a+b') as stream:
        if stream.tell() == 0:
            stream.write(b'0'); stream.flush()
        stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


class Adb:
    def __init__(self, executable, serial, port=5037):
        self.base = [str(executable), '-P', str(port), '-s', serial]
        self.serial = serial

    def run(self, *args, timeout=20):
        result = subprocess.run(self.base + list(args), capture_output=True, timeout=timeout)
        out = result.stdout.decode('utf-8', 'replace').strip()
        err = result.stderr.decode('utf-8', 'replace').strip()
        if result.returncode or re.search(r'(^|\n)(Error:|Exception|SecurityException|Failure \[)', out + '\n' + err):
            raise RuntimeError((out + '\n' + err).strip()[:1500])
        return out

    def shell(self, *args):
        # adb shell invokes a remote POSIX shell even on Windows. Quote each token there.
        return self.run('shell', shlex.join(str(x) for x in args))

    def identity(self):
        if self.run('get-state') != 'device':
            raise RuntimeError('ADB is offline or unauthorised')
        device = self.shell('getprop', 'ro.serialno')
        if not device:
            device = self.shell('settings', 'get', 'secure', 'android_id')
        if not device or device == 'null':
            raise RuntimeError('No stable device identity; refusing to save a restorable snapshot')
        return {'device': hashlib.sha256(device.encode()).hexdigest(),
                'model': self.shell('getprop', 'ro.product.model'),
                'firmware': self.shell('getprop', 'ro.build.display.id')}

    def package_state(self, target=SAVER):
        if target != SAVER:
            raise ValueError('Package outside the allowlist')
        dump = self.shell('dumpsys', 'package', target)
        match = re.search(r'^\s*User 0:.*\binstalled=true\b.*\benabled=(\d+)\b', dump, re.M)
        if not match:
            raise RuntimeError('Supported screensaver package not installed for user 0')
        state = int(match.group(1))
        if state not in RESTORE_VERBS:
            raise RuntimeError('Unknown package enable state')
        return state

    def set_package(self, value):
        self.shell('pm', RESTORE_VERBS[value], '--user', '0', SAVER)
        if self.package_state() != value:
            raise RuntimeError('Package state did not match the requested value')

    def exchange(self, command, data=None):
        encoded = base64.b64encode(json.dumps(data or {}, separators=(',', ':')).encode()).decode()
        out = self.shell('am', 'broadcast', '--user', '0', '-n', PACKAGE + '/.CleanReceiver',
                         '--es', 'command', command, '--es', 'payload', encoded)
        match = re.search(r'Broadcast completed: result=0, data="([A-Za-z0-9+/=]+)"', out)
        if not match:
            raise RuntimeError('CleanYourTV Local did not accept the shell request: ' + out[:500])
        return json.loads(base64.b64decode(match.group(1)))


class Cleaner:
    def __init__(self, adb, folder):
        self.adb, self.folder = adb, Path(folder)
        self.identity = adb.identity()
        self.path = self.folder / self.identity['device'][:20] / 'screensaver.json'

    def load(self):
        if not self.path.exists():
            return None
        journal = json.loads(self.path.read_text(encoding='utf-8'))
        if journal['identity'] != self.adb.identity():
            raise RuntimeError('Device or firmware changed; manual review required')
        if journal['target'] != SAVER or journal['before'] not in RESTORE_VERBS:
            raise RuntimeError('Invalid journal')
        return journal

    def save(self, journal):
        atomic_json(self.path, journal)

    def can_restore(self):
        journal = self.load()
        return bool(journal and journal['state'] in ('applying', 'applied', 'restoring', 'failed'))

    def apply(self, request_id):
        journal = self.load()
        current = self.adb.package_state()
        if journal and journal['state'] in ('applying', 'applied', 'restoring', 'failed'):
            if current == 3:
                journal['state'] = 'applied'; self.save(journal)
                return 'unchanged'
            if current != journal['before']:
                return 'conflict'
            # Reuse the original snapshot after an interrupted attempt.
        else:
            if current in (2, 3, 4):
                return 'unchanged'
            if journal:
                atomic_json(self.path.with_name('history-' + journal['id'] + '.json'), journal)
            journal = {'schema': 1, 'id': str(uuid.uuid4()), 'identity': self.identity,
                       'target': SAVER, 'before': current, 'after': 3, 'created': time.time(),
                       'request': request_id, 'state': 'prepared'}
        journal['state'] = 'applying'
        self.save(journal)  # Durable intent before any mutation, including crashes.
        try:
            self.adb.set_package(3)
            journal['state'] = 'applied'
            self.save(journal)
            return 'applied'
        except Exception:
            journal['state'] = 'failed'; self.save(journal)
            raise

    def restore(self):
        journal = self.load()
        if not journal or journal['state'] == 'restored':
            return 'unchanged'
        current = self.adb.package_state()
        if current == journal['before']:
            journal['state'] = 'restored'; self.save(journal)
            return 'restored'
        if current != journal['after']:
            return 'conflict'
        journal['state'] = 'restoring'; self.save(journal)
        self.adb.set_package(journal['before'])
        journal['state'] = 'restored'; self.save(journal)
        return 'restored'

    def receipt(self, result='ready', request_id=''):
        journal = self.load()
        return {'id': request_id, 'result': result, 'canRestore': self.can_restore(),
                'journal': journal['id'] if journal else ''}


def watch(adb, folder):
    cleaner = Cleaner(adb, folder)
    print('Connected. Use Advertising check in CleanYourTV Local. Ctrl+C stops the helper.', flush=True)
    with single_instance(cleaner.path.parent):
        while True:
            reply = adb.exchange('poll')
            request = reply.get('request')
            if not request:
                adb.exchange('receipt', cleaner.receipt())
            elif not request.get('claimed'):
                request_id = request['id']
                if request.get('action') not in ('disable_saver', 'restore'):
                    raise RuntimeError('Unknown requested action')
                if adb.exchange('claim', {'id': request_id}).get('claimed'):
                    try:
                        result = cleaner.apply(request_id) if request['action'] == 'disable_saver' else cleaner.restore()
                    except Exception as exc:
                        print('Action failed:', str(exc), flush=True)
                        result = 'failed'
                    adb.exchange('receipt', cleaner.receipt(result, request_id))
                    print(time.strftime('%H:%M:%S'), request['action'], result, flush=True)
            else:
                # A previous process claimed this request. Never replay it after a crash.
                adb.exchange('receipt', cleaner.receipt('failed', request['id']))
            time.sleep(3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['scan', 'watch', 'restore'])
    parser.add_argument('--adb', default='adb')
    parser.add_argument('--serial', required=True)
    parser.add_argument('--port', type=int, default=5037)
    parser.add_argument('--state-dir', type=Path, default=Path(__file__).resolve().parent / 'local' / 'clean-backups')
    args = parser.parse_args()
    adb = Adb(args.adb, args.serial, args.port)
    if args.command == 'watch':
        watch(adb, args.state_dir)
    else:
        cleaner = Cleaner(adb, args.state_dir)
        if args.command == 'scan':
            print(json.dumps({'device': cleaner.identity, 'screensaverState': adb.package_state(),
                              'canRestore': cleaner.can_restore()}, ensure_ascii=False, indent=2))
        else:
            with single_instance(cleaner.path.parent):
                print(cleaner.restore())


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Helper stopped.')
    except Exception as error:
        print('Stopped:', error, file=sys.stderr)
        sys.exit(1)
