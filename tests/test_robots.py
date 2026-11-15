import unittest
from robots import RobotsRules, normalize_path
import app


def decide(text,path,bot='OAI-SearchBot'):
    return RobotsRules(text).decision(bot,'https://example.com'+path)


class RobotsTests(unittest.TestCase):
    def test_longest_allow_overrides_broad_disallow_in_any_order(self):
        for rules in ['Disallow: /\nAllow: /public/', 'Allow: /public/\nDisallow: /']:
            result=decide('User-agent: *\n'+rules,'/public/page')
            self.assertTrue(result['allowed'])
            self.assertEqual(result['matched_rule'],'Allow: /public/')
            self.assertFalse(decide('User-agent: *\n'+rules,'/private')['allowed'])

    def test_specific_group_takes_precedence_over_wildcard(self):
        text='User-agent: *\nDisallow: /\n\nUser-agent: OAI-SearchBot\nAllow: /guide'
        self.assertTrue(decide(text,'/guide')['allowed'])
        # Wildcard rules are not inherited by a more specific group.
        result=decide(text,'/other')
        self.assertTrue(result['allowed'])
        self.assertEqual(result['group'],'OAI-SearchBot')
        self.assertFalse(decide(text,'/guide','GPTBot')['allowed'])

    def test_merges_multiple_groups_for_same_product_token(self):
        text='User-agent: OAI-SearchBot\nDisallow: /\n\nUser-agent: oai-searchbot\nAllow: /guide'
        self.assertTrue(decide(text,'/guide')['allowed'])
        self.assertFalse(decide(text,'/other')['allowed'])

    def test_allow_wins_equal_specificity(self):
        for rules in ['Disallow: /guide\nAllow: /guide','Allow: /guide\nDisallow: /guide']:
            self.assertTrue(decide('User-agent: *\n'+rules,'/guide')['allowed'])

    def test_wildcards_and_terminal_anchor(self):
        text='User-agent: *\nDisallow: /*.pdf$'
        self.assertFalse(decide(text,'/path/file.pdf')['allowed'])
        self.assertTrue(decide(text,'/path/file.pdf?download=1')['allowed'])
        self.assertTrue(decide(text,'/path/file.pdfx')['allowed'])
        text='User-agent: *\nDisallow: /*?*tracking='
        self.assertFalse(decide(text,'/guide?q=1&tracking=test')['allowed'])
        self.assertTrue(decide(text,'/guide?q=1')['allowed'])

    def test_matching_is_case_sensitive_but_agent_and_field_names_are_not(self):
        text='uSeR-aGeNt: oai-searchbot\ndIsAlLoW: /Private'
        self.assertFalse(decide(text,'/Private')['allowed'])
        self.assertTrue(decide(text,'/private')['allowed'])
        # Product tokens are exact: ChatGPT-User is not GPTBot.
        self.assertTrue(decide(text,'/Private','GPTBot')['allowed'])

    def test_comments_bom_and_line_evidence(self):
        result=decide('\ufeff#comment\nUser-agent: *\nDisallow: /guide # note','/guide')
        self.assertFalse(result['allowed'])
        self.assertEqual(result['matched_line'],3)
        self.assertEqual(result['matched_rule'],'Disallow: /guide')

    def test_multiple_agents_share_rules(self):
        text='User-agent: GPTBot\nUser-agent: OAI-SearchBot\nDisallow: /guide'
        self.assertFalse(decide(text,'/guide')['allowed'])
        self.assertFalse(decide(text,'/guide','GPTBot')['allowed'])
        self.assertTrue(decide(text,'/guide','Googlebot')['allowed'])

    def test_empty_and_unknown_records_do_not_block(self):
        text='User-agent: *\nDisallow:\nAllow:\nCrawl-delay: 10\nSitemap: https://example.com/sitemap.xml'
        self.assertTrue(decide(text,'/')['allowed'])
        self.assertIsNone(decide(text,'/')['matched_rule'])
        self.assertTrue(decide('','/')['allowed'])
        # Sitemap must not terminate a group.
        text='User-agent: *\nDisallow: /\nSitemap: https://example.com/sitemap.xml\nAllow: /guide'
        self.assertTrue(decide(text,'/guide')['allowed'])

    def test_unicode_and_unreserved_percent_encoding(self):
        for rule,path in [('/日本語','/%E6%97%A5%E6%9C%AC%E8%AA%9E'),
                          ('/%E6%97%A5%E6%9C%AC%E8%AA%9E','/日本語'),('/g%75ide','/guide'),('/guide','/%67uide')]:
            with self.subTest(rule=rule,path=path):
                self.assertFalse(decide('User-agent: *\nDisallow: '+rule,path)['allowed'])
        self.assertEqual(normalize_path('/foo%2fbar'),'/foo%2Fbar')
        self.assertTrue(decide('User-agent: *\nDisallow: /foo%2Fbar','/foo/bar')['allowed'])

    def test_wildcard_characters_other_than_star_are_literal(self):
        text='User-agent: *\nDisallow: /[ab]'
        self.assertTrue(decide(text,'/a')['allowed'])
        self.assertFalse(decide(text,'/[ab]')['allowed'])

    def test_adversarial_star_patterns_are_not_backtracking_regexes(self):
        pattern='/'+'a*'*900+'z$'
        self.assertTrue(decide('User-agent: *\nDisallow: '+pattern,'/'+'a'*1000)['allowed'])

    def test_oversized_robots_is_unknown_without_failing_page_audit(self):
        with self.assertRaises(ValueError): RobotsRules('#'*512001)
        result=app.analyze(dict(url='https://example.com',body='<title>Sample</title>',robots_header=''),'#'*512001)
        self.assertEqual(result['bots'],[])
        self.assertIn('解析上限',result['robots_error'])

if __name__=='__main__':unittest.main()
