"""Restore the paused Aerial configuration from the actual migration receipt; retain both APKs."""
import argparse, base64, json, re
from pathlib import Path
from clean_tv import Adb, atomic_json, single_instance
from clean_snapshot import Snapshot, settings_map

def aerial(adb, command, data=None):
    encoded=base64.b64encode(json.dumps(data or {},separators=(',',':')).encode()).decode()
    out=adb.shell('am','broadcast','--user','0','-n','app.orchard.tv/.clean.CleanReceiver',
                  '--es','command',command,'--es','payload',encoded)
    match=re.search(r'Broadcast completed: result=0, data="([A-Za-z0-9+/=]+)"',out)
    if not match:raise RuntimeError('Aerial did not accept the restoration request')
    return json.loads(base64.b64decode(match.group(1)))

def merge_aerial(before,current):
    parts=lambda x:[] if x in (None,'','null') else [p for p in x.split(':') if p]
    other=[p for p in parts(current) if not p.startswith('app.orchard.tv/')]
    mine=[p for p in parts(before) if p.startswith('app.orchard.tv/')]
    return ':'.join(other+mine)

def restore(adb,state_dir,pause_file):
    record=json.loads(pause_file.read_text(encoding='utf-8'))
    before=record['before']
    if before['identity']!=adb.identity():raise RuntimeError('Device/firmware does not match the pause receipt')
    snapshot=Snapshot(adb,state_dir)
    with single_instance(snapshot.path.parent):
        snapshot.restore()
    values=settings_map(adb.shell('settings','--user','0','list','secure'))
    for key in ['enabled_accessibility_services','enabled_notification_listeners']:
        restored=merge_aerial(before['secure'][key],values.get(key))
        if key=='enabled_notification_listeners':
            for component in restored.split(':'):
                if component.startswith('app.orchard.tv/'):
                    adb.shell('cmd','notification','allow_listener',component,'0')
        adb.shell('settings','--user','0','put','secure',key,restored)
    aerial(adb,'guard_restore',before['guard'])
    if before['secure']['accessibility_enabled'] is not None:
        adb.shell('settings','--user','0','put','secure','accessibility_enabled',before['secure']['accessibility_enabled'])
    adb.shell('am','start','-W','-n','app.orchard.tv/.MainActivity')
    if aerial(adb,'guard_state')!=before['guard']:raise RuntimeError('Aerial guard state did not restore exactly')
    record['status']='resumed_aerial';atomic_json(pause_file,record)
    print('Aerial resumed; CleanYourTV remains installed and paused. Confirm physical Home keys on TV.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--adb',default='adb');p.add_argument('--serial',required=True);p.add_argument('--port',type=int,default=5037)
    p.add_argument('--state-dir',type=Path,required=True);p.add_argument('--pause-file',type=Path,required=True)
    a=p.parse_args();restore(Adb(a.adb,a.serial,a.port),a.state_dir,a.pause_file)
