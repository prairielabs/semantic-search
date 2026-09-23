import importlib.util
import json
import threading
import io
import contextlib
from types import SimpleNamespace
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('runtime',Path(__file__).with_name('server.py'))
runtime=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class RuntimeTests(unittest.TestCase):
    def test_missing_cli_has_actionable_setup_error(self):
        with patch.object(runtime.shutil, 'which', return_value=None):
            with self.assertRaisesRegex(runtime.SetupError, 'npm install'):
                runtime.check_dependencies()

    def test_outdated_cli_stops_before_sign_in_or_browser(self):
        with patch.object(runtime.shutil, 'which', return_value='/fake/codex'), \
             patch.object(runtime.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='old help')) as run:
            with self.assertRaisesRegex(runtime.SetupError, 'Update Codex'):
                runtime.check_dependencies()
        self.assertEqual(run.call_count, 1)

    def test_api_key_login_is_not_silently_used(self):
        help_text='--ignore-user-config --ephemeral --output-schema --json'
        responses=[SimpleNamespace(returncode=0, stdout=help_text),
                   SimpleNamespace(returncode=0, stdout='Logged in using an API key', stderr='')]
        with patch.object(runtime.shutil, 'which', return_value='/fake/codex'), \
             patch.object(runtime.subprocess, 'run', side_effect=responses):
            with self.assertRaisesRegex(runtime.SetupError, 'ChatGPT'):
                runtime.check_dependencies()

    def test_failed_setup_does_not_open_browser(self):
        with patch.object(runtime.sys, 'argv', ['start.py', '--check']), \
             patch.object(runtime, 'check_dependencies'), \
             patch.object(runtime, 'check_live_access', side_effect=runtime.SetupError('No access')), \
             patch.object(runtime.webbrowser, 'open') as browser, \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(runtime.main(), 1)
        browser.assert_not_called()

    def test_terra_used_for_all_calls_and_web_search_only_for_retrieval(self):
        output=json.dumps(dict(type='item.completed', item=dict(type='agent_message', text='{"ok":true}')))
        with patch.object(runtime.shutil, 'which', return_value='/fake/codex'), \
             patch.object(runtime.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout=output)) as run:
            self.assertEqual(runtime.model_json('Return ok', {}, runtime.string_schema({'ok':{'type':'boolean'}})), {'ok':True})
        command=run.call_args.args[0]
        self.assertEqual(command[command.index('-m')+1], 'gpt-5.6-terra')
        self.assertIn('web_search="disabled"', command)
        self.assertIn('--ignore-user-config', command)
        self.assertIn('--ephemeral', command)
        self.assertIn('forced_login_method="chatgpt"', command)
        self.assertFalse(run.call_args.kwargs.get('shell', False))

    def test_failed_turn_cannot_render_an_earlier_model_message(self):
        output='\n'.join([json.dumps(dict(type='item.completed', item=dict(type='agent_message', text='{"ok":true}'))),
                          json.dumps(dict(type='turn.failed'))])
        with patch.object(runtime.shutil, 'which', return_value='/fake/codex'), \
             patch.object(runtime.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout=output)):
            with self.assertRaises(ValueError):
                runtime.codex_json('test', {})

    def test_static_preview_notice_is_absent_from_connected_app(self):
        self.assertIn('interface preview', (runtime.ROOT/'index.html').read_text(encoding='utf-8'))
        page=runtime.render(runtime.new_state())
        self.assertNotIn('interface preview', page)
        self.assertIn('Settings changes will trigger inference', page)
        self.assertNotIn('Language changes will trigger inference', page)

    def test_generated_text_is_inert(self):
        state=runtime.new_state()
        state.update(query='<img src=x onerror=alert(1)>',results=[dict(
            url='https://example.com/?q="&x=1',title='<script>alert(1)</script>',
            summary='<img src=x>',score=8.4)])
        page=runtime.render(state)
        self.assertNotIn('<img src=x',page)
        self.assertNotIn('<script>alert(1)',page)
        self.assertIn('&lt;script&gt;',page)
        self.assertIn('value="8.4"',page)
        self.assertIn('8.4/10',page)

    def test_model_cannot_supply_urls_or_duplicate_ids(self):
        candidates=[dict(id=0,url='https://example.com/real',title='Real',snippet='Source')]
        output={'results':[dict(id=99,url='https://invented.example',score=10,summary='Bad'),
                           dict(id=0,url='https://invented.example',score=8.4,summary='Good'),
                           dict(id=0,score=9,summary='Duplicate')]}
        with patch.object(runtime,'model_json',return_value=output):
            result=runtime.ranked('test',candidates,'en')
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['url'],candidates[0]['url'])

    def test_invented_ids_fail_closed(self):
        with patch.object(runtime,'model_json',return_value={'results':[dict(id=999,score=10,summary='Fake')]}):
            with self.assertRaises(ValueError):
                runtime.ranked('test',[dict(id=0,url='https://example.com',title='Real',snippet='Real')],'en')

    def test_retrieval_requires_completed_search_event(self):
        output=json.dumps(dict(type='item.completed',item=dict(type='agent_message',
            text=json.dumps({'sources':[dict(url='https://example.com',title='Unverified',snippet='No search')]}))))
        with patch.object(runtime.shutil,'which',return_value='/fake/codex'), \
             patch.object(runtime.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=output)):
            with self.assertRaises(ValueError):
                runtime.retrieve('test','en')

    def test_retrieval_passes_exact_query_without_shell_interpolation(self):
        output='\n'.join([json.dumps(dict(type='item.completed',item=dict(type='web_search'))),
            json.dumps(dict(type='item.completed',item=dict(type='agent_message',text=json.dumps(
                {'sources':[dict(url='https://example.com',title='Real',snippet='Verified')]}))))])
        query='exact "query" $(not-a-command)'
        with patch.object(runtime.shutil,'which',return_value='/fake/codex'), \
             patch.object(runtime.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=output)) as run:
            rows=runtime.retrieve(query,'en')
        self.assertEqual(rows[0]['url'],'https://example.com')
        self.assertEqual(json.loads(run.call_args.kwargs['input'].split('\n')[-1])['query'],query)
        self.assertFalse(run.call_args.kwargs.get('shell',False))

    def test_weak_live_candidates_reach_the_ranker(self):
        sources=[dict(url='https://example.com/weak',title='Weak match',snippet='A provider result')]
        output='\n'.join([json.dumps(dict(type='item.completed',item=dict(type='web_search'))),
            json.dumps(dict(type='item.completed',item=dict(type='agent_message',text=json.dumps(
                dict(sources=sources,error=None)))))])
        with patch.object(runtime.shutil,'which',return_value='/fake/codex'), \
             patch.object(runtime.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=output)):
            rows=runtime.retrieve('awdaklwd','en')
        self.assertEqual(len(rows),1)
        with patch.object(runtime,'model_json',return_value=dict(results=[dict(id=0,score=0.2)])):
            result=runtime.ranked('awdaklwd',rows,'en')
        self.assertEqual(result[0]['url'],sources[0]['url'])
        self.assertEqual(result[0]['score'],0.2)

    def test_loading_status_does_not_shift_title_layout(self):
        page=runtime.render(runtime.new_state())
        self.assertEqual(page.count('id="runtime-status"'),1)
        self.assertIn('id="runtime-status" class="visually-hidden"',page)
        self.assertLess(page.index('id="runtime-status"'),page.index('</section>',page.index('<main')))

    def test_identical_regional_source_copies_are_collapsed(self):
        sources=[dict(url='https://example.com/definition/aw',title='aw definition',snippet='Same entry'),
                 dict(url='https://example.com/us/definition/aw',title='aw definition',snippet='Same entry')]
        output='\n'.join([json.dumps(dict(type='item.completed',item=dict(type='web_search'))),
            json.dumps(dict(type='item.completed',item=dict(type='agent_message',text=json.dumps(
                dict(sources=sources,error=None)))))])
        with patch.object(runtime.shutil,'which',return_value='/fake/codex'), \
             patch.object(runtime.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=output)):
            rows=runtime.retrieve('awdaklwd','en')
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['url'],sources[0]['url'])

    def test_unsafe_urls_rejected(self):
        for url in ['javascript:alert(1)','http://localhost/','http://127.0.0.1/',
                    'https://user:password@example.com/','http://10.0.0.1/','http://[::1]/']:
            self.assertFalse(runtime.safe_url(url))
        self.assertTrue(runtime.safe_url('https://docs.python.org/'))

    def test_translation_preserves_sources_order_and_scores(self):
        state=runtime.new_state()
        state['results']=[dict(url='https://example.com',title='Example',summary='Old',score=8.4)]
        answer=dict(code='es',abbreviation='ES',labels=runtime.EN,summaries=['Nuevo'])
        with patch.object(runtime,'model_json',return_value=answer):
            runtime.translate(state,'Spanish')
        self.assertEqual(state['results'],[dict(url='https://example.com',title='Example',summary='Nuevo',score=8.4)])

    def test_loopback_host_origin_and_file_boundaries(self):
        server=runtime.ThreadingHTTPServer(('127.0.0.1',0),runtime.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        base='http://127.0.0.1:'+str(server.server_port)
        try:
            for path in ['/.git/config','/context.md','/../index.html']:
                with self.assertRaises(urllib.error.HTTPError) as e:
                    urllib.request.urlopen(base+path)
                self.assertEqual(e.exception.code,404)
                e.exception.close()
            request=urllib.request.Request(base+'/api/action',data=b'{"action":"theme"}',
                headers={'Origin':'https://foreign.example','Content-Type':'application/json'})
            with self.assertRaises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(request)
            self.assertEqual(e.exception.code,403)
            e.exception.close()
            request=urllib.request.Request(base+'/',headers={'Host':'foreign.example'})
            with self.assertRaises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(request)
            self.assertEqual(e.exception.code,403)
            e.exception.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_failure_keeps_query_and_existing_results(self):
        state=runtime.new_state()
        state.update(query='Retained query',error=True,results=[dict(url='https://example.com',
                    title='Retained source',summary='Real source',score=7.6)])
        page=runtime.render(state)
        self.assertIn('Search temporarily unavailable',page)
        self.assertIn('value="Retained query"',page)
        self.assertIn('Retained source',page)
        self.assertIn('data-runtime-action="retry"',page)

    def test_retrieval_failure_returns_visible_retry_through_http(self):
        server=runtime.ThreadingHTTPServer(('127.0.0.1',0),runtime.Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        base='http://127.0.0.1:'+str(server.server_port)
        try:
            request=urllib.request.Request(base+'/api/action',
                data=json.dumps(dict(action='search',query='Keep this query')).encode(),
                headers={'Origin':base,'Content-Type':'application/json'})
            with patch.object(runtime,'retrieve',side_effect=TimeoutError):
                with urllib.request.urlopen(request) as response:
                    page=response.read().decode()
            self.assertIn('Search temporarily unavailable',page)
            self.assertIn('value="Keep this query"',page)
            self.assertIn('data-runtime-action="retry"',page)
            self.assertNotIn('<article data-prairie-result',page)
        finally:
            server.shutdown()
            server.server_close()


if __name__=='__main__':
    unittest.main()
