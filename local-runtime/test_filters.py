"""Filter behavior at validation, model and actual HTTP session boundaries."""
import contextlib
import http.cookiejar
import importlib.util
import json
from pathlib import Path
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('filter_runtime', Path(__file__).with_name('server.py'))
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


@contextlib.contextmanager
def session():
    server = runtime.ThreadingHTTPServer(('127.0.0.1', 0), runtime.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def post(action, **data):
        request = urllib.request.Request(base+'/api/action',
            data=json.dumps(dict(action=action, **data)).encode(),
            headers={'Origin':base, 'Content-Type':'application/json'})
        with opener.open(request) as response:
            return response.read().decode()
    try:
        yield post
    finally:
        server.shutdown()
        server.server_close()


def presets(page):
    return json.loads(page.split('<script id="runtime-filters" type="application/json">')[1].split('</script>')[0])


class FilterTests(unittest.TestCase):
    def test_validation_is_atomic_and_names_are_unique(self):
        state = runtime.new_state()
        runtime.save_filter(state, dict(name=' Research ', criteria=' Original papers '))
        before = json.dumps(state)
        for data in [dict(name='research',criteria='duplicate'), dict(name='',criteria='x'),
                     dict(name='x',criteria='x'*2001),dict(name='x',criteria='x',filter_id='missing')]:
            with self.assertRaises(ValueError): runtime.save_filter(state,data)
            self.assertEqual(json.dumps(state),before)
        for i in range(19): runtime.save_filter(state,dict(name=str(i),criteria='papers'))
        with self.assertRaises(ValueError): runtime.save_filter(state,dict(name='21',criteria='papers'))
        key=state['filters'][0]['id']
        runtime.save_filter(state,dict(name='Updated',criteria='new',filter_id=key))
        self.assertEqual(len(state['filters']),20)

    def test_user_content_is_inert_in_editor_and_embedded_json(self):
        state=runtime.new_state()
        runtime.save_filter(state,dict(name='<img src=x>',criteria='</script><script>alert(1)</script>'))
        page=runtime.render(state)
        self.assertNotIn('<img src=x>',page)
        self.assertNotIn('<script>alert(1)',page)
        self.assertEqual(presets(page)[0]['criteria'],state['filters'][0]['criteria'])

    def test_filter_reaches_retriever_without_replacing_query(self):
        with patch.object(runtime,'codex_json',return_value={'sources':[]}) as model:
            runtime.retrieve('exact query','en',criteria='Official sources only')
        payload=json.loads(model.call_args.args[0].split('\n')[-1])
        self.assertEqual(payload['query'],'exact query')
        self.assertEqual(payload['filter_criteria'],'Official sources only')
        self.assertTrue(model.call_args.kwargs['live_search'])

    def test_filtered_ranking_requires_evidence_and_allows_empty(self):
        candidates=[dict(id=0,url='https://example.com/a',title='A',snippet='A paper')]
        with patch.object(runtime,'model_json',return_value={'results':[]}) as model:
            self.assertEqual(runtime.ranked('query',candidates,'en',criteria='Papers only'),[])
            self.assertEqual(model.call_args.args[1]['filter_criteria'],'Papers only')
        for choice in [dict(id=0,score=9),dict(id=0,score=9,matches_filter=False,filter_evidence='no'),
                       dict(id=99,score=9,matches_filter=True,filter_evidence='invented')]:
            with patch.object(runtime,'model_json',return_value={'results':[choice]}):
                with self.assertRaises(ValueError): runtime.ranked('query',candidates,'en',criteria='Papers')
        with patch.object(runtime,'model_json',return_value={'results':[dict(
            id=0,score=8.5,matches_filter=True,filter_evidence='Snippet identifies a paper')]}):
            self.assertEqual(runtime.ranked('query',candidates,'en',criteria='Papers')[0]['url'],candidates[0]['url'])

    def test_edit_delete_and_more_keep_search_snapshot(self):
        candidates=[dict(id=0,url='https://example.com/a',title='A',snippet='A')]
        results=[dict(url='https://example.com/a',title='A',summary='A',score=8)]
        with session() as post, patch.object(runtime,'retrieve',return_value=candidates) as retrieve, \
             patch.object(runtime,'ranked',return_value=results):
            page=post('filter_save',name='Research',criteria='Original papers')
            key=presets(page)[0]['id']
            retrieve.assert_not_called()
            post('search',query='batteries',filter_id=key)
            self.assertEqual(retrieve.call_args.kwargs['criteria'],'Original papers')
            post('filter_save',filter_id=key,name='Research',criteria='Reviews only')
            page=post('more')
            self.assertEqual(retrieve.call_args.kwargs['criteria'],'Original papers')
            self.assertIn('Original papers</p>',page)
            self.assertEqual(page.count('<article data-prairie-result'),1)
            page=post('filter_delete',filter_id=key)
            self.assertEqual(presets(page),[])
            post('retry')
            self.assertEqual(retrieve.call_args.kwargs['criteria'],'Original papers')
            post('search',query='batteries',filter_id='')
            self.assertEqual(retrieve.call_args.kwargs['criteria'],'')

    def test_no_matches_is_a_successful_results_page(self):
        with session() as post, patch.object(runtime,'retrieve',return_value=[dict(id=0,url='https://example.com',title='A',snippet='A')]), \
             patch.object(runtime,'ranked',return_value=[]):
            key=presets(post('filter_save',name='Papers',criteria='Only papers'))[0]['id']
            page=post('search',query='tea',filter_id=key)
            self.assertIn('data-prairie-page="results"',page)
            self.assertIn('No sources matched',page)
            self.assertNotIn('role="alert"',page)
            self.assertIn('data-runtime-action="more"',page)

    def test_failed_search_retry_uses_snapshot_after_edit(self):
        with session() as post:
            key=presets(post('filter_save',name='Papers',criteria='Original'))[0]['id']
            with patch.object(runtime,'retrieve',side_effect=TimeoutError):
                page=post('search',query='tea',filter_id=key)
            self.assertIn('data-runtime-action="retry"',page)
            post('filter_save',filter_id=key,name='Papers',criteria='Edited')
            with patch.object(runtime,'retrieve',return_value=[dict(id=0,url='https://example.com',title='A',snippet='A')]) as retrieve, \
                 patch.object(runtime,'ranked',return_value=[]):
                post('retry')
            self.assertEqual(retrieve.call_args.kwargs['criteria'],'Original')

    def test_filters_are_session_isolated_and_invalid_requests_do_not_search(self):
        with session() as first, session() as second, patch.object(runtime,'retrieve') as retrieve:
            key=presets(first('filter_save',name='Private preset',criteria='Criteria'))[0]['id']
            self.assertEqual(presets(second('theme')),[])
            for action in ['filter_delete','search']:
                with self.assertRaises(urllib.error.HTTPError) as exc:
                    second(action,filter_id=key,query='test')
                self.assertEqual(exc.exception.code,400)
                exc.exception.close()
            retrieve.assert_not_called()


if __name__=='__main__': unittest.main()
