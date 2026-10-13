#!/usr/bin/env python3
"""Assemble permitted local reader pages into a clearly labelled PDF reading copy."""
import argparse
import json
import os
import tempfile
from pathlib import Path
import fitz
from inspect_document import inspect_document, report_conflicts


def assemble_pages(manifest, output):
    output = Path(output).expanduser().resolve()
    if output.exists():
        raise ValueError('output_already_exists')
    total = manifest.get('expected_pages')
    pages = manifest.get('pages', [])
    if not isinstance(total, int) or isinstance(total, bool) or total < 1:
        raise ValueError('expected_pages_must_be_known')
    numbers = [p['number'] for p in pages]
    if any(type(n) is not int for n in numbers) or sorted(numbers) != list(range(1, total + 1)):
        raise ValueError('missing_or_duplicate_pages')
    if not manifest.get('source_url'):
        raise ValueError('source_url_required')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    with fitz.open() as merged:
        for entry in sorted(pages, key=lambda p: p['number']):
            path = Path(entry['path']).expanduser().resolve()
            with fitz.open(path) as page_doc:
                if page_doc.is_pdf:
                    if len(page_doc) != 1 or page_doc.needs_pass:
                        raise ValueError('each_pdf_entry_must_be_one_readable_page')
                    merged.insert_pdf(page_doc)
                else:
                    with fitz.open('pdf', page_doc.convert_to_pdf()) as image_pdf:
                        if len(image_pdf) != 1:
                            raise ValueError('each_image_entry_must_be_one_page')
                        merged.insert_pdf(image_pdf)
        merged.set_metadata({'title': 'Reading copy / 阅读副本',
                             'subject': 'Assembled from online reader pages; not an original publisher PDF',
                             'creator': 'download-engineering-standards'})
        try:
            fd, name = tempfile.mkstemp(prefix=output.name + '.', suffix='.part', dir=output.parent)
            os.close(fd)
            temporary = Path(name)
            merged.save(temporary)
            os.link(temporary, output)
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)
    result = inspect_document(output, manifest.get('expected_standard'), total)
    from download import public_url
    result.update(artifact_kind='reader_copy', source_url=public_url(manifest['source_url']),
                  generation_method='local_reader_pages_in_page_number_order')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if report_conflicts(args.report, args.output, args.manifest):
        parser.error('--report must not overwrite the document or manifest')
    try:
        manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
        # Resolve relative page paths against the manifest, not the working directory.
        for entry in manifest.get('pages', []):
            page = Path(entry['path'])
            if not page.is_absolute():
                entry['path'] = str((args.manifest.parent / page).resolve())
        if report_conflicts(args.report, *[entry['path'] for entry in manifest.get('pages', [])]):
            parser.error('--report must not overwrite source pages')
        result = assemble_pages(manifest, args.output)
    except Exception as exc:
        result = {'status': 'assembly_failed', 'reason': str(exc) if isinstance(exc, ValueError) else type(exc).__name__}
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + '\n', encoding='utf-8')
    print(rendered)
    return 1 if result['status'] == 'assembly_failed' else 0


if __name__ == '__main__':
    raise SystemExit(main())
