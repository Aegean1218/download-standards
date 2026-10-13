#!/usr/bin/env python3
"""Save an already discovered PDF/Word URL, atomically, with bounded retries and JSON evidence."""
import argparse
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
import requests
from inspect_document import document_format, inspect_document, report_conflicts

SECRET_KEYS = {'token', 'access_token', 'authorization', 'auth', 'cookie', 'session',
               'sessionid', 'jsessionid', 'key', 'api_key', 'signature', 'sig',
               'x-amz-signature', 'x-amz-credential', 'x-amz-security-token', 'password', 'ticket'}


def public_url(url):
    parts = urlsplit(str(url))
    netloc = parts.netloc.rsplit('@', 1)[-1]
    query = urlencode([(key, '[redacted]' if key.lower() in SECRET_KEYS else val)
                       for key, val in parse_qsl(parts.query, keep_blank_values=True)])
    return urlunsplit((parts.scheme, netloc, parts.path, query, ''))


def origin(url):
    p = urlsplit(url)
    return p.scheme, p.hostname, p.port


def download_one(url, output, *, headers=None, referer=None, timeout=30, attempts=3,
                 max_bytes=250 * 1024 * 1024, retry_delay=1, expected_standard=None,
                 expected_pages=None):
    destination = Path(output).expanduser().resolve()
    result = {'ok': False, 'source_url': public_url(url), 'final_url': None,
              'path': str(destination), 'checked_at': datetime.now(timezone.utc).isoformat(),
              'attempts': [], 'redirects': 0, 'status': 'download_failed'}
    if urlsplit(url).scheme not in ('http', 'https') or not urlsplit(url).hostname:
        result['reason'] = 'invalid_http_url'
        return result
    if timeout <= 0 or attempts not in range(1, 6) or max_bytes <= 0:
        result['reason'] = 'invalid_limits'
        return result
    if destination.exists():
        result['reason'] = 'output_already_exists'
        return result
    request_headers = {'User-Agent': 'EngineeringStandardsDownload/1.0', 'Accept-Encoding': 'identity'}
    request_headers.update(headers or {})
    if referer:
        request_headers['Referer'] = referer
    destination.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, attempts + 1):
        temporary = None
        retry = False
        wait_seconds = min(retry_delay * 2 ** (attempt - 1), 5)
        response = None
        try:
            current_url = url
            current_headers = dict(request_headers)
            redirects = 0
            # Separate requests ensure cookies aren't forwarded to an unrelated host.
            while True:
                response = requests.get(current_url, headers=current_headers, timeout=(timeout, timeout),
                                        stream=True, allow_redirects=False)
                if response.status_code not in (301, 302, 303, 307, 308):
                    break
                location = response.headers.get('Location')
                response.close()
                if not location or redirects >= 10:
                    raise ValueError('invalid_or_excessive_redirects')
                next_url = urljoin(current_url, location)
                if urlsplit(next_url).scheme not in ('http', 'https'):
                    raise ValueError('non_http_redirect')
                if urlsplit(current_url).scheme == 'https' and urlsplit(next_url).scheme == 'http':
                    raise ValueError('https_downgrade_redirect')
                if origin(next_url) != origin(current_url):
                    current_headers = {key: value for key, value in current_headers.items()
                                       if key.lower() in ('user-agent', 'accept', 'accept-encoding')}
                current_url = next_url
                redirects += 1
            result['final_url'] = public_url(current_url)
            result['redirects'] = redirects
            code = response.status_code
            result['attempts'].append({'number': attempt, 'http_status': code})
            if code != 200:
                result['reason'] = ('access_or_payment_required' if code in (401, 402, 403)
                                    else 'rate_limited' if code == 429 else 'http_error')
                retry = code in (408, 429, 500, 502, 503, 504)
                retry_after = response.headers.get('Retry-After')
                if retry and retry_after:
                    try:
                        requested_wait = float(retry_after)
                    except ValueError:
                        try:
                            requested_wait = (parsedate_to_datetime(retry_after) - datetime.now(timezone.utc)).total_seconds()
                        except (ValueError, TypeError, OverflowError):
                            requested_wait = 0
                    result['retry_after_seconds'] = max(0, requested_wait)
                    if requested_wait > 30:
                        retry = False
                    else:
                        wait_seconds = max(wait_seconds, requested_wait)
            else:
                declared = response.headers.get('Content-Length')
                if declared and declared.isdigit() and int(declared) > max_bytes:
                    raise ValueError('size_limit_exceeded')
                fd, name = tempfile.mkstemp(prefix=destination.name + '.', suffix='.part', dir=destination.parent)
                temporary = Path(name)
                total = 0
                with os.fdopen(fd, 'wb') as file:
                    for chunk in response.iter_content(128 * 1024):
                        total += len(chunk)
                        if total > max_bytes:
                            raise ValueError('size_limit_exceeded')
                        file.write(chunk)
                if document_format(temporary) == 'unknown':
                    raise ValueError('not_pdf_or_word_response')
                inspection = inspect_document(temporary, expected_standard, expected_pages, filename=destination)
                if inspection['status'] == 'invalid_file':
                    raise ValueError('invalid_document')
                # Hard link atomically fails if another download created the output meanwhile.
                os.link(temporary, destination)
                temporary.unlink()
                temporary = None
                inspection['path'] = str(destination)
                result.update(ok=True, status='downloaded_pending_review',
                              bytes=total, sha256=inspection['sha256'], inspection=inspection)
                return result
        except (requests.Timeout, requests.ConnectionError, requests.exceptions.ChunkedEncodingError) as exc:
            result['attempts'].append({'number': attempt, 'error': type(exc).__name__})
            result['reason'] = 'network_error'
            retry = True
        except Exception as exc:
            # Exception strings from HTTP libraries can contain credentials or signed URLs.
            result['reason'] = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            retry = False
        finally:
            if response is not None:
                response.close()
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        if not retry or attempt == attempts:
            break
        time.sleep(max(0, wait_seconds))
    return result


def download_batch(items, **options):
    results = []
    for number, item in enumerate(items, 1):
        try:
            if not isinstance(item, dict):
                raise ValueError('item_not_object')
            merged = {**options, **{key: item[key] for key in ('referer', 'expected_standard', 'expected_pages') if key in item}}
            result = download_one(item['url'], item['output'], **merged)
            result['item'] = number
        except Exception as exc:
            result = {'ok': False, 'status': 'download_failed', 'item': number, 'reason': type(exc).__name__}
        results.append(result)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--batch', type=Path, help='JSON array: url, output, optional referer/expected_standard/expected_pages')
    parser.add_argument('--headers-file', type=Path, help='Optional local JSON object of explicitly provided request headers; never logged')
    parser.add_argument('--referer')
    parser.add_argument('--expected-standard')
    parser.add_argument('--expected-pages', type=int)
    parser.add_argument('--timeout', type=float, default=30)
    parser.add_argument('--attempts', type=int, default=3, choices=range(1, 6))
    parser.add_argument('--max-mb', type=float, default=250)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if bool(args.batch) == bool(args.url) or (args.url and not args.output):
        parser.error('use either --batch or --url with --output')
    if report_conflicts(args.report, args.output, args.batch, args.headers_file):
        parser.error('--report must not overwrite documents or input files')
    headers = json.loads(args.headers_file.read_text(encoding='utf-8')) if args.headers_file else None
    if headers is not None and (not isinstance(headers, dict) or any(not isinstance(v, str) for v in headers.values())):
        parser.error('--headers-file must contain a string-valued JSON object')
    options = {'headers': headers, 'referer': args.referer, 'timeout': args.timeout,
               'attempts': args.attempts, 'max_bytes': int(args.max_mb * 1024 * 1024),
               'expected_standard': args.expected_standard, 'expected_pages': args.expected_pages}
    if args.batch:
        items = json.loads(args.batch.read_text(encoding='utf-8'))
        if not isinstance(items, list):
            parser.error('--batch must contain a JSON array')
        if report_conflicts(args.report, *[item.get('output') for item in items if isinstance(item, dict)]):
            parser.error('--report must not overwrite a batch output document')
        if headers:
            parser.error('authenticated headers are single-URL only; use the browser session for batch access')
        result = download_batch(items, **options)
        failed = any(not item['ok'] for item in result)
    else:
        result = download_one(args.url, args.output, **options)
        failed = not result['ok']
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + '\n', encoding='utf-8')
    print(rendered)
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
