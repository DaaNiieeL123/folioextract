from pathlib import Path

from backend.app.infrastructure.job_store import FileJobStore


def test_file_job_store_persists_lifecycle(tmp_path: Path):
    store_path = tmp_path / "jobs.json"
    store = FileJobStore(store_path)

    store.create_job(
        job_id="job_1",
        total=2,
        extension=".md",
        output_dir=str(tmp_path),
        files=["a.pdf", "b.pdf"],
    )
    store.update_progress(job_id="job_1", current=1, filename="a.pdf", is_error=False, error_msg=None)
    store.update_progress(job_id="job_1", current=2, filename="b.pdf", is_error=True, error_msg="fail")
    store.complete_job(job_id="job_1", successes=1, errors=1, elapsed_ms=123.45)

    reloaded = FileJobStore(store_path)
    job = reloaded.get_job("job_1")

    assert job is not None
    assert job["status"] == "completed"
    assert job["successes"] == 1
    assert job["errors"] == 1
    assert job["last_file"] == "b.pdf"
    assert job["last_error"] == "fail"
    assert isinstance(job["elapsed_ms"], float)
    assert job["source_paths"] == ["a.pdf", "b.pdf"]
    assert len(job["file_items"]) == 2
    assert job["file_items"][0]["filename"] == "a.pdf"
    assert job["file_items"][0]["source_path"] == "a.pdf"
    assert job["file_items"][0]["status"] == "completed"
    assert job["file_items"][1]["status"] == "failed"
    assert job["file_items"][1]["error"] == "fail"


def test_file_job_store_list_limit(tmp_path: Path):
    store = FileJobStore(tmp_path / "jobs.json")
    for idx in range(5):
        store.create_job(
            job_id=f"job_{idx}",
            total=1,
            extension=".txt",
            output_dir=str(tmp_path),
            files=["x.pdf"],
        )

    jobs = store.list_jobs(limit=3)
    assert len(jobs) == 3


def test_file_job_store_marks_unfinished_jobs_as_interrupted(tmp_path: Path):
    store = FileJobStore(tmp_path / "jobs.json")
    store.create_job(
        job_id="job_running",
        total=1,
        extension=".md",
        output_dir=str(tmp_path),
        files=["x.pdf"],
        status="running",
    )

    changed = store.mark_interrupted_unfinished()
    job = store.get_job("job_running")

    assert changed == 1
    assert job is not None
    assert job["status"] == "interrupted"
    assert job["file_items"][0]["status"] == "interrupted"


def test_file_job_store_returns_retryable_sources(tmp_path: Path):
    store = FileJobStore(tmp_path / "jobs.json")
    source_path = str(tmp_path / "retry.pdf")
    store.create_job(
        job_id="job_retry",
        total=1,
        extension=".md",
        output_dir=str(tmp_path),
        files=["retry.pdf"],
        source_paths=[source_path],
        status="failed",
    )
    store.complete_job(job_id="job_retry", successes=0, errors=1, elapsed_ms=1.0, status="failed")

    retryable = store.get_retryable_sources("job_retry")
    assert retryable == [source_path]


