import unittest

from db import Memory, session
from web_app import create_app


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    def test_index_page_loads(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'CORDHISK', response.data)

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

            updated = session.query(Memory).get(memory.id)
            self.assertEqual(updated.title, 'Updated title')
            self.assertEqual(updated.text, 'Updated body')
        finally:
            session.delete(memory)
            session.commit()

    def test_graph_page_loads(self):
        response = self.client.get('/graph')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Memory relationship graph', response.data)
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
            updated = session.query(Memory).get(memory.id)
            self.assertIn('updated watch', updated.text)
        finally:
            session.delete(memory)
            session.commit()

    def test_graph_page_includes_metadata_nodes(self):
        response = self.client.get('/graph')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'graph-node', response.data.lower())
        self.assertIn(b'metadata-hidden', response.data.lower())

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
            updated = session.query(Memory).get(memory.id)
            self.assertNotIn('type="memory"', updated.text)
            self.assertIn('watch', updated.text)
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
            updated = session.query(Memory).get(memory.id)
            self.assertIn('<dc:title cho="PR75">selected phrase</dc:title>', updated.text)
        finally:
            session.delete(memory)
            session.commit()


if __name__ == '__main__':
    unittest.main()
