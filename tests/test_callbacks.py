from utils.callbacks import SelectTestCB, ViewTestCB, SessionEditCB, TestOptionCB


def test_callbackdata_roundtrip():
    s = SelectTestCB(test_id=123).pack()
    parsed = SelectTestCB.unpack(s).model_dump()
    # now typed: test_id should be int
    assert parsed["test_id"] == 123

    v = ViewTestCB(test_id=42).pack()
    assert ViewTestCB.unpack(v).model_dump()["test_id"] == 42

    sess = SessionEditCB(test_id=5, field="title").pack()
    p = SessionEditCB.unpack(sess).model_dump()
    assert p["test_id"] == 5 and p["field"] == "title"

    opt = TestOptionCB(test_id=2, option="Hello").pack()
    po = TestOptionCB.unpack(opt).model_dump()
    assert po["test_id"] == 2 and po["option"] == "Hello"