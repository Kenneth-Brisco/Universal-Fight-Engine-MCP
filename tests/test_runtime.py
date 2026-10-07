"""Freshness acceptance tests with original fixtures and no live crawling."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import multiprocessing
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest import mock

from ufe_docs_mcp import index as index_module
from ufe_docs_mcp import runtime as runtime_module
from ufe_docs_mcp.index import (
    Document,
    build_index,
    get_doc,
    index_status,
    list_topics,
    search_docs,
    snapshot_from_status,
)
from ufe_docs_mcp.runtime import DocumentationRuntime, sync_cache


NOW = datetime(2026, 10, 7, 12, tzinfo=timezone.utc).timestamp()
DAY = 24 * 60 * 60
DOC_ID = "synthetic.sparrow.guide"


def _iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def _document(revision: str = "old", *, warnings: tuple[str, ...] = ()) -> Document:
    return Document(
        doc_id=DOC_ID,
        title="Synthetic sparrow guide",
        url="https://example.invalid/manual/#/synthetic:sparrow:guide",
        content=(
            "# Synthetic sparrow guide\n"
            f"This wholly invented sparrow fixture has the {revision} revision.\n"
            "## Practice cue\n"
            "Follow the paper moon for this fictional practice sequence.\n"
        ),
        category="Synthetic documentation",
        warnings=warnings,
    )


def _metadata(timestamp: float, *, raw_pages: bool = False) -> dict:
    return {
        "fixture": "original synthetic documentation",
        "fetched_at": _iso(timestamp),
        "content_mode": "raw_pages" if raw_pages else "published_catalog",
        "catalog_generated_at": "2026-07-31T00:00:00+00:00",
    }


class FakeClock:
    def __init__(self, now: float = NOW):
        self.now = now

    def __call__(self) -> float:
        return self.now


def _process_sync(cache_dir, started, release, call_count, results, name, now):
    """A separate interpreter owns its own mocked source and real cache lock."""
    def fetch(**kwargs):
        with call_count.get_lock():
            call_count.value += 1
        started.set()
        if not release.wait(10):
            raise RuntimeError("Synthetic process fetch was never released")
        return [_document("new")], _metadata(now, raw_pages=kwargs.get("refresh_pages", False))

    try:
        with mock.patch("ufe_docs_mcp.runtime.fetch_official_documents", side_effect=fetch):
            result = sync_cache(Path(cache_dir), automatic=True, clock=lambda: now)
        results.put((name, {"result": result}))
    except Exception as error:
        # A documented nonblocking RefreshBusy exception is also an acceptable
        # coordinator response; actual fetch/build failures remain test failures.
        results.put((name, {"error_type": type(error).__name__, "error": str(error)}))


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="ufe-runtime-fixture-")
        self.addCleanup(self.directory.cleanup)
        self.cache = Path(self.directory.name)
        self.path = self.cache / "docs.sqlite3"
        self.clock = FakeClock()

    def _seed(self, *, cache=None, age=DAY + 1, raw_pages=False, document=None):
        cache = self.cache if cache is None else Path(cache)
        build_index(
            [document or _document()],
            cache / "docs.sqlite3",
            _metadata(self.clock() - age, raw_pages=raw_pages),
        )
        return index_status(cache / "docs.sqlite3")

    def _runtime(self, *, cache=None, **kwargs):
        runtime = DocumentationRuntime(
            self.cache if cache is None else cache, clock=self.clock, **kwargs
        )
        self.addCleanup(runtime.close)
        return runtime

    def _finish_worker(self, runtime):
        worker = runtime._thread
        if worker is not None:
            worker.join(timeout=5)
            self.assertFalse(worker.is_alive(), "Synthetic refresh did not finish")
        self.assertNotEqual(runtime.status()["freshness"]["state"], "refreshing")

    def _fetched_documents(self, **kwargs):
        return [_document("new")], _metadata(
            self.clock(), raw_pages=kwargs.get("refresh_pages", False)
        )

    def test_fresh_cache_does_not_fetch_and_reports_snapshot_scope(self):
        for raw_pages in (False, True):
            with self.subTest(raw_pages=raw_pages):
                cache = self.cache / ("raw" if raw_pages else "catalog")
                self._seed(cache=cache, age=60 * 60, raw_pages=raw_pages)
                with mock.patch("ufe_docs_mcp.runtime.fetch_official_documents") as fetch:
                    runtime = self._runtime(cache=cache)
                    runtime.bootstrap()
                    runtime.maybe_refresh()
                    runtime.close()
                    fetch.assert_not_called()
                    freshness = runtime.status()["freshness"]
                expected = "current_to_raw_pages" if raw_pages else "current_to_catalog"
                self.assertEqual(freshness["state"], expected)
                self.assertFalse(freshness["check_overdue"])
                self.assertEqual(freshness["snapshot_age_seconds"], 60 * 60)
                self.assertEqual(freshness["refresh_interval_hours"], 24.0)
                self.assertEqual(freshness["snapshot_fetched_at"], _iso(self.clock() - 60 * 60))
                self.assertTrue(freshness["scope"])

    def test_overdue_refresh_keeps_old_cache_readable_until_atomic_publication(self):
        before = self._seed()
        entered = threading.Event()
        release = threading.Event()
        self.addCleanup(release.set)

        def fetch(**kwargs):
            entered.set()
            if not release.wait(5):
                raise RuntimeError("Synthetic blocking fetch was never released")
            return self._fetched_documents(**kwargs)

        with mock.patch("ufe_docs_mcp.runtime.fetch_official_documents", side_effect=fetch) as source:
            runtime = self._runtime()
            try:
                runtime.bootstrap()
                self.assertTrue(entered.wait(2), "Background source fetch did not start")
                during = runtime.status()
                self.assertEqual(during["freshness"]["state"], "refreshing")
                self.assertTrue(during["freshness"]["check_overdue"])
                old = runtime.decorate(get_doc(self.path, DOC_ID))
                self.assertIn("old revision", old["content"])
                self.assertEqual(old["snapshot"]["content_hash"], before["content_hash"])
                self.assertEqual(search_docs(self.path, "sparrow")["results"][0]["doc_id"], DOC_ID)
            finally:
                release.set()
                self._finish_worker(runtime)
            source.assert_called_once()
            after = runtime.decorate(get_doc(self.path, DOC_ID))
            self.assertIn("new revision", after["content"])
            self.assertNotEqual(after["snapshot"]["content_hash"], before["content_hash"])
            self.assertEqual(after["freshness"]["state"], "current_to_catalog")
            self.assertEqual(after["snapshot"]["fetched_at"], _iso(self.clock()))
            self.assertEqual(after["snapshot"]["catalog_generated_at"], "2026-07-31T00:00:00+00:00")

    def test_failed_refresh_preserves_existing_database_and_exposes_error(self):
        self._seed()
        before = self.path.read_bytes()
        with mock.patch(
            "ufe_docs_mcp.runtime.fetch_official_documents",
            side_effect=RuntimeError("Synthetic source failure: unavailable fixture"),
        ):
            runtime = self._runtime()
            runtime.bootstrap()
            self._finish_worker(runtime)
            status = runtime.status()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertTrue(status["available"])
        self.assertEqual(status["freshness"]["state"], "check_failed")
        self.assertIn("Synthetic source failure", status["freshness"]["last_error"])
        self.assertIn("old revision", get_doc(self.path, DOC_ID)["content"])
        state = json.loads((self.cache / "refresh-state.json").read_text())
        self.assertEqual(state["last_outcome"], "failed")
        self.assertTrue(state["last_attempt_at"])
        self.assertTrue(state["last_finished_at"])

    def test_failed_check_retry_delay_survives_new_runtime(self):
        self._seed()
        with mock.patch(
            "ufe_docs_mcp.runtime.fetch_official_documents",
            side_effect=RuntimeError("Synthetic retry failure"),
        ) as fetch:
            first = self._runtime()
            first.bootstrap()
            self._finish_worker(first)
            first.close()
            fetch.assert_called_once()
        self.clock.now += 899
        with mock.patch(
            "ufe_docs_mcp.runtime.fetch_official_documents",
            side_effect=self._fetched_documents,
        ) as fetch:
            reconnected = self._runtime()
            reconnected.bootstrap()
            reconnected.maybe_refresh()
            self._finish_worker(reconnected)
            fetch.assert_not_called()
            self.assertEqual(reconnected.status()["freshness"]["state"], "check_failed")
            self.clock.now += 2
            reconnected.maybe_refresh()
            self._finish_worker(reconnected)
            fetch.assert_called_once()
            self.assertEqual(reconnected.status()["freshness"]["state"], "current_to_catalog")

    def test_idle_scheduler_starts_a_check_when_injected_clock_becomes_due(self):
        self._seed(age=1)
        fetched = threading.Event()

        def fetch(**kwargs):
            fetched.set()
            return self._fetched_documents(**kwargs)

        with mock.patch("ufe_docs_mcp.runtime.SCHEDULER_SECONDS", 0.01), mock.patch(
            "ufe_docs_mcp.runtime.fetch_official_documents", side_effect=fetch
        ) as source:
            runtime = self._runtime()
            runtime.bootstrap()
            source.assert_not_called()
            self.clock.now += DAY
            # No read, status request or maybe_refresh call wakes the runtime.
            # The scheduler must observe that the source check became due.
            self.assertTrue(fetched.wait(2), "Idle scheduler did not start a due check")
            self._finish_worker(runtime)
            runtime.close()
            if runtime._scheduler is not None:
                runtime._scheduler.join(timeout=1)
                self.assertFalse(runtime._scheduler.is_alive())
            source.assert_called_once()
            self.assertFalse(runtime.status()["freshness"]["check_overdue"])

    def test_existing_client_clears_failed_check_after_shared_cache_success(self):
        self._seed()
        runtime = self._runtime()
        with mock.patch(
            "ufe_docs_mcp.runtime.fetch_official_documents",
            side_effect=RuntimeError("Synthetic existing-client failure"),
        ):
            runtime.bootstrap()
            self._finish_worker(runtime)
        self.assertEqual(runtime.status()["freshness"]["state"], "check_failed")
        self.clock.now += 2
        with mock.patch(
            "ufe_docs_mcp.runtime.fetch_official_documents",
            side_effect=self._fetched_documents,
        ):
            # Another client or a CLI process uses the same blocking coordinator.
            sync_cache(self.cache, clock=self.clock)
        status = runtime.status()
        self.assertEqual(status["freshness"]["state"], "current_to_catalog")
        self.assertIsNone(status["freshness"]["last_error"])
        self.assertFalse(status["freshness"]["check_overdue"])
        response = runtime.decorate(get_doc(self.path, DOC_ID))
        self.assertIn("new revision", response["content"])
        self.assertIsNone(response["freshness"]["last_error"])

    def test_missing_malformed_and_future_source_timestamps_are_due(self):
        cases = (
            ("missing", None),
            ("invalid", "not-a-time"),
            ("future", _iso(NOW + DAY)),
            ("near-future", _iso(NOW + 60)),
        )
        for label, timestamp in cases:
            with self.subTest(timestamp=label):
                cache = self.cache / label
                self._seed(cache=cache, age=0)
                path = cache / "docs.sqlite3"
                with sqlite3.connect(path) as connection:
                    state = json.loads(connection.execute("SELECT value FROM index_metadata WHERE key='status'").fetchone()[0])
                    state["indexed_at"] = _iso(NOW)
                    if timestamp is None:
                        state["metadata"].pop("fetched_at", None)
                    else:
                        state["metadata"]["fetched_at"] = timestamp
                    connection.execute("UPDATE index_metadata SET value=? WHERE key='status'", (json.dumps(state),))
                with mock.patch(
                    "ufe_docs_mcp.runtime.fetch_official_documents",
                    side_effect=self._fetched_documents,
                ) as fetch:
                    runtime = self._runtime(cache=cache)
                    self.assertTrue(runtime.status()["freshness"]["check_overdue"])
                    runtime.bootstrap()
                    self._finish_worker(runtime)
                    runtime.close()
                    fetch.assert_called_once()

    def test_missing_and_corrupt_caches_recover_without_blocking_status(self):
        for corrupted in (False, True):
            with self.subTest(corrupted=corrupted):
                cache = self.cache / ("corrupt" if corrupted else "missing")
                cache.mkdir()
                if corrupted:
                    (cache / "docs.sqlite3").write_bytes(b"Not a SQLite database; synthetic corruption.")
                with mock.patch(
                    "ufe_docs_mcp.runtime.fetch_official_documents",
                    side_effect=self._fetched_documents,
                ) as fetch:
                    runtime = self._runtime(cache=cache)
                    self.assertFalse(runtime.status()["available"])
                    self.assertTrue(runtime.status()["freshness"]["check_overdue"])
                    runtime.bootstrap()
                    self._finish_worker(runtime)
                    runtime.close()
                    fetch.assert_called_once()
                    self.assertTrue(runtime.status()["available"])
                    self.assertIn("new revision", get_doc(cache / "docs.sqlite3", DOC_ID)["content"])

    def test_metadata_only_warning_change_is_published_and_counted(self):
        original = _document()
        before = self._seed(document=original)
        updated = replace(original, warnings=("needs_verification",))
        with mock.patch(
            "ufe_docs_mcp.runtime.fetch_official_documents",
            return_value=([updated], _metadata(self.clock())),
        ):
            result = sync_cache(self.cache, clock=self.clock)
        after = index_status(self.path)
        self.assertEqual(after["content_hash"], before["content_hash"])
        self.assertNotEqual(after["index_revision"], before["index_revision"])
        self.assertEqual(get_doc(self.path, DOC_ID)["warnings"], ["needs_verification"])
        self.assertEqual(result["sync_outcome"], "updated")
        runtime = self._runtime(offline=True)
        update = runtime.status()["freshness"]["last_update"]
        self.assertEqual((update["added"], update["changed"], update["removed"]), (0, 1, 0))

    def test_refresh_keeps_raw_page_mode_and_allows_explicit_upgrade(self):
        cases = (
            (True, False, False, True),
            (True, False, True, True),
            (False, True, False, True),
            (False, False, True, False),
        )
        for number, (was_raw, requested_raw, automatic, expected_raw) in enumerate(cases):
            with self.subTest(was_raw=was_raw, requested_raw=requested_raw, automatic=automatic):
                cache = self.cache / f"mode-{number}"
                self._seed(cache=cache, raw_pages=was_raw)
                with mock.patch(
                    "ufe_docs_mcp.runtime.fetch_official_documents",
                    side_effect=self._fetched_documents,
                ) as fetch:
                    sync_cache(cache, refresh_pages=requested_raw, automatic=automatic, clock=self.clock)
                fetch.assert_called_once()
                self.assertEqual(fetch.call_args.kwargs["refresh_pages"], expected_raw)
                self.assertEqual(index_status(cache / "docs.sqlite3")["metadata"]["content_mode"], "raw_pages" if expected_raw else "published_catalog")

    def test_corrupt_raw_index_recovers_without_downgrading_successful_source_mode(self):
        self._seed()
        history_path = self.cache / "refresh-state.json"
        with mock.patch(
            "ufe_docs_mcp.runtime.fetch_official_documents",
            side_effect=self._fetched_documents,
        ):
            sync_cache(self.cache, clock=self.clock)
        self.assertEqual(
            json.loads(history_path.read_text())["last_successful_mode"],
            "published_catalog",
        )
        before_failed_upgrade = self.path.read_bytes()
        self.clock.now += 1
        with mock.patch(
            "ufe_docs_mcp.runtime.fetch_official_documents",
            side_effect=RuntimeError("Synthetic raw upgrade failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "Synthetic raw upgrade failed"):
                sync_cache(self.cache, refresh_pages=True, clock=self.clock)
        failed_history = json.loads(history_path.read_text())
        self.assertEqual(failed_history["last_outcome"], "failed")
        self.assertEqual(failed_history["check_mode"], "raw_pages")
        self.assertEqual(failed_history["last_successful_mode"], "published_catalog")
        self.assertEqual(self.path.read_bytes(), before_failed_upgrade)

        self.clock.now += 1
        with mock.patch(
            "ufe_docs_mcp.runtime.fetch_official_documents",
            side_effect=self._fetched_documents,
        ):
            published = sync_cache(self.cache, refresh_pages=True, clock=self.clock)
        self.assertEqual(published["metadata"]["content_mode"], "raw_pages")
        history = history_path.read_text()
        self.assertEqual(json.loads(history)["last_successful_mode"], "raw_pages")
        self.path.write_bytes(b"Synthetic corruption after a successful raw-page publication.")
        self.assertEqual(history_path.read_text(), history)

        self.clock.now += 1
        with mock.patch(
            "ufe_docs_mcp.runtime.fetch_official_documents",
            side_effect=self._fetched_documents,
        ) as fetch:
            recovered = sync_cache(self.cache, automatic=True, clock=self.clock)
        fetch.assert_called_once()
        self.assertTrue(fetch.call_args.kwargs["refresh_pages"])
        self.assertTrue(recovered["available"])
        self.assertEqual(recovered["metadata"]["content_mode"], "raw_pages")
        self.assertEqual(index_status(self.path)["metadata"]["content_mode"], "raw_pages")
        self.assertEqual(json.loads(history_path.read_text())["last_successful_mode"], "raw_pages")
        self.assertIn("new revision", get_doc(self.path, DOC_ID)["content"])

    def test_automatic_coordinator_skips_fresh_cache(self):
        self._seed(age=5)
        before = self.path.read_bytes()
        with mock.patch("ufe_docs_mcp.runtime.fetch_official_documents") as fetch:
            result = sync_cache(self.cache, automatic=True, clock=self.clock)
        fetch.assert_not_called()
        self.assertEqual(result["sync_outcome"], "not_due")
        self.assertEqual(self.path.read_bytes(), before)

    def test_offline_never_fetches_and_explicit_refresh_is_rejected(self):
        self._seed()
        before = self.path.read_bytes()
        with mock.patch("ufe_docs_mcp.runtime.fetch_official_documents") as fetch:
            runtime = self._runtime(offline=True)
            runtime.bootstrap()
            runtime.maybe_refresh()
            for raw_pages in (False, True):
                result = runtime.refresh(refresh_pages=raw_pages)
                self.assertFalse(result["accepted"])
                self.assertEqual(result["reason"], "offline")
            status = runtime.status()
            runtime.close()
            fetch.assert_not_called()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(status["freshness"]["state"], "offline")
        self.assertTrue(status["freshness"]["check_overdue"])

    def test_disabling_auto_refresh_still_allows_explicit_refresh(self):
        self._seed()
        with mock.patch(
            "ufe_docs_mcp.runtime.fetch_official_documents",
            side_effect=self._fetched_documents,
        ) as fetch:
            runtime = self._runtime(auto_refresh=False)
            runtime.bootstrap()
            runtime.maybe_refresh()
            fetch.assert_not_called()
            self.assertFalse(runtime.status()["freshness"]["automatic_refresh"])
            accepted = runtime.refresh()
            self.assertTrue(accepted["accepted"])
            self.assertEqual(accepted["reason"], "started")
            self._finish_worker(runtime)
            fetch.assert_called_once()
            runtime.close()
            rejected = runtime.refresh()
            self.assertFalse(rejected["accepted"])
            self.assertEqual(rejected["reason"], "closed")

    def test_explicit_raw_refresh_is_rejected_while_another_owner_holds_lock(self):
        self._seed()
        before = self.path.read_bytes()
        runtime = self._runtime(auto_refresh=False)
        with mock.patch("ufe_docs_mcp.runtime.fetch_official_documents") as fetch:
            with runtime_module._refresh_lock(self.cache):
                response = runtime.refresh(refresh_pages=True)
                self.assertFalse(response["accepted"])
                self.assertEqual(response["reason"], "already_running")
                self.assertIsNone(runtime._thread)
                fetch.assert_not_called()
            runtime.close()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(index_status(self.path)["metadata"]["content_mode"], "published_catalog")

    def test_accepted_refresh_owns_lock_before_queued_worker_and_through_fetch(self):
        self._seed()
        runtime = self._runtime(auto_refresh=False)
        competing_runtime = self._runtime(auto_refresh=False)
        worker_entered = threading.Event()
        allow_sync = threading.Event()
        source_entered = threading.Event()
        allow_publish = threading.Event()
        original_sync = runtime._sync

        def queued_worker(*args, **kwargs):
            worker_entered.set()
            if not allow_sync.wait(5):
                raise RuntimeError("Synthetic queued worker was never released")
            return original_sync(*args, **kwargs)

        def blocked_source(**kwargs):
            source_entered.set()
            if not allow_publish.wait(5):
                raise RuntimeError("Synthetic source fetch was never released")
            return self._fetched_documents(**kwargs)

        def assert_lock_held():
            with self.assertRaises(runtime_module.RefreshBusy):
                with runtime_module._refresh_lock(self.cache):
                    pass

        with mock.patch.object(runtime, "_sync", side_effect=queued_worker), mock.patch(
            "ufe_docs_mcp.runtime.fetch_official_documents", side_effect=blocked_source
        ) as fetch:
            try:
                response = runtime.refresh()
                self.assertTrue(response["accepted"])
                self.assertEqual(response["reason"], "started")
                self.assertTrue(worker_entered.wait(2))
                fetch.assert_not_called()
                assert_lock_held()
                competing = competing_runtime.refresh(refresh_pages=True)
                self.assertFalse(competing["accepted"])
                self.assertEqual(competing["reason"], "already_running")
                allow_sync.set()
                self.assertTrue(source_entered.wait(2))
                assert_lock_held()
                self.assertIn("old revision", get_doc(self.path, DOC_ID)["content"])
            finally:
                allow_sync.set()
                allow_publish.set()
                self._finish_worker(runtime)
            fetch.assert_called_once()
            self.assertFalse(fetch.call_args.kwargs["refresh_pages"])
        with runtime_module._refresh_lock(self.cache):
            pass
        self.assertIn("new revision", get_doc(self.path, DOC_ID)["content"])

    def test_post_publication_history_failure_preserves_successful_sync_result(self):
        self._seed()
        original_writer = runtime_module._write_state

        def fail_completed_history(cache, state):
            if state["last_outcome"] in {"updated", "unchanged", "initialized"}:
                raise OSError("Synthetic completed-history write failure")
            return original_writer(cache, state)

        with mock.patch(
            "ufe_docs_mcp.runtime.fetch_official_documents",
            side_effect=self._fetched_documents,
        ), mock.patch("ufe_docs_mcp.runtime._write_state", side_effect=fail_completed_history):
            result = sync_cache(self.cache, clock=self.clock)
        self.assertEqual(result["sync_outcome"], "updated")
        self.assertTrue(result["available"])
        self.assertIn("Synthetic completed-history write failure", result["state_warning"])
        self.assertIn("new revision", get_doc(self.path, DOC_ID)["content"])
        self.assertEqual(index_status(self.path)["metadata"]["fetched_at"], _iso(self.clock()))
        stored = json.loads((self.cache / "refresh-state.json").read_text())
        self.assertEqual(stored["last_outcome"], "checking")
        self.assertNotEqual(stored["snapshot_id"], snapshot_from_status(index_status(self.path))["id"])

    def test_runtime_surfaces_history_warning_without_failing_published_snapshot(self):
        self._seed()
        original_writer = runtime_module._write_state

        def fail_completed_history(cache, state):
            if state["last_outcome"] in {"updated", "unchanged", "initialized"}:
                raise OSError("Synthetic runtime-history write failure")
            return original_writer(cache, state)

        with mock.patch(
            "ufe_docs_mcp.runtime.fetch_official_documents",
            side_effect=self._fetched_documents,
        ), mock.patch("ufe_docs_mcp.runtime._write_state", side_effect=fail_completed_history):
            runtime = self._runtime(auto_refresh=False)
            self.assertTrue(runtime.refresh()["accepted"])
            self._finish_worker(runtime)
            status = runtime.status()
        self.assertTrue(status["available"])
        self.assertEqual(status["sync_state"], "ready")
        self.assertEqual(status["freshness"]["state"], "current_to_catalog")
        self.assertIsNone(status["freshness"]["last_error"])
        self.assertTrue(any(
            "Synthetic runtime-history write failure" in warning
            for warning in status["freshness"]["warnings"]
        ))
        self.assertIn("new revision", runtime.decorate(get_doc(self.path, DOC_ID))["content"])

    def test_invalid_source_build_still_raises_and_preserves_previous_bytes(self):
        self._seed()
        before = self.path.read_bytes()
        with mock.patch(
            "ufe_docs_mcp.runtime.fetch_official_documents",
            return_value=([], _metadata(self.clock())),
        ):
            with self.assertRaises(ValueError):
                sync_cache(self.cache, clock=self.clock)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertIn("old revision", get_doc(self.path, DOC_ID)["content"])
        state = json.loads((self.cache / "refresh-state.json").read_text())
        self.assertEqual(state["last_outcome"], "failed")
        self.assertTrue(state["last_error"])

    def test_interrupted_check_without_lock_reports_failure_and_retries_after_start(self):
        before = self._seed()
        (self.cache / "refresh-state.json").write_text(json.dumps({
            "schema_version": 1,
            "snapshot_id": snapshot_from_status(before)["id"],
            "last_attempt_at": _iso(self.clock()),
            "last_finished_at": None,
            "last_outcome": "checking",
            "last_error": None,
        }))
        with mock.patch(
            "ufe_docs_mcp.runtime.fetch_official_documents",
            side_effect=self._fetched_documents,
        ) as fetch:
            runtime = self._runtime()
            freshness = runtime.status()["freshness"]
            self.assertEqual(freshness["state"], "check_failed")
            self.assertIn("interrupted", freshness["last_error"].lower())
            self.assertEqual(freshness["next_check_at"], _iso(self.clock() + 900))
            runtime.bootstrap()
            self.clock.now += 899
            self.assertFalse(runtime.maybe_refresh())
            fetch.assert_not_called()
            self.clock.now += 2
            self.assertTrue(runtime.maybe_refresh())
            self._finish_worker(runtime)
            fetch.assert_called_once()
            recovered = runtime.status()["freshness"]
            self.assertEqual(recovered["state"], "current_to_catalog")
            self.assertIsNone(recovered["last_error"])

    def test_two_processes_coordinate_one_fetch_without_blocking_cached_reads(self):
        self._seed()
        context = multiprocessing.get_context("spawn")
        started = context.Event()
        release = context.Event()
        calls = context.Value("i", 0)
        results = context.Queue()
        first = context.Process(
            target=_process_sync,
            args=(str(self.cache), started, release, calls, results, "first", self.clock()),
        )
        second = context.Process(
            target=_process_sync,
            args=(str(self.cache), started, release, calls, results, "second", self.clock()),
        )
        processes = (first, second)
        try:
            first.start()
            self.assertTrue(started.wait(5), "First coordinator never reached its mocked source")
            self.assertIn("old revision", get_doc(self.path, DOC_ID)["content"])
            second.start()
            second.join(timeout=5)
            self.assertFalse(second.is_alive(), "Competing coordinator blocked behind the source fetch")
            self.assertEqual(second.exitcode, 0)
            self.assertEqual(calls.value, 1)
            name, second_result = results.get(timeout=2)
            self.assertEqual(name, "second")
            if "error_type" in second_result:
                self.assertEqual(second_result["error_type"], "RefreshBusy", second_result)
            self.assertIn("old revision", get_doc(self.path, DOC_ID)["content"])
            release.set()
            first.join(timeout=5)
            self.assertFalse(first.is_alive(), "First coordinator did not finish after release")
            self.assertEqual(first.exitcode, 0)
            name, first_result = results.get(timeout=2)
            self.assertEqual(name, "first")
            self.assertNotIn("error_type", first_result, first_result)
            self.assertEqual(calls.value, 1)
            self.assertIn("new revision", get_doc(self.path, DOC_ID)["content"])
        finally:
            release.set()
            for process in processes:
                if process.pid is not None:
                    process.join(timeout=2)
                    if process.is_alive():
                        process.terminate()
                        process.join(timeout=2)
            results.close()
            results.join_thread()

    def test_source_passages_keep_old_snapshot_when_publication_happens_mid_read(self):
        readers = (
            ("search", lambda path: search_docs(path, "sparrow")),
            ("get", lambda path: get_doc(path, DOC_ID)),
            ("topics", lambda path: list_topics(path)),
        )
        for label, read in readers:
            with self.subTest(reader=label):
                cache = self.cache / label
                before = self._seed(cache=cache)
                path = cache / "docs.sqlite3"
                old_snapshot = snapshot_from_status(before)
                capture = index_module._snapshot

                def publish_after_capture(connection):
                    snapshot = capture(connection)
                    build_index([_document("new")], path, _metadata(self.clock()))
                    return snapshot

                with mock.patch("ufe_docs_mcp.index._snapshot", side_effect=publish_after_capture):
                    old = read(path)
                self.assertEqual(old["snapshot"], old_snapshot)
                if label == "get":
                    self.assertIn("old revision", old["content"])
                elif label == "search":
                    self.assertTrue(any("old revision" in item["content"] for item in old["results"]))
                else:
                    self.assertEqual(
                        old["topics"][0]["content_hash"],
                        hashlib.sha256(_document().content.encode()).hexdigest(),
                    )

                runtime = self._runtime(cache=cache, auto_refresh=False)
                decorated = runtime.decorate(old)
                self.assertEqual(decorated["snapshot"], old_snapshot)
                self.assertEqual(decorated["freshness"]["snapshot_fetched_at"], old_snapshot["fetched_at"])
                self.assertTrue(decorated["freshness"]["check_overdue"])
                current = read(path)
                self.assertNotEqual(current["snapshot"]["id"], old_snapshot["id"])
                self.assertEqual(current["snapshot"]["fetched_at"], _iso(self.clock()))
                self.assertFalse(runtime.status()["freshness"]["check_overdue"])
                runtime.close()

if __name__ == "__main__":
    unittest.main()
