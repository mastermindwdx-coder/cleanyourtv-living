"""Check both source-only patches and run their portable Java tests."""
from pathlib import Path
import os,re,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
new={}
for filename in ['chinese-prompts.patch','playback-network-status.patch']:
    patch=(ROOT/'integrations/smarttube'/filename).read_text(encoding='utf-8')
    assert 'GIT binary patch' not in patch
    for section in re.split(r'(?=^diff --git )',patch,flags=re.M):
        if not section.strip():continue
        name=re.match(r'diff --git a/(.*?) b/',section)[1]
        assert Path(name).suffix in {'.java','.xml','.gradle'},name
        assert '..' not in Path(name).parts and not name.startswith('/'),name
        if '--- /dev/null' in section:
            new[name]='\n'.join(line[1:] for line in section.splitlines() if line.startswith('+') and not line.startswith('+++'))+'\n'
sources={name:body for name,body in new.items() if Path(name).name in {'ChinesePlaybackErrors.java','ChinesePlaybackErrorsTest.java','DownloadRate.java','DownloadRateTest.java'}}
assert len(sources)==4
java=Path(os.environ['JAVA_HOME'])/'bin' if os.environ.get('JAVA_HOME') else None
exe=lambda x:str(java/x) if java else x
with tempfile.TemporaryDirectory(prefix='cyt-errors-') as folder:
    files=[]
    for name,body in sources.items():
        p=Path(folder)/Path(name).name;p.write_text(body,encoding='utf-8');files.append(str(p))
    subprocess.run([exe('javac'),'-encoding','UTF-8','-d',folder,*files],check=True)
    subprocess.run([exe('java'),'-cp',folder,'ChinesePlaybackErrorsTest'],check=True)
    subprocess.run([exe('java'),'-cp',folder,'DownloadRateTest'],check=True)
print('Both text-only SmartTube patches and portable tests passed.')
