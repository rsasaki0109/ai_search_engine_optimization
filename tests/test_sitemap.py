import unittest
from unittest.mock import patch
import app
from sitemap import parse_sitemap


def parse(body): return parse_sitemap(body,'https://example.com/sitemap.xml',app.validate_url)


class SitemapTests(unittest.TestCase):
    def test_namespaced_page_list_ignores_image_locations(self):
        r=parse('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="https://example.com/image"><url><loc>https://example.com/a?x=1&amp;y=2</loc><image:image><image:loc>https://example.com/image.jpg</image:loc></image:image></url></urlset>')
        self.assertEqual(r['urls'],['https://example.com/a?x=1&y=2'])
        self.assertEqual(r['kind'],'pages')

    def test_index_is_returned_without_recursion(self):
        r=parse('<sitemapindex><sitemap><loc>https://example.com/posts.xml</loc></sitemap></sitemapindex>')
        self.assertEqual(r['kind'],'index')
        self.assertEqual(r['urls'],['https://example.com/posts.xml'])

    def test_deduplication_and_invalid_or_external_urls(self):
        r=parse('<urlset>'+''.join(f'<url><loc>{u}</loc></url>' for u in ['https://example.com/a#one','https://example.com/a#two','https://other.test/a','file:///etc/passwd','/relative'])+'</urlset>')
        self.assertEqual(r['urls'],['https://example.com/a'])
        self.assertEqual(r['skipped'],3)

    def test_candidate_limit(self):
        r=parse('<urlset>'+''.join(f'<url><loc>https://example.com/{n}</loc></url>' for n in range(101))+'</urlset>')
        self.assertEqual(len(r['urls']),100)
        self.assertTrue(r['truncated'])

    def test_invalid_xml_and_entities_are_rejected(self):
        for body in ['<urlset>', '<html/>', '<!DOCTYPE urlset [<!ENTITY x "text">]><urlset/>','<urlset xmlns="https://other.test"/>','x'*2_000_001]:
            with self.subTest(body=body[:40]),self.assertRaises(ValueError):parse(body)

    @patch('app.fetch')
    def test_fetch_status_and_final_source(self,fetch):
        fetch.return_value=dict(status=404)
        with self.assertRaises(ValueError):app.load_sitemap('https://example.com/sitemap.xml')
        fetch.return_value=dict(status=200,url='https://other.test/s.xml',body='<urlset><url><loc>https://other.test/a</loc></url></urlset>')
        self.assertEqual(app.load_sitemap('https://example.com/sitemap.xml')['urls'],['https://other.test/a'])

if __name__=='__main__':unittest.main()
