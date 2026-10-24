import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from db import init_db
from main import Job, app, engine

client = TestClient(app)


def _insert(**fields):
    job_id = uuid.uuid4().hex
    with Session(engine) as s:
        s.add(Job(id=job_id, **fields))
        s.commit()
    return job_id


def _delete(job_id):
    with Session(engine) as s:
        job = s.get(Job, job_id)
        if job:
            s.delete(job)
            s.commit()


def test_finished_job_survives_restart():
    result = [{"category": "penalty", "severity": "high",
               "quote": "q", "explanation": "e"}]
    job_id = _insert(status="done", done=1, total=1, result=result)
    try:
        init_db()  # simulira restart servera
        r = client.get(f"/jobs/{job_id}")
        assert r.status_code == 200
        assert r.json()["status"] == "done"
        assert r.json()["result"] == result
    finally:
        _delete(job_id)


def test_interrupted_job_becomes_error_on_restart():
    job_id = _insert(status="running", done=1, total=5)
    try:
        init_db()
        r = client.get(f"/jobs/{job_id}")
        assert r.status_code == 200
        assert r.json()["status"] == "error"
        assert r.json()["error"]
    finally:
        _delete(job_id)


def test_unknown_job_returns_404():
    assert client.get("/jobs/does-not-exist").status_code == 404