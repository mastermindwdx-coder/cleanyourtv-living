"""Make a private snapshot; never print credentials or overwrite source/output."""
import argparse,hashlib,ipaddress,json
from pathlib import Path
import yaml

class Quoted(str):pass
class Dumper(yaml.SafeDumper):pass
Dumper.add_representer(Quoted,lambda d,v:d.represent_scalar('tag:yaml.org,2002:str',v,style='"'))

def adapt(raw,lan):
    network=str(ipaddress.ip_network(lan,strict=False))
    if not ipaddress.ip_network(network).is_private:raise ValueError('LAN must be a private network')
    data=yaml.safe_load(raw)
    if not isinstance(data,dict):raise ValueError('Expected a Mihomo configuration mapping')
    for key in ['external-controller','external-controller-pipe','external-controller-unix','external-controller-tls','external-ui','external-ui-url','secret','tun','listeners','profile','log-file']:
        data.pop(key,None)
    data.update({'allow-lan':False,'bind-address':'127.0.0.1','log-level':'warning','mode':'rule'})
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
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);p.add_argument('--lan',required=True);a=p.parse_args()
    source=Path(a.input).resolve();dest=Path(a.output).resolve()
    if source==dest or dest.exists():raise ValueError('Use a new output file; existing files are preserved')
    result=adapt(source.read_bytes(),a.lan);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(result,encoding='utf-8')
    print('Private TV configuration prepared. Import it locally; do not publish it.')
if __name__=='__main__':main()
