import importlib.util
from pathlib import Path
import unittest
import app
from tools.build_pages import build

class PagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build()
        cls.out=Path(app.ROOT)/'dist-pages'
        spec=importlib.util.spec_from_file_location('pages_analysis',cls.out/'analysis.py')
        cls.analysis=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.analysis)

    def test_analyzer_parity_and_no_network_code(self):
        for stage in ['before','after']:
            page=dict(body=(self.out/'demo'/f'{stage}.html').read_text(),url='https://demo.example/guide',robots_header='')
            self.assertEqual(self.analysis.analyze(page,'User-agent: *\nAllow: /'), app.analyze(page,'User-agent: *\nAllow: /'))
        self.assertFalse((self.out/'app.py').exists())
        self.assertNotIn('import socket',(self.out/'analysis.py').read_text())

    def test_project_subpath_assets(self):
        html=(self.out/'index.html').read_text()
        self.assertNotIn('src="/',html)
        self.assertNotIn('href="/',html)
        self.assertTrue((self.out/'.nojekyll').exists())
        self.assertIn('pages-form',html)

if __name__=='__main__':unittest.main()
