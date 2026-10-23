"""End-to-end check on the bundled sample: before set, after shots, follow-ups, signed report, verification."""
import os
import tempfile

os.environ["TWICE_DATA"] = tempfile.mkdtemp()

from fastapi.testclient import TestClient  # noqa: E402

from twice.app import app  # noqa: E402

client = TestClient(app)


def run_sample() -> dict:
    check = client.post("/api/samples/apartment").json()
    cid = check["id"]
    for spot in check["spots"]:
        url = f"/api/checks/{cid}/spots/{spot['id']}/sample-shot"
        state = client.post(url).json()["state"]
        for _ in range(3):
            if state["status"] == "done":
                break
            state = client.post(url).json()["state"]
        assert state["status"] == "done", state["trace"]
    report = client.post(f"/api/checks/{cid}/report")
    assert report.status_code == 200, report.text
    return report.json()


def test_sample_flow_finds_damage_and_rules_out_glare():
    check = run_sample()
    verdicts = {s["label"]: [(f["verdict"], f["kind"]) for f in s["state"]["findings"]] for s in check["spots"]}
    car = verdicts["Rental car, front quarter panel"]
    assert ("lighting", "glare") in car, car
    assert sum(v == "changed" for v, _ in car) == 1, car
    room = verdicts["Living room, east wall"]
    assert sum(v == "changed" for v, _ in room) >= 2, room
    assert [s["phase"] for s in check["seals"]] == ["before", "report"]

    v = client.get(f"/api/checks/{check['id']}/verify").json()
    assert v["ok"], v


def test_tampered_file_fails_verification():
    from twice.app import store

    check = run_sample()
    key = check["spots"][0]["after"]["key"]
    store.put(key, store.get(key) + b"\0")
    v = client.get(f"/api/checks/{check['id']}/verify").json()
    assert not v["ok"]
    assert [f for f in v["files"] if not f["ok"]][0]["role"] == "after"


def test_rejects_non_images():
    cid = client.post("/api/checks", json={"name": "x"}).json()["id"]
    r = client.post(f"/api/checks/{cid}/spots", files={"file": ("a.jpg", b"not an image", "image/jpeg")})
    assert r.status_code == 415


def test_swapped_photo_with_rewritten_record_fails_verification():
    from twice import evidence
    from twice.app import load, save, store

    check = run_sample()
    record = load(check["id"])
    after = record["spots"][0]["after"]
    fake = store.get(after["key"]) + b"edited"
    store.put(after["key"], fake)
    after["sha256"] = evidence.sha256(fake)
    save(record)
    v = client.get(f"/api/checks/{check['id']}/verify").json()
    assert not v["ok"]


def test_signed_photo_moved_to_another_role_fails_verification():
    from twice.app import load, save

    check = run_sample()
    record = load(check["id"])
    spot = record["spots"][0]
    spot["after"] = {**spot["after"], "sha256": spot["before"]["sha256"], "key": spot["before"]["key"]}
    save(record)
    v = client.get(f"/api/checks/{check['id']}/verify").json()
    assert not v["ok"]


def test_photos_rejected_after_report_and_before_seal():
    check = run_sample()
    url = f"/api/checks/{check['id']}/spots/{check['spots'][0]['id']}/sample-shot"
    assert client.post(url).status_code == 409
    cid = client.post("/api/checks", json={"name": "x"}).json()["id"]
    with open("../web/public/hero/room-a.jpg", "rb") as f:
        sid = client.post(f"/api/checks/{cid}/spots", files={"file": ("a.jpg", f.read(), "image/jpeg")}).json()["id"]
    with open("../web/public/hero/room-b.jpg", "rb") as f:
        r = client.post(f"/api/checks/{cid}/spots/{sid}/after", files={"file": ("b.jpg", f.read(), "image/jpeg")})
    assert r.status_code == 409
