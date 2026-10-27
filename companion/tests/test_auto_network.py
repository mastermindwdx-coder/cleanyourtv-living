import copy,json,subprocess,sys,tempfile,unittest,yaml
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_network import adapt,SELECT,AUTO,FALLBACK

class AutoNetworkTests(unittest.TestCase):
    def profile(self):
        return {'external-controller':'0.0.0.0:9090','external-controller-cors':{},'secret':'synthetic-secret',
                'interface-name':'example-adapter','tun':{'enable':True},'mode':'global',
                'proxies':[{'name':'node-a','type':'vless','reality-opts':{'short-id':'1234e56789'}},{'name':'node-b','type':'vless'},{'name':'node-c','type':'vless'}],
                'proxy-groups':[{'name':'old-group','type':'select','proxies':['node-a']}],
                'rules':['DOMAIN-SUFFIX,example.org,DIRECT','DOMAIN-SUFFIX,youtube.com,old-group','IP-CIDR,10.0.0.0/8,old-group,no-resolve','MATCH,old-group']}
    def selection(self):return {'preferred':['node-a','node-b'],'fallback':['node-a','node-b','node-c']}
    def convert(self,d=None,selection=None):
        return yaml.safe_load(adapt(yaml.safe_dump(d or self.profile()),'192.168.10.0/24',selection or self.selection()))
    def test_local_safety_and_real_string_id(self):
        raw=yaml.safe_dump(self.profile());before=raw
        result=adapt(raw,'192.168.10.0/24',self.selection());d=yaml.safe_load(result)
        self.assertEqual(before,raw)
        for k in ['external-controller','external-controller-cors','secret','interface-name','tun']:self.assertNotIn(k,d)
        self.assertFalse(d['allow-lan']);self.assertEqual(d['bind-address'],'127.0.0.1')
        self.assertIn('short-id: "1234e56789"',result)
    def test_rules_keep_direct_and_retarget_old_groups(self):
        d=self.convert()
        self.assertEqual(d['rules'][0],'IP-CIDR,192.168.10.0/24,DIRECT,no-resolve')
        self.assertIn('DOMAIN-SUFFIX,example.org,DIRECT',d['rules'])
        self.assertIn('IP-CIDR,10.0.0.0/8,'+SELECT+',no-resolve',d['rules'])
        self.assertEqual(d['rules'][-1],'MATCH,'+SELECT)
    def test_measured_pool_and_separate_fallback(self):
        groups={g['name']:g for g in self.convert()['proxy-groups']}
        self.assertEqual(groups[SELECT]['proxies'][0],AUTO)
        self.assertEqual(groups[AUTO]['proxies'],['node-a','node-b'])
        self.assertEqual(groups[AUTO]['interval'],120);self.assertEqual(groups[AUTO]['tolerance'],150)
        self.assertEqual(groups[FALLBACK]['interval'],60)
        self.assertFalse(groups[AUTO]['lazy'])
    def test_bad_candidates_rejected_without_output(self):
        for selection in [{'preferred':[]},{'preferred':['unknown']},{'preferred':['node-a','node-a']},{'preferred':['node-a'],'fallback':['node-b']},{'preferred':'node-a'}]:
            with self.subTest(selection=selection),self.assertRaises(ValueError):self.convert(selection=selection)
    def test_unsupported_dynamic_or_chained_profile_rejected(self):
        for key,value in [('proxy-providers',{'example':{}}),('sub-rules',{'example':[]})]:
            d=self.profile();d[key]=value
            with self.assertRaises(ValueError):self.convert(d)
        d=self.profile();d['proxies'][0]['dialer-proxy']='old-group'
        with self.assertRaises(ValueError):self.convert(d)
    def test_group_name_collision_rejected(self):
        d=self.profile();d['proxies'][0]['name']=AUTO
        with self.assertRaises(ValueError):self.convert(d)
    def test_cli_preserves_source_and_existing_output(self):
        script=Path(__file__).resolve().parents[1]/'scripts/prepare_network.py'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'input.yaml';dest=root/'output.yaml';selection=root/'selection.json'
            original=yaml.safe_dump(self.profile());source.write_text(original,encoding='utf-8')
            selection.write_text(json.dumps(self.selection()),encoding='utf-8')
            args=[sys.executable,str(script),'--input',str(source),'--output',str(dest),'--lan','192.168.10.0/24','--selection-file',str(selection)]
            first=subprocess.run(args,capture_output=True,text=True);self.assertEqual(first.returncode,0,first.stderr)
            self.assertEqual(source.read_text(encoding='utf-8'),original)
            saved=dest.read_bytes();second=subprocess.run(args,capture_output=True,text=True)
            self.assertNotEqual(second.returncode,0);self.assertEqual(dest.read_bytes(),saved)
            self.assertNotIn('node-a',first.stdout)

if __name__=='__main__':unittest.main()
