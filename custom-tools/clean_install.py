"""Install the local CleanYourTV build and configure the explicitly tested Xiaomi profile."""
import argparse
from pathlib import Path
import sys
from clean_tv import Adb, PACKAGE, single_instance
from clean_snapshot import Snapshot, settings_map

def install(adb, apk):
    if not apk or not apk.is_file(): raise RuntimeError('APK file is required')
    result = adb.run('install', '-r', str(apk.resolve()), timeout=180)
    if 'Success' not in result: raise RuntimeError('Installation did not report success: ' + result)
    adb.run('shell', 'cmd package compile -m speed -f ' + PACKAGE, timeout=120)
    adb.shell('am', 'start', '-W', '-n', PACKAGE + '/.MainActivity')
    print('Installed and compiled; Home takeover is a separate setup step.')

def setup_home(adb, folder, keep_adb=False):
    identity = adb.identity()
    if identity['model'] != 'MiTV-MFTR0' or identity['firmware'] != 'OS3.0.101.0.UFTMATV':
        raise RuntimeError('This profile is limited to MiTV-MFTR0 / OS3.0.101.0.UFTMATV')
    snapshot = Snapshot(adb, folder)
    with single_instance(snapshot.path.parent):
        snapshot.capture()
        values = settings_map(adb.shell('settings', '--user', '0', 'list', 'secure'))
        if any('app.orchard.tv/' in (values.get(k) or '') for k in ('enabled_accessibility_services','enabled_notification_listeners')):
            raise RuntimeError('Pause the previous Aerial guard before enabling another Home guard.')
        try:
            adb.shell('pm', 'grant', '--user', '0', PACKAGE, 'android.permission.WRITE_SECURE_SETTINGS')
            for op in ('SYSTEM_ALERT_WINDOW','GET_USAGE_STATS'):
                adb.shell('appops','set','--user','0',PACKAGE,op,'allow')
            state = adb.exchange('guard_state')
            state.update(enabled=True, clean_restore_hold=None)
            # Public default never re-enables debugging after the owner closes it.
            state['keep_adb'] = bool(keep_adb)
            adb.exchange('guard_restore',state)
            adb.shell('cmd','notification','allow_listener',PACKAGE+'/.GuardRevival')
            values = settings_map(adb.shell('settings','--user','0','list','secure'))
            services = [x for x in (values.get('enabled_accessibility_services') or '').split(':') if x and x != 'null']
            if not any(x in services for x in (PACKAGE+'/.HomeKeyService', PACKAGE+'/'+PACKAGE+'.HomeKeyService')):
                services.append(PACKAGE+'/.HomeKeyService')
            adb.shell('settings','--user','0','put','secure','enabled_accessibility_services',':'.join(services))
            adb.shell('settings','--user','0','put','secure','accessibility_enabled','1')
            adb.shell('am','start','-W','-n',PACKAGE+'/.MainActivity')
        finally:
            snapshot.record()
    print('Home guard configured; physical keys and standby need device validation.')

def end_maintenance(adb):
    # Stop the observer from reopening ADB before asking the owner to close debugging.
    state = adb.exchange('guard_state')
    state['keep_adb'] = False
    adb.exchange('guard_restore', state)
    if adb.exchange('guard_state').get('keep_adb') is not False:
        raise RuntimeError('Maintenance preference did not settle; do not claim ADB is closed.')
    print('Keep-ADB is off. Close debugging on the TV, then verify with tools/adb-closed.py.')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['install','setup-home','restore-home','end-maintenance'])
    p.add_argument('--adb',default='adb');p.add_argument('--serial',required=True)
    p.add_argument('--port',type=int,default=5037);p.add_argument('--apk',type=Path)
    p.add_argument('--state-dir',type=Path,default=Path(__file__).resolve().parent/'local/backups')
    p.add_argument('--keep-adb',action='store_true',help='Explicit maintenance opt-in for setup-home only; keeps debugging enabled until end-maintenance.')
    a=p.parse_args();adb=Adb(a.adb,a.serial,a.port);adb.identity()
    if a.keep_adb and a.command != 'setup-home': p.error('--keep-adb is only valid with setup-home')
    if a.command=='install':install(adb,a.apk)
    elif a.command=='setup-home':setup_home(adb,a.state_dir,a.keep_adb)
    elif a.command=='end-maintenance':end_maintenance(adb)
    else:
        snapshot=Snapshot(adb,a.state_dir)
        with single_instance(snapshot.path.parent):snapshot.restore()

if __name__=='__main__':
    try:main()
    except Exception as e:print('Stopped:',e,file=sys.stderr);sys.exit(1)
