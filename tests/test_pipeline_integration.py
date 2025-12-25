import time
from pathlib import Path
import json

from data_pipeline.views.mvb_view import MVBView
from data_pipeline.validators.schema import RequestSchema

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def load_requests():
    return json.loads((DATA_DIR / "sample_request_cases.json").read_text(encoding="utf-8"))


def test_end_to_end_parse_and_download_roundtrip():
    view = MVBView(DATA_DIR)
    cases = load_requests()
    req = RequestSchema.parse_obj(cases[0])

    t0 = time.time()
    parsed = view.parse(req)
    parsed_dur = time.time() - t0

    assert parsed["meta"]["frames_parsed"] >= 0

    t0 = time.time()
    csv = view.download(req)
    dl_dur = time.time() - t0

    assert b"idx,speed,temp" in csv["bytes"]
    # basic perf expectations for small placeholder data
    assert parsed_dur < 1.0
    assert dl_dur < 1.0
