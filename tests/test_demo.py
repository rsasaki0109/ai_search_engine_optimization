import unittest
from unittest.mock import patch
import app

class DemoTests(unittest.TestCase):
    @patch('app.fetch',side_effect=AssertionError('demo must not fetch externally'))
    def test_before_after_use_real_analysis_without_network(self,fetch):
        demo=app.demo_audits()
        self.assertEqual(demo['before']['score'],30)
        self.assertEqual(demo['after']['score'],100)
        improved=[c['id'] for c in demo['after']['checks'] if c['passed'] and not next(b for b in demo['before']['checks'] if b['id']==c['id'])['passed']]
        self.assertEqual(set(improved),{'description','h1','headings','content','schema','canonical'})
        for stage,report in demo.items():
            self.assertTrue(report['is_demo'])
            self.assertEqual(report['demo_stage'],stage)
            self.assertIn('検証用サンプル',report['note'])
        fetch.assert_not_called()

if __name__=='__main__':unittest.main()
