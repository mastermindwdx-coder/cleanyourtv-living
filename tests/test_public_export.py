from pathlib import Path
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from check_public import private_path, validate
from export_source import export

class PublicExportTests(unittest.TestCase):
    def test_second_smarttube_patch_is_also_checked(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)
            for rel in json.loads((ROOT/'public-files.json').read_text())['files']:
                p=target/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,p)
            with (target/'integrations/smarttube/playback-network-status.patch').open('a',encoding='utf-8') as stream:
                stream.write('\nGIT binary patch\n')
            result=validate(target)
            self.assertFalse(result['ok'])
            self.assertIn('SmartTube patch contains image replacement: playback-network-status.patch',result['errors'])
    def test_private_paths_are_never_exportable(self):
        for name in ['../private.yaml','/absolute/key','private/subscription.yaml','launcher/app/local/key.jks',
                     'companion/android/local.properties','key.p12','app.apk','.env','tools/adbkey/adbkey']:
            self.assertTrue(private_path(name),name)
    def test_repository_preflight_passes(self):
        self.assertTrue(validate()['ok'],validate()['errors'])
    def test_export_refuses_to_overwrite_previous_delivery(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'release.zip';target.write_bytes(b'keep')
            with self.assertRaises(FileExistsError):export(target)
            self.assertEqual(b'keep',target.read_bytes())
    def test_export_cannot_land_inside_repository(self):
        with self.assertRaises(ValueError):export(ROOT/'mistake.zip')
    def test_new_unreviewed_file_cannot_silently_enter_export(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)
            for rel in json.loads((ROOT/'public-files.json').read_text())['files']:
                p=target/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,p)
            (target/'accidental-config.yaml').write_text('sample: value')
            result=validate(target)
            self.assertFalse(result['ok'])
            self.assertIn('Unreviewed public file: accidental-config.yaml',result['errors'])
    def test_secret_in_reviewed_text_blocks_export_without_echoing_value(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)
            for rel in json.loads((ROOT/'public-files.json').read_text())['files']:
                p=target/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,p)
            fixture='-----BEGIN '+'PRIVATE KEY-----'+'\nFAKE-TEST-ONLY'
            with (target/'README.md').open('a',encoding='utf-8') as stream:stream.write(fixture)
            result=validate(target)
            self.assertFalse(result['ok'])
            self.assertIn('private-key: README.md',result['errors'])
            self.assertNotIn(fixture,json.dumps(result))

if __name__=='__main__':unittest.main()
