from utils.callbacks import select_test_cb, view_test_cb, session_edit_cb, test_option_cb

def test_callbackdata_roundtrip():
    s = select_test_cb.new(test_id=123)
    parsed = select_test_cb.parse(s)
    assert parsed["test_id"] == "123"

    v = view_test_cb.new(test_id=42)
    assert view_test_cb.parse(v)["test_id"] == "42"

    sess = session_edit_cb.new(test_id=5, field="title")
    p = session_edit_cb.parse(sess)
    assert p["test_id"] == "5" and p["field"] == "title"

    opt = test_option_cb.new(test_id=2, option="Hello")
    po = test_option_cb.parse(opt)
    assert po["test_id"] == "2" and po["option"] == "Hello"