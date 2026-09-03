import io
import os
import re
import unittest
import tempfile
import uuid

from db import CHO, Memory, session
from web_app import create_app


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    def test_index_page_loads(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'CORDHISK', response.data)

    def test_index_shows_import_cta_and_delete_confirmations(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Import TXT memory', response.data)
        self.assertIn(b"confirm('Delete this CHO and remove its tags from all memories?')", response.data)

    def test_add_cho_metadata_dialog_removed(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'Add CHO metadata', response.data)

    def test_index_page_includes_license_options(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'CC BY-SA 3.0 IGO', response.data)
        self.assertIn(b'CC BY-NC-ND', response.data)

    def test_sidebar_memory_and_cho_records_are_sorted_by_id(self):
        suffix = uuid.uuid4().hex
        memory_a = Memory(custom_id=f'alpha-{suffix}', title='Alpha', text='', file_path='demo.txt')
        memory_z = Memory(custom_id=f'zulu-{suffix}', title='Zulu', text='', file_path='demo.txt')
        cho_a = CHO(custom_id=f'alpha-cho-{suffix}', title='Alpha CHO')
        cho_z = CHO(custom_id=f'zulu-cho-{suffix}', title='Zulu CHO')
        session.add_all([memory_z, memory_a, cho_z, cho_a])
        session.commit()

        try:
            response = self.client.get('/')
            self.assertEqual(response.status_code, 200)
            page = response.data.decode()
            self.assertLess(page.index(memory_a.custom_id), page.index(memory_z.custom_id))
            self.assertLess(page.index(cho_a.custom_id), page.index(cho_z.custom_id))
        finally:
            session.delete(memory_a)
            session.delete(memory_z)
            session.delete(cho_a)
            session.delete(cho_z)
            session.commit()

    def test_graph_memory_and_cho_nodes_keep_navigation_links(self):
        suffix = uuid.uuid4().hex
        cho = CHO(custom_id=f'cho-nav-{suffix}', title='Navigable CHO')
        memory = Memory(
            custom_id=f'memory-nav-{suffix}',
            title='Navigable memory',
            text=f'A <dc:title cho="{cho.custom_id}">linked</dc:title> record',
            file_path='demo.txt',
        )
        session.add_all([cho, memory])
        session.commit()

        try:
            response = self.client.get(f'/?memory_id={memory.id}')
            self.assertEqual(response.status_code, 200)
            page = response.data.decode()
            self.assertIn(f'<a href="/?memory_id={memory.id}">', page)
            self.assertIn(f'<a href="/?memory_id={memory.id}&focus_cho={cho.custom_id}">', page)
            self.assertNotIn('collapsedByMemory', page)
            self.assertNotIn('collapsedByCho', page)
        finally:
            session.delete(memory)
            session.delete(cho)
            session.commit()

    def test_edit_memory_updates_database(self):
        memory = Memory(
            custom_id='test-memory',
            title='Original title',
            text='Original body',
            file_path='demo.txt'
        )
        session.add(memory)
        session.commit()
        session.refresh(memory)

        try:
            response = self.client.post(
                f'/memories/{memory.id}/edit',
                data={'title': 'Updated title', 'text': 'Updated body'},
                follow_redirects=True,
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Updated title', response.data)

            updated = session.get(Memory, memory.id)
            self.assertEqual(updated.title, 'Updated title')
            self.assertEqual(updated.text, 'Updated body')
            self.assertTrue(updated.file_path.endswith('.txt'))
            self.assertTrue(os.path.exists(updated.file_path))
            with open(updated.file_path, encoding='utf-8') as handle:
                self.assertEqual(handle.read(), 'Updated body')
        finally:
            updated = session.get(Memory, memory.id)
            file_path = updated.file_path if updated is not None else None
            session.delete(memory)
            session.commit()
            if file_path and os.path.exists(file_path):
                os.remove(file_path)

    def test_memory_display_preserves_single_line_breaks(self):
        memory = Memory(
            custom_id=f'test-single-lines-{uuid.uuid4().hex}',
            title='Single line breaks',
            text='First line\nSecond line\nThird line',
            file_path='demo.txt',
        )
        session.add(memory)
        session.commit()

        try:
            response = self.client.get(f'/?memory_id={memory.id}')
            self.assertEqual(response.status_code, 200)
            page = response.data.decode()
            self.assertIn('white-space: pre-line', page)
            self.assertIn('<p>First line\nSecond line\nThird line</p>', page)
        finally:
            session.delete(memory)
            session.commit()

    def test_memory_display_preserves_line_break_after_tagged_text(self):
        cho = CHO(custom_id=f'cho-line-break-{uuid.uuid4().hex}', title='Line break CHO')
        memory = Memory(
            custom_id=f'test-tagged-line-{uuid.uuid4().hex}',
            title='Tagged line break',
            text=f'<dc:subject cho="{cho.custom_id}">First line</dc:subject>\nSecond line',
            file_path='demo.txt',
        )
        session.add_all([cho, memory])
        session.commit()

        try:
            response = self.client.get(f'/?memory_id={memory.id}')
            self.assertEqual(response.status_code, 200)
            page = response.data.decode()
            self.assertIn('</span>\nSecond line</p>', page)
        finally:
            session.delete(memory)
            session.delete(cho)
            session.commit()

    def test_cho_tag_click_targets_its_memory_highlight(self):
        cho = CHO(custom_id=f'cho-scroll-{uuid.uuid4().hex}', title='Scroll CHO')
        memory = Memory(
            custom_id=f'test-cho-scroll-{uuid.uuid4().hex}',
            title='CHO tag scroll',
            text=(
                f'Before <dc:subject cho="{cho.custom_id}">first tagged text</dc:subject> after\n\n'
                f'Before <dc:subject cho="{cho.custom_id}">second tagged text</dc:subject> after'
            ),
            file_path='demo.txt',
        )
        session.add_all([cho, memory])
        session.commit()

        try:
            response = self.client.get(f'/?memory_id={memory.id}')
            self.assertEqual(response.status_code, 200)
            page = response.data.decode()
            self.assertIn('class="pill cho cho-tag-link" data-cho-tag-index="0"', page)
            self.assertIn('class="pill cho cho-tag-link" data-cho-tag-index="1"', page)
            self.assertIn('class="highlight cho" title="dc:subject" data-cho-tag-index="0"', page)
            self.assertIn('class="highlight cho" title="dc:subject" data-cho-tag-index="1"', page)
            self.assertIn("tag.addEventListener('click', function ()", page)
            self.assertNotRegex(page, r"cho-tag-link.*?event\.preventDefault\(\)")
            self.assertIn("targetSpan.scrollIntoView({ behavior: 'smooth', block: 'center' })", page)
        finally:
            session.delete(memory)
            session.delete(cho)
            session.commit()

    def test_tag_selection_is_exclusive(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        page = response.data.decode()
        self.assertIn("document.querySelectorAll('.tag-selector input').forEach(function (otherInput)", page)
        self.assertIn('otherInput.checked = false;', page)

    def test_graph_page_loads(self):
        response = self.client.get('/graph')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'CORDHISK 2.2', response.data)
        self.assertIn(b'CHO records', response.data)

    def test_edit_cho_metadata_updates_memory_text(self):
        memory = Memory(
            custom_id='test-memory-cho',
            title='Memory for CHO editing',
            text='Example <dc:title cho="PR75">watch</dc:title> text',
            file_path='demo.txt'
        )
        session.add(memory)
        session.commit()
        session.refresh(memory)

        try:
            response = self.client.post(
                f'/memories/{memory.id}/edit',
                data={'title': 'Updated memory', 'text': 'Example <dc:title cho="PR75">watch</dc:title> text', 'cho_metadata[PR75][dc:title]': 'updated watch'},
                follow_redirects=True,
            )
            self.assertEqual(response.status_code, 200)
            updated = session.get(Memory, memory.id)
            self.assertIn('updated watch', updated.text)
        finally:
            session.delete(memory)
            session.commit()

    def test_graph_page_includes_metadata_nodes(self):
        response = self.client.get('/graph')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'graph-node', response.data.lower())
        self.assertIn(b'metadata-hidden', response.data.lower())

    def test_cho_id_and_name_are_shown_in_tag_controls_and_graph(self):
        cho_id = f'CHO-LABEL-{uuid.uuid4().hex}'
        cho = CHO(custom_id=cho_id, title='Penico')
        memory = Memory(
            custom_id=f'test-cho-labels-{uuid.uuid4().hex}',
            title='CHO labels',
            text=f'A <dc:title cho="{cho_id}">penico</dc:title> record',
            file_path='demo.txt',
        )
        session.add_all([cho, memory])
        session.commit()
        session.refresh(memory)

        try:
            response = self.client.get(f'/?memory_id={memory.id}')
            self.assertEqual(response.status_code, 200)
            expected_label = f'{cho_id} (Penico)'.encode()
            self.assertIn(f'<option value="{cho_id}">'.encode() + expected_label + b'</option>', response.data)
            self.assertIn(b'data-cho-label="' + expected_label + b'"', response.data)
            self.assertIn(b'>' + expected_label + b'</text>', response.data)
        finally:
            session.delete(memory)
            session.delete(cho)
            session.commit()

    def test_graph_memory_node_uses_custom_id_in_details(self):
        memory = Memory(
            custom_id='TEST-MEMORY-ID',
            title='Memory details test',
            text='Body text',
            file_path='demo.txt'
        )
        session.add(memory)
        session.commit()
        session.refresh(memory)

        try:
            response = self.client.get(f'/?memory_id={memory.id}')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'data-details="TEST-MEMORY-ID"', response.data)
        finally:
            session.delete(memory)
            session.commit()

    def test_delete_metadata_updates_memory_text(self):
        memory = Memory(
            custom_id='test-delete-metadata',
            title='Memory for deletion',
            text='Example <dc:title type="memory">keep me</dc:title> and <dc:title cho="PR75">watch</dc:title> text',
            file_path='demo.txt'
        )
        session.add(memory)
        session.commit()
        session.refresh(memory)

        try:
            response = self.client.post(
                f'/memories/{memory.id}/edit',
                data={
                    'title': 'Updated memory',
                    'text': 'Example <dc:title type="memory">keep me</dc:title> and <dc:title cho="PR75">watch</dc:title> text',
                    'delete_memory_metadata[dc:title]': '1',
                },
                follow_redirects=True,
            )
            self.assertEqual(response.status_code, 200)
            updated = session.get(Memory, memory.id)
            self.assertNotIn('type="memory"', updated.text)
            self.assertIn('watch', updated.text)
        finally:
            session.delete(memory)
            session.commit()

    def test_delete_metadata_preserves_wrapped_text(self):
        memory = Memory(
            custom_id='test-delete-preserves-text',
            title='Memory for preserving text',
            text='Before <dc:title type="memory">Momo</dc:title> after',
            file_path='demo.txt'
        )
        session.add(memory)
        session.commit()
        session.refresh(memory)

        try:
            response = self.client.post(
                f'/memories/{memory.id}/edit',
                data={
                    'title': 'Updated memory',
                    'text': 'Before <dc:title type="memory">Momo</dc:title> after',
                    'delete_memory_metadata[dc:title]': '1',
                },
                follow_redirects=True,
            )
            self.assertEqual(response.status_code, 200)
            updated = session.get(Memory, memory.id)
            self.assertEqual(updated.text, 'Before Momo after')
        finally:
            session.delete(memory)
            session.commit()

    def test_annotation_wraps_selected_text(self):
        memory = Memory(
            custom_id='test-annotation',
            title='Annotated memory',
            text='A selected phrase for tagging',
            file_path='demo.txt'
        )
        session.add(memory)
        session.commit()
        session.refresh(memory)

        try:
            response = self.client.post(
                f'/memories/{memory.id}/annotate',
                data={
                    'selected_annotation_text': 'selected phrase',
                    'annotation_field': 'dc:title',
                    'annotation_cho': 'PR75',
                },
                follow_redirects=True,
            )
            self.assertEqual(response.status_code, 200)
            updated = session.get(Memory, memory.id)
            self.assertIn('<dc:title cho="PR75">selected phrase</dc:title>', updated.text)
        finally:
            session.delete(memory)
            session.commit()

    def test_annotation_uses_selected_occurrence_for_repeated_text(self):
        memory = Memory(
            custom_id='test-annotation-repeated',
            title='Annotated repeated token',
            text='house alpha house beta house gamma',
            file_path='demo.txt'
        )
        session.add(memory)
        session.commit()
        session.refresh(memory)

        try:
            response = self.client.post(
                f'/memories/{memory.id}/annotate',
                data={
                    'selected_annotation_text': 'house',
                    'selected_annotation_occurrence': '2',
                    'annotation_field': 'dc:title',
                    'annotation_cho': 'PR75',
                },
                follow_redirects=True,
            )
            self.assertEqual(response.status_code, 200)
            updated = session.get(Memory, memory.id)
            self.assertEqual(
                updated.text,
                'house alpha house beta <dc:title cho="PR75">house</dc:title> gamma'
            )
        finally:
            session.delete(memory)
            session.commit()

    def test_annotation_position_ignores_hidden_memory_metadata_block(self):
        memory = Memory(
            custom_id='test-annotation-hidden-memory-block',
            title='Annotated with hidden memory metadata block',
            text=(
                '=== MEMORY METADATA START ===\n'
                '<dc:title type="memory">My Memory Title</dc:title>\n'
                '=== MEMORY METADATA END ===\n\n'
                'Before house after'
            ),
            file_path='demo.txt'
        )
        session.add(memory)
        session.commit()
        session.refresh(memory)

        try:
            response = self.client.post(
                f'/memories/{memory.id}/annotate',
                data={
                    'selected_annotation_text': 'house',
                    'selected_annotation_occurrence': '0',
                    'annotation_field': 'dc:title',
                    'annotation_cho': 'PR75',
                },
                follow_redirects=True,
            )
            self.assertEqual(response.status_code, 200)
            updated = session.get(Memory, memory.id)
            self.assertIn('Before <dc:title cho="PR75">house</dc:title> after', updated.text)
            self.assertIn('=== MEMORY METADATA START ===', updated.text)
            self.assertIn('=== MEMORY METADATA END ===', updated.text)
        finally:
            session.delete(memory)
            session.commit()

    def test_search_returns_matching_memory(self):
        memory = Memory(
            custom_id='test-search-memory',
            title='Search title',
            text='The quick brown fox metadata sample',
            file_path='demo.txt'
        )
        session.add(memory)
        session.commit()
        session.refresh(memory)

        try:
            response = self.client.get('/search?q=brown')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'test-search-memory', response.data)
        finally:
            session.delete(memory)
            session.commit()

    def test_search_pagination_and_snippet_preview(self):
        term = 'pagination-snippet-unique-token'
        created = []

        for i in range(12):
            memory = Memory(
                custom_id=f'test-search-page-{i}',
                title=f'Search page {i}',
                text=f'Prefix context {term} suffix context item {i}',
                file_path='demo.txt'
            )
            session.add(memory)
            created.append(memory)
        session.commit()

        try:
            page_one = self.client.get(f'/search?q={term}&page=1')
            self.assertEqual(page_one.status_code, 200)
            self.assertIn(b'Page 1 of 2', page_one.data)
            self.assertIn(term.encode('utf-8'), page_one.data)

            page_two = self.client.get(f'/search?q={term}&page=2')
            self.assertEqual(page_two.status_code, 200)
            self.assertIn(b'Page 2 of 2', page_two.data)
            self.assertIn(b'test-search-page-11', page_two.data)
        finally:
            for memory in created:
                session.delete(memory)
            session.commit()

    def test_compare_returns_rows_for_selected_cho(self):
        cho = CHO(custom_id='CHO-COMPARE', title='Compare CHO')
        memory = Memory(
            custom_id='test-compare-memory',
            title='Compare memory',
            text='This is <dc:title cho="CHO-COMPARE">linked value</dc:title> text',
            file_path='demo.txt'
        )
        session.add(cho)
        session.add(memory)
        session.commit()
        session.refresh(memory)

        try:
            response = self.client.get('/compare?cho_id=CHO-COMPARE')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'test-compare-memory', response.data)
            self.assertIn(b'linked value', response.data)
        finally:
            session.delete(memory)
            session.delete(cho)
            session.commit()

    def test_compare_field_labels_include_tooltips(self):
        cho = CHO(custom_id='CHO-COMPARE-DESC', title='Compare CHO')
        memory = Memory(
            custom_id='test-compare-memory-desc',
            title='Compare memory',
            text='This is <dc:title cho="CHO-COMPARE-DESC">linked value</dc:title> text',
            file_path='demo.txt'
        )
        session.add(cho)
        session.add(memory)
        session.commit()

        try:
            response = self.client.get('/compare?cho_id=CHO-COMPARE-DESC')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'title="The name given to the resource."', response.data)
        finally:
            session.delete(memory)
            session.delete(cho)
            session.commit()

    def test_delete_duplicate_cho_metadata_removes_selected_occurrence(self):
        memory = Memory(
            custom_id='test-delete-duplicate-cho-md',
            title='Duplicate CHO metadata',
            text='Before <dc:type cho="PR75">first</dc:type> and <dc:type cho="PR75">second</dc:type> after',
            file_path='demo.txt'
        )
        session.add(memory)
        session.commit()
        session.refresh(memory)

        try:
            response = self.client.post(
                f'/memories/{memory.id}/edit',
                data={
                    'title': 'Duplicate CHO metadata',
                    'delete_cho_metadata[1]': '1',
                },
                follow_redirects=True,
            )
            self.assertEqual(response.status_code, 200)
            updated = session.get(Memory, memory.id)
            self.assertIn('<dc:type cho="PR75">first</dc:type>', updated.text)
            self.assertNotIn('<dc:type cho="PR75">second</dc:type>', updated.text)
        finally:
            session.delete(memory)
            session.commit()

    def test_export_memory_rdf_download(self):
        memory = Memory(
            custom_id='test-export-memory',
            title='Export memory',
            text='=== MEMORY METADATA START ===\n<dc:title type="memory">Export title</dc:title>\n=== MEMORY METADATA END ===\n\nBody text',
            file_path='demo.txt'
        )
        session.add(memory)
        session.commit()
        session.refresh(memory)

        try:
            response = self.client.get(f'/export/memory/{memory.id}.rdf')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'rdf:RDF', response.data)
            self.assertIn(b'Export title', response.data)
        finally:
            session.delete(memory)
            session.commit()

    def test_export_cho_rdf_single_download(self):
        cho = CHO(custom_id='CHO-EXPORT', title='Export CHO')
        memory = Memory(
            custom_id='test-export-cho-memory',
            title='Export CHO memory',
            text='Some <dc:title cho="CHO-EXPORT">artifact</dc:title> record',
            file_path='demo.txt'
        )
        session.add(cho)
        session.add(memory)
        session.commit()
        session.refresh(memory)

        try:
            response = self.client.get(f'/export/cho?cho_id=CHO-EXPORT&mode=single&memory_id={memory.id}')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'rdf:RDF', response.data)
            self.assertIn(b'CHO-EXPORT', response.data)
            self.assertIn(b'artifact', response.data)
        finally:
            session.delete(memory)
            session.delete(cho)
            session.commit()

    def test_create_and_delete_cho(self):
        response = self.client.post(
            '/chos/create',
            data={'custom_id': 'CHO-CRUD', 'title': 'Created CHO'},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)

        cho = session.query(CHO).filter(CHO.custom_id == 'CHO-CRUD').first()
        self.assertIsNotNone(cho)

        try:
            delete_response = self.client.post(
                f'/chos/{cho.id}/delete',
                follow_redirects=True,
            )
            self.assertEqual(delete_response.status_code, 200)
            self.assertIsNone(session.get(CHO, cho.id))
        finally:
            stale = session.query(CHO).filter(CHO.custom_id == 'CHO-CRUD').first()
            if stale is not None:
                session.delete(stale)
                session.commit()

    def test_delete_memory_route(self):
        memory = Memory(
            custom_id='test-delete-memory-route',
            title='Delete me',
            text='Body',
            file_path='demo.txt'
        )
        session.add(memory)
        session.commit()
        session.refresh(memory)

        response = self.client.post(f'/memories/{memory.id}/delete', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Deleted memory', response.data)
        self.assertIsNone(session.get(Memory, memory.id))

    def test_import_memory_accepts_txt_only(self):
        valid_id = 'test-import-txt'
        invalid_id = 'test-import-invalid'

        prepare_response = self.client.post(
            '/memories/import',
            data={
                'stage': 'prepare',
                'id': valid_id,
                'file': (io.BytesIO(b'This is valid txt content'), 'memory.txt'),
            },
            content_type='multipart/form-data',
            follow_redirects=True,
        )
        self.assertEqual(prepare_response.status_code, 200)

        temp_path_match = re.search(rb'name="temp_path" value="([^"]+)"', prepare_response.data)
        self.assertIsNotNone(temp_path_match)
        temp_path = temp_path_match.group(1).decode('utf-8')

        valid_response = self.client.post(
            '/memories/import',
            data={
                'stage': 'confirm',
                'temp_path': temp_path,
                'id': valid_id,
                'dc:title': 'Imported title',
            },
            follow_redirects=True,
        )
        self.assertEqual(valid_response.status_code, 200)

        imported = session.query(Memory).filter(Memory.custom_id == valid_id).first()
        self.assertIsNotNone(imported)
        self.assertTrue(imported.file_path.endswith('.txt'))
        self.assertTrue(os.path.exists(imported.file_path))

        try:
            invalid_response = self.client.post(
                '/memories/import',
                data={
                    'stage': 'prepare',
                    'id': invalid_id,
                    'dc:title': 'Invalid ext',
                    'file': (io.BytesIO(b'Not txt'), 'memory.md'),
                },
                content_type='multipart/form-data',
                follow_redirects=True,
            )
            self.assertEqual(invalid_response.status_code, 200)
            invalid = session.query(Memory).filter(Memory.custom_id == invalid_id).first()
            self.assertIsNone(invalid)
        finally:
            imported_now = session.query(Memory).filter(Memory.custom_id == valid_id).first()
            if imported_now is not None:
                if imported_now.file_path and os.path.exists(imported_now.file_path):
                    os.remove(imported_now.file_path)
                session.delete(imported_now)
                session.commit()

    def test_import_preserves_existing_memory_metadata_block(self):
        memory_id = 'test-import-preserve-md'
        existing_text = (
            '=== MEMORY METADATA START ===\n'
            '<dc:title type="memory">Existing title</dc:title>\n'
            '<dc:creator type="memory">Existing creator</dc:creator>\n'
            '=== MEMORY METADATA END ===\n\n'
            'Body content here.'
        )

        prepare_response = self.client.post(
            '/memories/import',
            data={
                'stage': 'prepare',
                'id': memory_id,
                'file': (io.BytesIO(existing_text.encode('utf-8')), 'memory.txt'),
            },
            content_type='multipart/form-data',
            follow_redirects=True,
        )
        self.assertEqual(prepare_response.status_code, 200)
        self.assertIn(b'Existing title', prepare_response.data)

        temp_path_match = re.search(rb'name="temp_path" value="([^"]+)"', prepare_response.data)
        self.assertIsNotNone(temp_path_match)
        temp_path = temp_path_match.group(1).decode('utf-8')

        response = self.client.post(
            '/memories/import',
            data={
                'stage': 'confirm',
                'temp_path': temp_path,
                'id': memory_id,
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)

        imported = session.query(Memory).filter(Memory.custom_id == memory_id).first()
        self.assertIsNotNone(imported)

        try:
            self.assertIn('<dc:title type="memory">Existing title</dc:title>', imported.text)
            self.assertIn('<dc:creator type="memory">Existing creator</dc:creator>', imported.text)
            self.assertIn(b'Preserved 2 existing memory metadata fields', response.data)
            self.assertTrue(imported.file_path.endswith('.txt'))
            self.assertTrue(os.path.exists(imported.file_path))
        finally:
            imported_now = session.query(Memory).filter(Memory.custom_id == memory_id).first()
            if imported_now is not None:
                if imported_now.file_path and os.path.exists(imported_now.file_path):
                    os.remove(imported_now.file_path)
                session.delete(imported_now)
                session.commit()

    def test_import_memory_retrieves_identifier_and_license_from_preamble(self):
        memory_id = 'imported-memory-7'
        existing_text = (
            '=== MEMORY METADATA START ===\n'
            f'<dc:identifier type="memory">{memory_id}</dc:identifier>\n'
            '<dc:license type="memory">CC BY-SA</dc:license>\n'
            '<dc:title type="memory">Imported title</dc:title>\n'
            '=== MEMORY METADATA END ===\n\n'
            'Body text'
        )

        prepare_response = self.client.post(
            '/memories/import',
            data={
                'stage': 'prepare',
                'id': '',
                'file': (io.BytesIO(existing_text.encode('utf-8')), 'memory.txt'),
            },
            content_type='multipart/form-data',
            follow_redirects=True,
        )
        self.assertEqual(prepare_response.status_code, 200)
        self.assertIn(b'Imported title', prepare_response.data)

        temp_path_match = re.search(rb'name="temp_path" value="([^"]+)"', prepare_response.data)
        self.assertIsNotNone(temp_path_match)
        temp_path = temp_path_match.group(1).decode('utf-8')

        response = self.client.post(
            '/memories/import',
            data={
                'stage': 'confirm',
                'temp_path': temp_path,
                'id': '',
                'dc:title': 'Imported title',
                'dc:creator': '',
                'dc:date': '',
                'dc:subject': '',
                'dc:description': '',
                'dc:license': '',
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)

        imported = session.query(Memory).filter(Memory.custom_id == memory_id).first()
        self.assertIsNotNone(imported)

        try:
            self.assertEqual(imported.license, 'CC BY-SA')
            self.assertIn('<dc:identifier type="memory">imported-memory-7</dc:identifier>', imported.text)
            self.assertIn('<dc:license type="memory">CC BY-SA</dc:license>', imported.text)
        finally:
            if imported is not None:
                if imported.file_path and os.path.exists(imported.file_path):
                    os.remove(imported.file_path)
                session.delete(imported)
                session.commit()

    def test_delete_cho_metadata_does_not_duplicate_text(self):
        memory = Memory(
            custom_id='test-delete-cho-md',
            title='Delete CHO metadata',
            text='Before <dc:title cho="PR75">watch</dc:title> after',
            file_path='demo.txt'
        )
        session.add(memory)
        session.commit()
        session.refresh(memory)

        try:
            response = self.client.post(
                f'/memories/{memory.id}/edit',
                data={
                    'title': 'Delete CHO metadata',
                    'text': 'Before <dc:title cho="PR75">watch</dc:title> after',
                    'delete_cho_metadata[PR75][dc:title]': '1',
                    'cho_metadata[PR75][dc:title]': 'watch',
                },
                follow_redirects=True,
            )
            self.assertEqual(response.status_code, 200)
            updated = session.get(Memory, memory.id)
            self.assertNotIn('<dc:title cho="PR75">', updated.text)
            self.assertEqual(updated.text.count('watch'), 1)
        finally:
            session.delete(memory)
            session.commit()

    def test_save_memory_license_updates_preamble_and_database(self):
        memory = Memory(
            custom_id='test-memory-license-save',
            title='License test',
            text='Body text only',
            file_path='demo.txt',
            license='CC BY'
        )
        session.add(memory)
        session.commit()
        session.refresh(memory)

        try:
            response = self.client.post(
                f'/memories/{memory.id}/edit',
                data={
                    'title': 'License test',
                    'text': 'Body text only',
                    'memory_license': 'CC BY-SA 3.0 IGO',
                    'save_memory_license': '1',
                },
                follow_redirects=True,
            )
            self.assertEqual(response.status_code, 200)

            updated = session.get(Memory, memory.id)
            self.assertEqual(updated.license, 'CC BY-SA 3.0 IGO')
            self.assertIn('<dc:identifier type="memory">test-memory-license-save</dc:identifier>', updated.text)
            self.assertIn('<dc:license type="memory">CC BY-SA 3.0 IGO</dc:license>', updated.text)
        finally:
            session.delete(memory)
            session.commit()


if __name__ == '__main__':
    unittest.main()
