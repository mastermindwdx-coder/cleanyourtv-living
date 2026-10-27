"""Export only reviewed public files. Preserve existing output files."""
from pathlib import Path
import argparse, hashlib, json, zipfile
from check_public import ROOT, validate

def export(output, root=ROOT):
    result=validate(root)
    if not result['ok']:raise RuntimeError('Public preflight failed: '+'; '.join(result['errors']))
    output=Path(output).resolve()
    if output.is_relative_to(root.resolve()):raise ValueError('Place the ZIP outside the source repository')
    names=json.loads((root/'public-files.json').read_text(encoding='utf-8'))['files']
    records=[]
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for rel in names:
            data=(root/rel).read_bytes()
            item=zipfile.ZipInfo(rel,date_time=(2026,10,27,0,0,0))
            item.compress_type=zipfile.ZIP_DEFLATED
            item.external_attr=(0o755 if rel.endswith('.sh') or rel.endswith('/gradlew') else 0o644)<<16
            archive.writestr(item,data)
            records.append({'path':rel,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
        archive.writestr('SOURCE-MANIFEST.json',json.dumps({'schema':1,'files':records},ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(output) as archive:
        if archive.testzip():raise RuntimeError('ZIP CRC verification failed')
    return {'file':output.name,'files':len(records),'bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args()
    print(json.dumps(export(args.output),ensure_ascii=False,indent=2))
