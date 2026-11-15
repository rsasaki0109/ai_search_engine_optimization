import json
import unittest
import app


def inspect(value, raw=False):
    parser=app.Page()
    parser.feed('<script type="application/ld+json">'+(value if raw else json.dumps(value))+'</script>')
    return app.inspect_schemas(parser)[0]


class SchemaTests(unittest.TestCase):
    def test_graph_inherits_context_and_collects_nested_types(self):
        result=inspect({'@context':'https://schema.org','@graph':[
            {'@type':['Article','CreativeWork'],'author':{'@type':'Person','name':'Alice'}},
            {'@type':'Organization','name':'Example'}]})
        self.assertTrue(result['passed'])
        self.assertEqual(result['types'],['Article','CreativeWork','Organization','Person'])

    def test_object_arrays_and_prefix_contexts(self):
        for context, typename in [({'@vocab':'https://schema.org/'},'Article'),
                                  ({'schema':'https://schema.org/'},'schema:Article'),
                                  ({'schema':{'@id':'https://schema.org/','@prefix':True}},'schema:Article'),
                                  (['https://schema.org',{'name':'https://schema.org/name'}],'Article')]:
            with self.subTest(context=context):
                self.assertTrue(inspect([{'@context':context,'@type':typename}])['passed'])

    def test_absolute_schema_type_needs_no_context(self):
        self.assertTrue(inspect({'@type':'https://schema.org/WebPage'})['passed'])

    def test_missing_context_or_type_and_non_schema_context(self):
        for value in [{'@type':'Article'},{'@context':'https://schema.org','name':'Example'},
                      {'@context':'https://other.test/context','@type':'Article'},{}]:
            with self.subTest(value=value): self.assertFalse(inspect(value)['passed'])

    def test_invalid_json_scalars_and_nonstandard_constants(self):
        for raw in ['{broken','null','42','[]','"text"','{"@type":NaN}']:
            with self.subTest(raw=raw):
                result=inspect(raw,raw=True)
                self.assertFalse(result['passed'])
                self.assertTrue(result['issues'])

    def test_invalid_type_shapes(self):
        for value in [None,[],['Article',3],{},'',False]:
            with self.subTest(value=value):
                result=inspect({'@context':'https://schema.org','@type':value})
                self.assertFalse(result['passed'])
                self.assertTrue(result['issues'])

    def test_invalid_or_unresolved_context_is_not_hidden_by_absolute_type(self):
        for value in [42, True, 'https://other.test/context']:
            with self.subTest(value=value):
                result=inspect({'@context':value,'@type':'https://schema.org/Article'})
                self.assertFalse(result['passed'])
                self.assertIn('@context',' '.join(result['issues']))

    def test_explicitly_disabled_prefix_is_not_expanded(self):
        result=inspect({'@context':{'schema':{'@id':'https://schema.org/','@prefix':False}},'@type':'schema:Article'})
        self.assertFalse(result['passed'])

    def test_invalid_graph_is_reported_even_with_valid_parent_type(self):
        result=inspect({'@context':'https://schema.org','@type':'WebPage','@graph':'broken'})
        self.assertFalse(result['passed'])
        self.assertIn('@graph', ' '.join(result['issues']))

    def test_local_context_reset_does_not_inherit_schema(self):
        result=inspect({'@context':'https://schema.org','@type':'Article',
                        'author':{'@context':None,'@type':'Person'}})
        self.assertFalse(result['passed'])
        self.assertEqual(result['types'],['Article'])

    def test_mixed_blocks_do_not_hide_broken_json(self):
        page=app.analyze(dict(url='https://example.com',robots_header='',body=
            '<script type="application/ld+json">{"@context":"https://schema.org","@type":"Article"}</script>'
            '<script type="application/ld+json">broken</script>'))
        self.assertFalse(next(c for c in page['checks'] if c['id']=='schema')['passed'])
        self.assertTrue(page['schema_details'][0]['passed'])
        self.assertFalse(page['schema_details'][1]['passed'])
        self.assertEqual(page['analysis_version'],'2')

    def test_bounded_inspection(self):
        result=inspect({'@context':'https://schema.org','@graph':[{'@type':'Article'}]*2100})
        self.assertFalse(result['passed'])
        self.assertIn('解析上限',' '.join(result['issues']))
        nested='https://schema.org'
        for _ in range(65): nested=[nested]
        result=inspect({'@context':nested,'@type':'Article'})
        self.assertFalse(result['passed'])
        self.assertIn('解析上限',' '.join(result['issues']))

    def test_too_deep_json_is_reported_without_crashing(self):
        result=inspect('['*1200+'{}'+']'*1200,raw=True)
        self.assertFalse(result['passed'])

if __name__=='__main__': unittest.main()
