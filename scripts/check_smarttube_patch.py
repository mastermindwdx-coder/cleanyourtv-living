"""Check the source-only patch and run its portable Java error formatter tests."""
from pathlib import Path
import os,re,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
patch=(ROOT/'integrations/smarttube/chinese-prompts.patch').read_text(encoding='utf-8')
assert 'GIT binary patch' not in patch
new={}
for section in re.split(r'(?=^diff --git )',patch,flags=re.M):
    if not section.strip():continue
    name=re.match(r'diff --git a/(.*?) b/',section)[1]
    assert Path(name).suffix in {'.java','.xml','.gradle'},name
    if '--- /dev/null' in section:
        new[name]='\n'.join(line[1:] for line in section.splitlines() if line.startswith('+') and not line.startswith('+++'))+'\n'
sources={name:body for name,body in new.items() if name.endswith(('ChinesePlaybackErrors.java','ChinesePlaybackErrorsTest.java'))}
assert len(sources)==2
java=Path(os.environ['JAVA_HOME'])/'bin' if os.environ.get('JAVA_HOME') else None
exe=lambda x:str(java/x) if java else x
with tempfile.TemporaryDirectory(prefix='cyt-errors-') as folder:
    files=[]
    for name,body in sources.items():
        p=Path(folder)/Path(name).name;p.write_text(body,encoding='utf-8');files.append(str(p))
    subprocess.run([exe('javac'),'-encoding','UTF-8','-d',folder,*files],check=True)
    subprocess.run([exe('java'),'-cp',folder,'ChinesePlaybackErrorsTest'],check=True)
print('Text-only SmartTube patch and portable formatter tests passed.')
