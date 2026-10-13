import hashlib
import importlib
import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import fitz
from docx import Document

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))


def pdf_bytes(text='SJG 223-2026\nEngineering Standard\n1 General provisions', pages=2):
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((60, 70), text if i == 0 else f'Appendix A\nPage {i+1}')
    data = doc.tobytes()
    doc.close()
    return data


class HelpersTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.inspect = importlib.import_module('inspect_document').inspect_document
        self.download = importlib.import_module('download').download_one
        self.assemble = importlib.import_module('assemble_pages').assemble_pages

    def tearDown(self):
        self.tmp.cleanup()

    def write_pdf(self, name='a.pdf', **kw):
        file = self.root / name
        file.write_bytes(pdf_bytes(**kw))
        return file

    def test_valid_file_does_not_automatically_claim_verified(self):
        result = self.inspect(self.write_pdf(), expected_standard='SJG 223-2026', expected_pages=2)
        self.assertEqual(result['status'], 'downloaded_pending_review')
        self.assertEqual(result['identity_match'], True)
        self.assertEqual(result['pages'], 2)
        self.assertEqual(result['completeness'], 'not_established')

    def test_wrong_year_and_missing_pages_are_reported(self):
        result = self.inspect(self.write_pdf(), expected_standard='SJG 223-2025', expected_pages=3)
        self.assertFalse(result['identity_match'])
        self.assertIn('page_count_mismatch', result['warnings'])
        self.assertIn('standard_identity_mismatch', result['warnings'])

    def test_html_cannot_pass_as_pdf(self):
        file = self.root / 'fake.pdf'
        file.write_text('<html>login required</html>')
        self.assertEqual(self.inspect(file)['status'], 'invalid_file')

    def test_corrupt_pdf_is_invalid(self):
        file = self.root / 'bad.pdf'
        file.write_bytes(b'%PDF-1.7\ninvalid')
        self.assertEqual(self.inspect(file)['status'], 'invalid_file')

    def test_title_about_drafting_is_not_a_draft_edition(self):
        result = self.inspect(self.write_pdf(text='SJG 223-2026\nRules for drafting engineering construction standards'))
        self.assertNotIn('draft_or_preview', result['warnings'])

    def test_draft_cover_is_flagged(self):
        result = self.inspect(self.write_pdf(text='SJG 223-2026\nDRAFT FOR COMMENT'))
        self.assertIn('draft_or_preview', result['warnings'])

    def test_scanned_pages_require_visual_review(self):
        doc = fitz.open()
        doc.new_page()
        file = self.root / 'scan.pdf'
        doc.save(file)
        doc.close()
        result = self.inspect(file, expected_standard='SJG 223-2026')
        self.assertIsNone(result['identity_match'])
        self.assertIn('image_or_low_text_pages', result['warnings'])
        self.assertEqual(result['watermark'], 'not_visually_checked')

    def test_docx_native_format_and_no_invented_page_count(self):
        doc = Document()
        doc.add_paragraph('SJG 223-2026 Engineering standard')
        file = self.root / 'native.docx'
        doc.save(file)
        result = self.inspect(file, expected_standard='SJG 223-2026')
        self.assertEqual(result['format'], 'docx')
        self.assertIsNone(result['pages'])
        self.assertTrue(result['identity_match'])

    def test_zip_is_not_docx(self):
        import zipfile
        file = self.root / 'a.docx'
        with zipfile.ZipFile(file, 'w') as z:
            z.writestr('readme.txt', 'not Word')
        self.assertEqual(self.inspect(file)['status'], 'invalid_file')

    def server(self):
        payload = pdf_bytes()
        counts = {}
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                counts[self.path] = counts.get(self.path, 0) + 1
                if self.path == '/redirect':
                    self.send_response(302)
                    self.send_header('Location', '/file')
                    self.end_headers()
                    return
                if self.path == '/retry' and counts[self.path] == 1:
                    self.send_response(503)
                    self.end_headers()
                    return
                code = 429 if self.path == '/limited' else 403 if self.path == '/forbidden' else 404 if self.path == '/missing' else 200
                data = b'<html>login</html>' if self.path == '/html' else payload
                self.send_response(code)
                self.send_header('Content-Length', str(len(data)))
                if self.path == '/limited':
                    self.send_header('Retry-After', '120')
                self.end_headers()
                self.wfile.write(data)
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return f'http://127.0.0.1:{server.server_port}', counts, payload

    def test_redirect_download_preserves_bytes_and_hash(self):
        url, counts, payload = self.server()
        result = self.download(url + '/redirect', self.root / 'got.pdf', retry_delay=0)
        self.assertTrue(result['ok'])
        self.assertEqual((self.root / 'got.pdf').read_bytes(), payload)
        self.assertEqual(result['sha256'], hashlib.sha256(payload).hexdigest())
        self.assertEqual(result['redirects'], 1)

    def test_download_checks_final_filename_extension(self):
        url, _, _ = self.server()
        result = self.download(url + '/file', self.root / 'wrong.docx', retry_delay=0)
        self.assertTrue(result['ok'])
        self.assertIn('extension_format_mismatch', result['inspection']['warnings'])

    def test_reader_copy_supports_page_images(self):
        from PIL import Image
        image = self.root / 'page.png'
        Image.new('RGB', (100, 150), 'white').save(image)
        spec = {'source_url': 'https://example.com/viewer', 'expected_pages': 1,
                'pages': [{'number': 1, 'path': str(image)}]}
        result = self.assemble(spec, self.root / 'copy.pdf')
        self.assertEqual(result['pages'], 1)
        self.assertEqual(result['artifact_kind'], 'reader_copy')

    def test_temporary_error_is_retried_and_access_denial_is_not(self):
        url, counts, _ = self.server()
        self.assertTrue(self.download(url + '/retry', self.root / 'retry.pdf', retry_delay=0)['ok'])
        self.assertEqual(counts['/retry'], 2)
        result = self.download(url + '/forbidden', self.root / 'no.pdf', retry_delay=0)
        self.assertFalse(result['ok'])
        self.assertEqual(counts['/forbidden'], 1)
        self.assertFalse((self.root / 'no.pdf').exists())

    def test_long_rate_limit_is_reported_without_repeated_requests(self):
        url, counts, _ = self.server()
        result = self.download(url + '/limited', self.root / 'limited.pdf', retry_delay=0)
        self.assertFalse(result['ok'])
        self.assertEqual(result['reason'], 'rate_limited')
        self.assertEqual(result['retry_after_seconds'], 120)
        self.assertEqual(counts['/limited'], 1)

    def test_html_and_size_limit_leave_no_partial_file(self):
        url, _, _ = self.server()
        for endpoint, max_bytes in [('/html', 100000), ('/file', 10)]:
            file = self.root / (endpoint[1:] + '.pdf')
            result = self.download(url + endpoint, file, max_bytes=max_bytes, retry_delay=0)
            self.assertFalse(result['ok'])
            self.assertFalse(file.exists())
        self.assertEqual(list(self.root.glob('*.part')), [])

    def test_existing_output_is_not_overwritten(self):
        file = self.root / 'existing.pdf'
        file.write_bytes(b'keep')
        result = self.download('http://127.0.0.1:1/file', file, retry_delay=0)
        self.assertFalse(result['ok'])
        self.assertEqual(file.read_bytes(), b'keep')

    def test_batch_continues_after_one_failure(self):
        url, _, _ = self.server()
        module = importlib.import_module('download')
        results = module.download_batch([
            {'url': url + '/missing', 'output': str(self.root / 'missing.pdf')},
            {'url': url + '/file', 'output': str(self.root / 'valid.pdf')}
        ], retry_delay=0)
        self.assertFalse(results[0]['ok'])
        self.assertTrue(results[1]['ok'])

    def test_sensitive_url_data_is_redacted(self):
        module = importlib.import_module('download')
        result = module.public_url('https://example.com/file?id=42&token=secret&X-Amz-Signature=secret')
        self.assertIn('id=42', result)
        self.assertNotIn('secret', result)

    def test_cross_origin_redirect_does_not_forward_credentials(self):
        received = []
        payload = pdf_bytes()
        class Target(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                received.append(dict(self.headers))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(payload)
        target = ThreadingHTTPServer(('127.0.0.1', 0), Target)
        threading.Thread(target=target.serve_forever, daemon=True).start()
        self.addCleanup(target.server_close)
        self.addCleanup(target.shutdown)
        class Redirect(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                self.send_response(302)
                self.send_header('Location', f'http://127.0.0.1:{target.server_port}/file')
                self.end_headers()
        redirect = ThreadingHTTPServer(('127.0.0.1', 0), Redirect)
        threading.Thread(target=redirect.serve_forever, daemon=True).start()
        self.addCleanup(redirect.server_close)
        self.addCleanup(redirect.shutdown)
        result = self.download(f'http://127.0.0.1:{redirect.server_port}/redirect', self.root / 'safe.pdf',
                               headers={'Authorization': 'Bearer private', 'Cookie': 'session=private', 'X-Api-Key': 'private'})
        self.assertTrue(result['ok'])
        self.assertNotIn('Authorization', received[0])
        self.assertNotIn('Cookie', received[0])
        self.assertNotIn('X-Api-Key', received[0])

    def test_extension_mismatch_is_reported_without_changing_bytes(self):
        file = self.write_pdf(name='wrong.docx')
        result = self.inspect(file)
        self.assertEqual(result['format'], 'pdf')
        self.assertIn('extension_format_mismatch', result['warnings'])

    def test_reader_copy_rejects_duplicate_page_number(self):
        first = self.write_pdf(pages=1)
        spec = {'source_url': 'https://example.com/viewer', 'expected_pages': 2,
                'pages': [{'number': 1, 'path': str(first)}, {'number': 1, 'path': str(first)}]}
        with self.assertRaises(ValueError):
            self.assemble(spec, self.root / 'copy.pdf')

    def test_reader_copy_orders_pages_and_cannot_claim_original(self):
        first = self.write_pdf(name='first.pdf', text='First page', pages=1)
        second = self.write_pdf(name='second.pdf', text='Second page', pages=1)
        spec = {'source_url': 'https://example.com/viewer', 'expected_pages': 2,
                'pages': [{'number': 2, 'path': str(second)}, {'number': 1, 'path': str(first)}]}
        result = self.assemble(spec, self.root / 'copy.pdf')
        self.assertEqual(result['artifact_kind'], 'reader_copy')
        with fitz.open(self.root / 'copy.pdf') as doc:
            self.assertEqual(len(doc), 2)
            self.assertIn('First page', doc[0].get_text())
        self.assertEqual(result['status'], 'downloaded_pending_review')

    def test_report_path_cannot_overwrite_document(self):
        import subprocess
        url, _, _ = self.server()
        original = self.write_pdf(name='original.pdf')
        before = original.read_bytes()
        output = self.root / 'new.pdf'
        batch_output = self.root / 'batch.pdf'
        batch = self.root / 'batch.json'
        batch.write_text(json.dumps([{'url': url + '/file', 'output': str(batch_output)}]))
        page = self.write_pdf(name='page.pdf', pages=1)
        manifest = self.root / 'pages.json'
        manifest.write_text(json.dumps({'source_url': url + '/viewer', 'expected_pages': 1,
                                       'pages': [{'number': 1, 'path': str(page)}]}))
        copy_output = self.root / 'copy.pdf'
        cases = [
            ['inspect_document.py', str(original), '--report', str(original)],
            ['download.py', '--url', url + '/file', '--output', str(output), '--report', str(output)],
            ['download.py', '--batch', str(batch), '--report', str(batch_output)],
            ['assemble_pages.py', '--manifest', str(manifest), '--output', str(copy_output), '--report', str(copy_output)]
        ]
        for args in cases:
            with self.subTest(args=args[:2]):
                run = subprocess.run([sys.executable, str(SCRIPTS / args[0]), *args[1:]], capture_output=True)
                self.assertNotEqual(run.returncode, 0)
        self.assertEqual(original.read_bytes(), before)
        self.assertFalse(output.exists())
        self.assertFalse(batch_output.exists())
        self.assertFalse(copy_output.exists())

    def test_missing_reader_pages_prevents_full_copy(self):
        first = self.write_pdf(pages=1)
        spec = {'source_url': 'https://example.com/viewer', 'expected_pages': 2,
                'pages': [{'number': 1, 'path': str(first)}]}
        with self.assertRaises(ValueError):
            self.assemble(spec, self.root / 'copy.pdf')
        self.assertFalse((self.root / 'copy.pdf').exists())

if __name__ == '__main__':
    unittest.main(verbosity=2)
