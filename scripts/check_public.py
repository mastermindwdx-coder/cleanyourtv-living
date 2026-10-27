"""Validate the exact public source selection; never print matched secret values."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {'.git', '.gradle', 'build', 'private', 'local', 'backup', 'backups',
           'shots', 'work', 'dist', 'venv', '.venv', '__pycache__', 'adbkey'}
LOCAL_FILES = {'local.properties', 'keystore.properties', 'gradle.properties.local'}
BLOCKED_SUFFIXES = {'.apk', '.aab', '.jks', '.keystore', '.p12', '.pem', '.key', '.log', '.pyc', '.mp4'}
TEXT_SUFFIXES = {'.md','.py','.java','.xml','.json','.yml','.yaml','.properties','.gradle','.sh','.ps1','.bat','.txt','.svg','.patch','.html'}

def private_path(name):
    p=PurePosixPath(name)
    return (p.is_absolute() or '..' in p.parts or bool(set(p.parts)&IGNORED)
            or p.name in LOCAL_FILES or p.suffix.lower() in BLOCKED_SUFFIXES
            or p.name.startswith('.env') or ':' in name)

def candidates(root):
    # Do not inspect unrelated private/build contents, including material added after a release.
    import os
    for folder, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORED]
        for name in files:
            rel=(Path(folder)/name).relative_to(root).as_posix()
            if name in LOCAL_FILES or name.endswith(('.pyc','.log')):continue
            yield rel

def validate(root=ROOT):
    errors=[]
    manifest=json.loads((root/'public-files.json').read_text(encoding='utf-8'))
    names=manifest['files']
    if names != sorted(set(names)):errors.append('public-files.json: paths must be unique and sorted')
    extra=set(candidates(root))-set(names)-{'SOURCE-MANIFEST.json'}
    errors.extend('Unreviewed public file: '+x for x in sorted(extra))
    binaries=json.loads((root/'docs/public-binaries.json').read_text(encoding='utf-8'))['files']
    binary_by_path={x['path']:x['sha256'] for x in binaries}
    patterns=[
        ('private-key',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE' + r' KEY-----'),
        ('github-token',r'\bgh[pousr]_[A-Za-z0-9]{30,}\b'),
        ('local-workspace',r'[CD]:[\\/]'+r'(?:Creator' + r'_OS|CodexData|Users[\\/]Admin)[\\/]'),
        ('personal-tv-address',r'192\.168\.' + r'3\.(?:6|8)(?![0-9])'),
        ('proxy-uri',r'\b(?:vmess|vless|trojan|ss)://[A-Za-z0-9+/_=-]{20,}'),
    ]
    for rel in names:
        if private_path(rel):errors.append('Private or unsafe path: '+rel);continue
        p=root/rel
        if not p.is_file() or p.is_symlink():errors.append('Missing or symlink: '+rel);continue
        raw=p.read_bytes()
        if rel in binary_by_path:
            if hashlib.sha256(raw).hexdigest()!=binary_by_path[rel]:errors.append('Unreviewed binary hash: '+rel)
            continue
        try: text=raw.decode('utf-8-sig')
        except UnicodeError:errors.append('Binary missing provenance: '+rel);continue
        for rule,pattern in patterns:
            if re.search(pattern,text): errors.append(rule+': '+rel)
        if p.suffix=='.json':
            try:json.loads(text)
            except ValueError:errors.append('Invalid JSON: '+rel)
        if p.suffix=='.md':
            for target in re.findall(r'\]\(([^)]+)\)',text):
                target=target.split(' ')[0].split('#')[0]
                if not target or re.match(r'^[a-zA-Z]+:',target):continue
                if not (p.parent/target).exists():errors.append('Broken local link: '+rel+' -> '+target)
    launcher=ET.parse(root/'launcher/app/src/main/AndroidManifest.xml')
    ns='{http://schemas.android.com/apk/res/android}'
    if any(p.get(ns+'name')=='android.permission.INTERNET' for p in launcher.findall('uses-permission')):
        errors.append('Launcher unexpectedly requests INTERNET')
    patch=(root/'integrations/smarttube/chinese-prompts.patch').read_text(encoding='utf-8')
    if 'GIT binary patch' in patch or re.search(r'^diff --git .*\.(png|webp|jpg)',patch,re.M):
        errors.append('SmartTube patch contains image replacement')
    for p in (root/'.github/workflows').glob('*'):
        text=p.read_text(encoding='utf-8')
        if 'pull_request_target' in text or 'contents: write' in text:errors.append('Unexpected publishing workflow authority: '+p.name)
    return {'ok':not errors,'files':len(names),'reviewed_binaries':len(binaries),'errors':errors,
            'scope':'Exact allowlisted working tree; Git history and remote services are outside this check.'}

if __name__=='__main__':
    result=validate();print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(0 if result['ok'] else 1)
