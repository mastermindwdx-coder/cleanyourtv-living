"""Make a private snapshot; never print credentials or overwrite source/output."""
import argparse,hashlib,ipaddress,json
from pathlib import Path
import yaml

class Quoted(str):pass
class Dumper(yaml.SafeDumper):pass
Dumper.add_representer(Quoted,lambda d,v:d.represent_scalar('tag:yaml.org,2002:str',v,style='"'))

SELECT='电视网络'
AUTO='电视自动优选'
FALLBACK='电视故障回退'
HEALTH_URL='https://www.youtube.com/generate_204'

def add_auto_groups(data,selection):
    """Use caller-measured candidates, not an unverified 'fastest node' claim."""
    if not isinstance(selection,dict):raise ValueError('Selection must be a mapping')
    if data.get('proxy-providers') or data.get('sub-rules'):
        raise ValueError('Auto selection requires a flattened static profile without providers/sub-rules')
    nodes=data.get('proxies',[])
    names=[p['name'] for p in nodes]
    if not names or len(set(names))!=len(names):raise ValueError('Proxy names must be nonempty and unique')
    if set(names)&{SELECT,AUTO,FALLBACK}:raise ValueError('Reserved TV group name collision')
    old_groups={g['name'] for g in data.get('proxy-groups',[])}
    if any(p.get('dialer-proxy') in old_groups for p in nodes):
        raise ValueError('Review chained proxies before replacing their policy groups')
    preferred=selection.get('preferred')
    fallback=selection.get('fallback',preferred)
    for candidates in [preferred,fallback]:
        if not isinstance(candidates,list) or not candidates or not all(isinstance(x,str) for x in candidates):
            raise ValueError('Candidate lists must contain existing proxy names')
        if len(set(candidates))!=len(candidates) or not set(candidates).issubset(names):
            raise ValueError('Candidate lists must be unique and refer to existing proxies')
    if not set(preferred).issubset(fallback):raise ValueError('Fallback must include all preferred candidates')
    data['proxy-groups']=[
        {'name':SELECT,'type':'select','proxies':[AUTO,FALLBACK]+names},
        {'name':AUTO,'type':'url-test','proxies':preferred,'url':HEALTH_URL,'interval':120,'tolerance':150,'timeout':6000,'lazy':False},
        {'name':FALLBACK,'type':'fallback','proxies':fallback,'url':HEALTH_URL,'interval':60,'timeout':6000,'lazy':False},
    ]
    rules=[]
    for rule in data.get('rules',[]):
        parts=rule.split(',');target=-2 if parts[-1]=='no-resolve' else -1
        if parts[target] in old_groups or parts[target] in names:parts[target]=SELECT
        rewritten=','.join(parts)
        if rewritten not in rules:rules.append(rewritten)
    if not any(r.startswith('MATCH,') for r in rules):rules.append('MATCH,'+SELECT)
    data['rules']=rules

def adapt(raw,lan,selection=None):
    network=str(ipaddress.ip_network(lan,strict=False))
    if not ipaddress.ip_network(network).is_private:raise ValueError('LAN must be a private network')
    data=yaml.safe_load(raw)
    if not isinstance(data,dict):raise ValueError('Expected a Mihomo configuration mapping')
    for key in list(data):
        if key.startswith('external-') or key in {'secret','tun','listeners','profile','log-file','interface-name','routing-mark','authentication'}:
            data.pop(key,None)
    data.update({'allow-lan':False,'bind-address':'127.0.0.1','log-level':'warning','mode':'rule'})
    if selection is not None:add_auto_groups(data,selection)
    data['rules']=[f'IP-CIDR,{network},DIRECT,no-resolve','IP-CIDR,127.0.0.0/8,DIRECT,no-resolve']+data.get('rules',[])
    for proxy in data.get('proxies',[]):
        if 'reality-opts' in proxy:
            opts=proxy['reality-opts']
            if 'short-id' in opts:
                if not isinstance(opts['short-id'],str):raise ValueError('Input short-id must be quoted as a string; numeric parsing may have lost its exact value')
                opts['short-id']=Quoted(opts['short-id'])
    for category in ['proxy-providers','rule-providers']:
        for name,provider in data.get(category,{}).items():
            if provider.get('path'):provider['path']=f'./{category}/'+hashlib.sha256(name.encode()).hexdigest()[:12]+'.yaml'
    return yaml.dump(data,Dumper=Dumper,allow_unicode=True,sort_keys=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);p.add_argument('--lan',required=True)
    p.add_argument('--selection-file',help='Private JSON with measured preferred/fallback node names; optional')
    a=p.parse_args()
    source=Path(a.input).resolve();dest=Path(a.output).resolve()
    if source==dest or dest.exists():raise ValueError('Use a new output file; existing files are preserved')
    selection_path=Path(a.selection_file).resolve() if a.selection_file else None
    if selection_path==dest:raise ValueError('Output must not overwrite the private selection file')
    selection=json.loads(selection_path.read_text(encoding='utf-8')) if selection_path else None
    result=adapt(source.read_bytes(),a.lan,selection);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(result,encoding='utf-8')
    print('Private TV configuration prepared. Import it locally; do not publish it.')
if __name__=='__main__':main()
