import sys,unittest,yaml
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_network import adapt
class NetworkTests(unittest.TestCase):
 def test_private_snapshot_preserves_node_string_and_rules(self):
  raw='external-controller: 127.0.0.1:9090\nsecret: synthetic-secret\nmode: global\nproxies:\n- name: sample\n  type: vless\n  reality-opts:\n    short-id: "1234e56789"\nrules:\n- MATCH,sample\n'
  out=adapt(raw,'192.168.10.0/24');d=yaml.safe_load(out)
  self.assertNotIn('secret',d);self.assertNotIn('external-controller',d);self.assertEqual(d['mode'],'rule')
  self.assertIn('short-id: "1234e56789"',out);self.assertEqual(d['rules'][-1],'MATCH,sample')
 def test_non_private_network_rejected(self):
  with self.assertRaises(ValueError):adapt('proxies: []','8.8.8.0/24')
 def test_numeric_short_id_rejected_instead_of_silently_corrupted(self):
  with self.assertRaises(ValueError):adapt('proxies: [{reality-opts: {short-id: 123456}}]','192.168.1.0/24')
