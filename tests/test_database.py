import os
import tempfile
import json
from utils.database import Database

def test_add_get_update_delete_test():
    db_file = tempfile.NamedTemporaryFile(delete=False).name
    db = Database(db_file)

    # add test
    options = {"A": "Result A", "B": "Result B"}
    test_id = db.add_test("Title", "text", "Some text", None, None, "Question?", options)
    assert isinstance(test_id, int)

    t = db.get_test(test_id)
    assert t[1] == "Title"
    opts = json.loads(t[7])
    assert opts == options

    # update
    db.update_test(test_id, title="New Title", question_text="New Q")
    t2 = db.get_test(test_id)
    assert t2[1] == "New Title"
    assert t2[6] == "New Q"

    # delete (soft)
    db.delete_test(test_id)
    # get_all_tests should not include it
    all_tests = db.get_all_tests()
    assert all(t[0] != test_id for t in all_tests)

    os.unlink(db_file)