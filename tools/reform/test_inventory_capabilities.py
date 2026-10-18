import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("inventory", Path(__file__).with_name("inventory_capabilities.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class InventoryTests(unittest.TestCase):
    def test_routes_are_read_without_importing_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); p = root / "app.py"
            p.write_text('raise RuntimeError("must not import")\n@app.get("/items")\ndef read(): pass\n@app.api_route("/items", methods=["PUT", "PATCH"])\ndef edit(): pass\n')
            data = m.inspect_python(p, root)
            self.assertEqual({x['method'] for x in data['routes']}, {'GET','PUT','PATCH'})
            self.assertEqual(data['parse_errors'], [])

    def test_tool_registration_is_not_execution_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); p = root / "app.py"
            p.write_text('TOOLS=(ToolDescriptor(Action.SEARCH,"search",False,False,False),)\ndef f(): return [_tool("search","desc",{},[])]\n')
            data = m.inspect_python(p, root)
            self.assertEqual(data['registered_tools'][0]['name'], 'search')
            self.assertIs(data['registered_tools'][0]['changes_money'], False)
            self.assertEqual(data['model_tools'][0]['name'], 'search')

    def test_dynamic_route_is_not_fabricated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); p = root / "app.py"
            p.write_text('@app.get(prefix + "/x")\ndef dynamic(): pass\n')
            self.assertEqual(m.inspect_python(p, root)['routes'], [])

    def test_parse_error_is_reported_not_silenced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); p = root / "bad.py"; p.write_text('def broken(')
            self.assertEqual(m.inspect_python(p, root)['parse_errors'][0]['error_type'], 'SyntaxError')

    def test_missing_domains_are_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = m.collect(Path(tmp))
            self.assertEqual(data['domains']['agent']['source_paths_present'], [])
            self.assertEqual(data['domains']['agent']['live_validation'], 'NOT_PERFORMED')

if __name__ == '__main__': unittest.main()
