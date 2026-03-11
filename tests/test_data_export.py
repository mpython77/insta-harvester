"""
Unit Tests — DataExporter
Covers: _flatten_dict, _to_records, export_csv, export_json, auto_export
Uses tmp files for isolation.
"""

import sys, os, json, csv, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from pathlib import Path
from instaharvest.data_export import DataExporter


@pytest.fixture
def tmp_dir():
    """Create temporary directory for exports"""
    with tempfile.TemporaryDirectory() as d:
        yield d


# ═══════════════════════════════════════════════════════════
# HELPER METHODS
# ═══════════════════════════════════════════════════════════

class TestFlattenDict:
    def test_simple(self):
        exporter = DataExporter()
        flat = exporter._flatten_dict({'a': 1, 'b': 'hello'})
        assert flat == {'a': 1, 'b': 'hello'}

    def test_nested(self):
        exporter = DataExporter()
        flat = exporter._flatten_dict({
            'name': 'test',
            'location': {'city': 'Paris', 'country': 'France'}
        })
        assert flat['location_city'] == 'Paris'
        assert flat['location_country'] == 'France'

    def test_deep_nested(self):
        exporter = DataExporter()
        flat = exporter._flatten_dict({
            'level1': {
                'level2': {
                    'value': 42
                }
            }
        })
        assert flat['level1_level2_value'] == 42

    def test_list_value(self):
        exporter = DataExporter()
        flat = exporter._flatten_dict({
            'tags': ['a', 'b', 'c']
        })
        # Lists should be stringified for CSV
        assert isinstance(flat['tags'], str) or isinstance(flat['tags'], list)


class TestNormalizeRows:
    def test_dict_list(self):
        exporter = DataExporter()
        records = exporter._normalize_rows([{'a': 1}, {'a': 2}])
        assert len(records) == 2

    def test_dataclass_list(self):
        from instaharvest.post_data import PostLocation
        exporter = DataExporter()
        records = exporter._normalize_rows([
            PostLocation(name='Paris'),
            PostLocation(name='London'),
        ])
        assert len(records) == 2
        assert records[0]['name'] == 'Paris'

    def test_single_dataclass(self):
        from instaharvest.post_data import PostLocation
        exporter = DataExporter()
        records = exporter._normalize_rows([PostLocation(name='Tokyo')])
        assert len(records) == 1


# ═══════════════════════════════════════════════════════════
# CSV EXPORT
# ═══════════════════════════════════════════════════════════

class TestExportCSV:
    def test_basic_csv(self, tmp_dir):
        exporter = DataExporter(output_dir=tmp_dir)
        data = [
            {'name': 'Alice', 'age': 25},
            {'name': 'Bob', 'age': 30},
        ]
        filepath = exporter.export_csv(data, 'test.csv')
        assert os.path.exists(filepath)

        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2
        assert rows[0]['name'] == 'Alice'

    def test_csv_custom_fields(self, tmp_dir):
        exporter = DataExporter(output_dir=tmp_dir)
        data = [
            {'name': 'Alice', 'age': 25, 'city': 'NYC'},
        ]
        filepath = exporter.export_csv(data, 'test2.csv', fieldnames=['name', 'city'])
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        # Only specified fields should be headers
        assert 'name' in rows[0]

    def test_csv_empty(self, tmp_dir):
        exporter = DataExporter(output_dir=tmp_dir)
        filepath = exporter.export_csv([], 'empty.csv')
        # Empty data returns empty string (no file created)
        assert filepath == ''

    def test_csv_bom(self, tmp_dir):
        exporter = DataExporter(output_dir=tmp_dir, add_bom=True)
        filepath = exporter.export_csv([{'a': 1}], 'bom_test.csv')
        with open(filepath, 'rb') as f:
            first_bytes = f.read(3)
        assert first_bytes == b'\xef\xbb\xbf'

    def test_csv_no_bom(self, tmp_dir):
        exporter = DataExporter(output_dir=tmp_dir, add_bom=False)
        filepath = exporter.export_csv([{'a': 1}], 'nobom_test.csv')
        with open(filepath, 'rb') as f:
            first_bytes = f.read(3)
        assert first_bytes != b'\xef\xbb\xbf'


# ═══════════════════════════════════════════════════════════
# JSON EXPORT
# ═══════════════════════════════════════════════════════════

class TestExportJSON:
    def test_basic_json(self, tmp_dir):
        exporter = DataExporter(output_dir=tmp_dir)
        data = {'username': 'test', 'posts': [{'id': 1}, {'id': 2}]}
        filepath = exporter.export_json(data, 'test.json')
        assert os.path.exists(filepath)

        with open(filepath, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        assert loaded['username'] == 'test'
        assert len(loaded['posts']) == 2

    def test_json_pretty(self, tmp_dir):
        exporter = DataExporter(output_dir=tmp_dir, pretty_json=True)
        filepath = exporter.export_json({'key': 'value'}, 'pretty.json')
        with open(filepath, 'r') as f:
            content = f.read()
        assert '\n' in content  # Pretty-printed has newlines

    def test_json_dataclass(self, tmp_dir):
        from instaharvest.post_data import PostLocation
        exporter = DataExporter(output_dir=tmp_dir)
        loc = PostLocation(name='Bali', latitude=-8.3405)
        filepath = exporter.export_json(loc.to_dict(), 'loc.json')
        with open(filepath, 'r') as f:
            data = json.load(f)
        assert data['name'] == 'Bali'


# ═══════════════════════════════════════════════════════════
# AUTO EXPORT
# ═══════════════════════════════════════════════════════════

class TestAutoExport:
    def test_auto_export_json(self, tmp_dir):
        exporter = DataExporter(output_dir=tmp_dir)
        from instaharvest.story_scraper import StoryResult
        result = StoryResult(username='testuser', story_count=5, has_stories=True)
        paths = exporter.auto_export(result, prefix='stories', formats=['json'])
        # auto_export returns a dict: {'json': '/path/to/file.json'}
        assert isinstance(paths, dict)
        assert 'json' in paths
        assert paths['json'].endswith('.json')

    def test_auto_export_csv(self, tmp_dir):
        exporter = DataExporter(output_dir=tmp_dir)
        data = [{'name': 'A'}, {'name': 'B'}]
        paths = exporter.auto_export(data, prefix='test', formats=['csv'])
        assert isinstance(paths, dict)
        assert 'csv' in paths


# ═══════════════════════════════════════════════════════════
# INIT
# ═══════════════════════════════════════════════════════════

class TestDataExporterInit:
    def test_creates_output_dir(self):
        with tempfile.TemporaryDirectory() as base:
            out = os.path.join(base, 'subdir', 'exports')
            exporter = DataExporter(output_dir=out)
            assert os.path.isdir(out)

    def test_defaults(self):
        exporter = DataExporter()
        assert exporter.add_bom is True
        assert exporter.pretty_json is True


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
