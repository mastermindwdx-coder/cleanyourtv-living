from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
results=[]
for project,budget in [('launcher',768*1024),('companion/android',256*1024)]:
    paths=list((ROOT/project/'app/build/outputs/apk/release').glob('*.apk'))
    if not paths:raise SystemExit('No release APK: '+project)
    for p in paths:
        size=p.stat().st_size
        results.append({'module':project,'file':p.name,'bytes':size,'budget':budget,'passed':size<=budget})
print(json.dumps(results,indent=2))
if not all(x['passed'] for x in results):raise SystemExit(1)
