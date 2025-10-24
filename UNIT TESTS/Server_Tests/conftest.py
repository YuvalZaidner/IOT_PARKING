import sys
import os
import pytest
from unittest.mock import MagicMock

# Make project root importable so tests can `import event_generator` etc.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


@pytest.fixture
def firebase_db_mock(monkeypatch):
    """Provide a mock for firebase_admin.db.reference used by event_generator.

    Returns a factory that when called with a path returns a MagicMock with
    .child(...).set and .child(...).update methods. Tests can inspect calls if needed.
    """
    # Create a registry of mocks per path so tests can inspect calls
    registry = {}

    def make_child_mock(child_name):
        cm = MagicMock(name=f"child({child_name})")
        # ensure set/update exist
        cm.set = MagicMock()
        cm.update = MagicMock()
        return cm

    def fake_reference(path=None):
        key = path or ''
        if key in registry:
            return registry[key]['ref']

        # create a new ref mock with its own child registry
        ref = MagicMock(name=f"db_ref({key})")
        child_registry = {}

        def child(name):
            if name in child_registry:
                return child_registry[name]
            cm = make_child_mock(name)
            child_registry[name] = cm
            return cm

        ref.child.side_effect = child
        registry[key] = {'ref': ref, 'children': child_registry}
        return ref

    # monkeypatch the db.reference symbol where event_generator imports it from
    try:
        # import here to avoid hard dependency if firebase_admin isn't installed
        from firebase_admin import db
        monkeypatch.setattr(db, 'reference', fake_reference)
    except Exception:
        # if firebase_admin isn't available in the environment, create a fake module path
        fake_db = MagicMock()
        fake_db.reference = fake_reference
        monkeypatch.setitem(__import__('sys').modules, 'firebase_admin.db', fake_db)

    # expose the registry for introspection in tests
    fake_reference._registry = registry
    return fake_reference