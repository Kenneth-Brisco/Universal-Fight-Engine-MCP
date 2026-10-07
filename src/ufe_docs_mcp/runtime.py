"""Maintain a local documentation snapshot without blocking cached reads."""
from __future__ import annotations

from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
import json
import logging
import math
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
from typing import Callable

from .index import (
    _document_revision, build_index, document_revisions, index_status,
    snapshot_from_status,
)
from .source import fetch_official_documents

LOG = logging.getLogger("ufe_docs_mcp")
DEFAULT_REFRESH_HOURS = 24.0
RETRY_SECONDS = 15 * 60
SCHEDULER_SECONDS = 30.0


class RefreshBusy(RuntimeError):
    """Another process already holds this cache's synchronization lock."""


def _iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def _epoch(value: object) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return date.timestamp() if date.tzinfo is not None else None
    except (ValueError, OverflowError, OSError):
        return None


def _past(value: object, now: float) -> float | None:
    stamp = _epoch(value)
    return stamp if stamp is not None and stamp <= now else None


def _hours(value: float) -> float:
    if isinstance(value, bool) or not math.isfinite(value) or value < 1:
        raise ValueError("refresh_hours must be a finite number of at least 1 hour")
    return float(value)


def _cache_status(cache_dir: Path) -> dict:
    path = Path(cache_dir) / "docs.sqlite3"
    try:
        return index_status(path)
    except (OSError, ValueError, sqlite3.DatabaseError) as exc:
        return {"available": False, "path": str(path), "reason": str(exc)}


def _read_state(cache_dir: Path) -> dict:
    path = Path(cache_dir) / "refresh-state.json"
    try:
        with path.open(encoding="utf-8") as stream:
            text = stream.read(64_001)
        state = json.loads(text)
        if len(text) > 64_000 or not isinstance(state, dict) or state.get("schema_version") != 1:
            raise ValueError("unsupported update state")
        return state
    except FileNotFoundError:
        return {}
    except (OSError, ValueError, UnicodeError):
        return {"state_error": "Saved update-check state is unreadable; a new check is required."}


def _write_state(cache_dir: Path, state: dict) -> None:
    descriptor, name = tempfile.mkstemp(prefix=".refresh-state-", suffix=".tmp", dir=cache_dir)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump({**state, "schema_version": 1}, stream, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, cache_dir / "refresh-state.json")
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def _refresh_lock(cache_dir: Path, wait_seconds: float = 0.0):
    """OS-backed SQLite lock, separate from the atomically replaced index.

    The transaction is only a mutex. Closing it or exiting the process releases
    the lock; there are no stale lock leases to delete. Readers use docs.sqlite3.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    # A runtime may acquire the lock before acknowledging a tool request, then
    # transfer its exclusive ownership to the worker that eventually closes it.
    connection = sqlite3.connect(cache_dir / "refresh-lock.sqlite3", timeout=wait_seconds, check_same_thread=False)
    try:
        try:
            connection.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc).lower() or "busy" in str(exc).lower():
                raise RefreshBusy("Another UFE documentation synchronization is already running.") from exc
            raise
        yield
    finally:
        connection.close()


PROBE_WAIT_SECONDS = 0.2


def _refresh_running(cache_dir: Path) -> bool:
    """Whether a synchronization holds the lock.

    Every server sharing the cache probes by taking the lock briefly, so two
    simultaneous probes can collide. Waiting a moment lets another probe release
    it, while a real synchronization holds it for many seconds.
    """
    if not (cache_dir / "refresh-lock.sqlite3").exists():
        return False
    try:
        with _refresh_lock(cache_dir, wait_seconds=PROBE_WAIT_SECONDS):
            return False
    except RefreshBusy:
        return True
    except (OSError, sqlite3.DatabaseError):
        return False


def _snapshot_id(status: dict) -> str | None:
    return snapshot_from_status(status)["id"] if status.get("available") else None


def _due_at(status: dict, state: dict, now: float, refresh_hours: float) -> float:
    if state.get("state_error"):
        return 0
    same_snapshot = state.get("snapshot_id") == _snapshot_id(status)
    if same_snapshot and state.get("last_outcome") in ("checking", "failed"):
        attempt = _past(state.get("last_finished_at"), now) or _past(state.get("last_attempt_at"), now)
        if attempt is not None:
            return attempt + RETRY_SECONDS
    fetched = _past(status.get("metadata", {}).get("fetched_at"), now) if status.get("available") else None
    return fetched + refresh_hours * 3600 if fetched is not None else 0


def sync_cache(
    cache_dir: Path, *, refresh_pages: bool = False, automatic: bool = False,
    refresh_hours: float = DEFAULT_REFRESH_HOURS, clock: Callable[[], float] = time.time,
    _lock_held: bool = False,
) -> dict:
    """Synchronize once, with shared locking, durable retry state and safe publication."""
    cache_dir = Path(cache_dir)
    refresh_hours = _hours(refresh_hours)
    with nullcontext() if _lock_held else _refresh_lock(cache_dir):
        previous = _cache_status(cache_dir)
        state = _read_state(cache_dir)
        if automatic and _due_at(previous, state, clock(), refresh_hours) > clock():
            return {**previous, "sync_outcome": "not_due"}
        old_revisions = document_revisions(cache_dir / "docs.sqlite3") if previous["available"] else {}
        # Once the user opts into raw pages, keep that source mode. A newer
        # download of an older bulk catalog must not overwrite raw-page content.
        recorded_mode = previous.get("metadata", {}).get("content_mode") or state.get("last_successful_mode")
        if recorded_mode is None and state.get("last_outcome") in ("updated", "unchanged", "initialized"):
            recorded_mode = state.get("check_mode")
        raw = refresh_pages or recorded_mode == "raw_pages"
        last_finished = _past(state.get("last_finished_at"), clock())
        prior_delay = previous.get("metadata", {}).get("crawl_delay_seconds", 10.0)
        if not isinstance(prior_delay, (int, float)) or not 1 <= prior_delay <= 60:
            prior_delay = 10.0
        state = {
            "schema_version": 1,
            "snapshot_id": _snapshot_id(previous),
            "last_attempt_at": _iso(clock()),
            "last_finished_at": None,
            "last_successful_check_at": previous.get("metadata", {}).get("fetched_at"),
            "last_outcome": "checking", "last_error": None,
            "check_mode": "raw_pages" if raw else "published_catalog",
            "last_successful_mode": recorded_mode,
            "last_update": state.get("last_update"),
        }
        _write_state(cache_dir, state)
        try:
            documents, metadata = fetch_official_documents(
                refresh_pages=raw, report=LOG.info,
                not_before=last_finished + prior_delay if last_finished is not None else None,
            )
            metadata = {**metadata, "fetched_at": _iso(clock())}
            revisions = {document.doc_id: _document_revision(document) for document in documents}
            added = sorted(revisions.keys() - old_revisions.keys())
            removed = sorted(old_revisions.keys() - revisions.keys())
            changed = sorted(key for key in revisions.keys() & old_revisions.keys()
                             if revisions[key] != old_revisions[key])
            result = build_index(documents, cache_dir / "docs.sqlite3", metadata)
            outcome = "initialized" if not previous["available"] else "updated" if added or removed or changed else "unchanged"
            if outcome != "unchanged":
                state["last_update"] = {
                    "detected_at": _iso(clock()), "added": len(added),
                    "changed": len(changed), "removed": len(removed),
                    "examples": (added + changed + removed)[:5],
                    "index_revision": result["index_revision"],
                    "initial_download": not previous["available"],
                }
            state.update({
                "snapshot_id": _snapshot_id(result), "last_finished_at": _iso(clock()),
                "last_successful_check_at": metadata["fetched_at"],
                "last_successful_mode": metadata.get("content_mode"),
                "last_outcome": outcome, "last_error": None,
            })
            try:
                _write_state(cache_dir, state)
            except OSError as exc:
                # Publication has already succeeded. Failure to save auxiliary
                # update history must not be presented as a failed source sync.
                result["state_warning"] = "Documentation updated, but saving update history failed: " + str(exc)[:1_000]
                LOG.warning(result["state_warning"])
            return {**result, "sync_outcome": outcome, "last_update": state["last_update"]}
        except Exception as exc:
            state.update({"last_finished_at": _iso(clock()), "last_outcome": "failed", "last_error": str(exc)[:2_000]})
            try:
                _write_state(cache_dir, state)
            except OSError:
                LOG.warning("Could not persist the failed update attempt.")
            raise


class DocumentationRuntime:
    def __init__(
        self, cache_dir: Path, offline: bool = False, *,
        refresh_hours: float = DEFAULT_REFRESH_HOURS, auto_refresh: bool = True,
        clock: Callable[[], float] = time.time,
    ):
        self.cache_dir = Path(cache_dir)
        self.path = self.cache_dir / "docs.sqlite3"
        self.offline = offline
        self.refresh_hours = _hours(refresh_hours)
        self.auto_refresh = auto_refresh
        self.clock = clock
        self.last_error: str | None = None
        self._error_at = 0.0
        self._state_warning: str | None = None
        self._retry_at = 0.0
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._scheduler: threading.Thread | None = None
        self._stop = threading.Event()

    def bootstrap(self) -> None:
        if self.offline or not self.auto_refresh or self._stop.is_set():
            return
        self.maybe_refresh()
        with self._lock:
            if self._scheduler is None:
                self._scheduler = threading.Thread(target=self._schedule, name="ufe-docs-scheduler", daemon=True)
                self._scheduler.start()

    def _schedule(self) -> None:
        while not self._stop.wait(SCHEDULER_SECONDS):
            self.maybe_refresh()

    def close(self) -> None:
        self._stop.set()

    def maybe_refresh(self) -> bool:
        if self.offline or not self.auto_refresh or self._stop.is_set() or self.clock() < self._retry_at:
            return False
        status = _cache_status(self.cache_dir)
        if _due_at(status, _read_state(self.cache_dir), self.clock(), self.refresh_hours) > self.clock():
            return False
        try:
            return self._start(automatic=True)
        except (OSError, sqlite3.DatabaseError) as exc:
            self.last_error = str(exc)[:2_000]
            self._error_at = self.clock()
            self._retry_at = self.clock() + RETRY_SECONDS
            LOG.warning("Could not start a documentation update: %s", exc)
            return False

    def _start(self, *, automatic: bool, refresh_pages: bool = False) -> bool:
        with self._lock:
            if self._stop.is_set() or (self._thread is not None and self._thread.is_alive()):
                return False
            lease = _refresh_lock(self.cache_dir)
            try:
                lease.__enter__()
            except RefreshBusy:
                return False
            self._thread = threading.Thread(
                target=self._sync, kwargs={"automatic": automatic, "refresh_pages": refresh_pages, "lease": lease},
                name="ufe-docs-sync", daemon=True,
            )
            try:
                self._thread.start()
            except Exception:
                lease.__exit__(None, None, None)
                raise
            return True

    def _sync(self, *, automatic: bool, refresh_pages: bool, lease) -> None:
        try:
            result = sync_cache(self.cache_dir, automatic=automatic, refresh_pages=refresh_pages,
                                refresh_hours=self.refresh_hours, clock=self.clock, _lock_held=True)
            self.last_error = None
            self._error_at = 0
            self._retry_at = 0
            self._state_warning = result.get("state_warning")
            LOG.info("Documentation synchronization: %s.", result["sync_outcome"])
        except Exception as exc:
            self.last_error = str(exc)[:2_000]
            self._error_at = self.clock()
            self._retry_at = self.clock() + RETRY_SECONDS
            LOG.warning("Documentation update did not complete: %s", exc)
        finally:
            lease.__exit__(None, None, None)

    def refresh(self, refresh_pages: bool = False) -> dict:
        if self.offline:
            return {**self.status(), "accepted": False, "reason": "offline"}
        if self._stop.is_set():
            return {**self.status(), "accepted": False, "reason": "closed"}
        try:
            accepted = self._start(automatic=False, refresh_pages=refresh_pages)
        except (OSError, sqlite3.DatabaseError) as exc:
            self.last_error = str(exc)[:2_000]
            self._error_at = self.clock()
            self._retry_at = self.clock() + RETRY_SECONDS
            return {**self.status(), "accepted": False, "reason": "failed_to_start"}
        return {**self.status(), "accepted": accepted, "reason": "started" if accepted else "already_running"}

    def freshness(self, snapshot: dict | None, *, available: bool = True) -> dict:
        now = self.clock()
        snapshot = snapshot or {}
        state = _read_state(self.cache_dir)
        finished = _past(state.get("last_finished_at"), now)
        if (self.last_error and state.get("last_outcome") in ("updated", "unchanged", "initialized")
                and finished is not None and finished >= self._error_at):
            # A different client or the CLI may have recovered this shared cache.
            self.last_error = None
            self._error_at = 0
            self._retry_at = 0
        fetched = _past(snapshot.get("fetched_at"), now)
        age = max(0, int(now - fetched)) if fetched is not None else None
        overdue = age is None or age >= self.refresh_hours * 3600
        running = ((self._thread is not None and self._thread.is_alive()) or _refresh_running(self.cache_dir)) and not self.offline
        same_snapshot = state.get("snapshot_id") == (snapshot.get("id") if available else None)
        if same_snapshot and state.get("last_outcome") in ("updated", "unchanged", "initialized"):
            self._state_warning = None
        error = state.get("last_error") if same_snapshot else None
        error = self.last_error or error or state.get("state_error")
        if same_snapshot and state.get("last_outcome") == "checking" and not running:
            error = error or "The previous update was interrupted; the automatic retry is delayed for 15 minutes from its start."
        mode = snapshot.get("content_mode", "unknown")
        warnings = []
        if self.offline:
            label = "offline"
            warnings.append("Offline mode: no update checks or documentation downloads are performed.")
        elif not available:
            label = "unavailable"
        elif running:
            label = "refreshing"
            warnings.append("An update is running; this response uses the existing snapshot.")
        elif error:
            label = "check_failed"
        elif overdue:
            label = "check_due"
        else:
            label = "current_to_raw_pages" if mode == "raw_pages" else "current_to_catalog" if mode == "published_catalog" else "check_due"
        if overdue:
            warnings.append("The source-check time is missing or invalid." if age is None else
                            "The update check is overdue; documentation may have changed since this snapshot was fetched.")
        if error:
            warnings.append("The latest update check could not be completed: " + str(error)[:2_000])
        if self._state_warning:
            warnings.append(self._state_warning)
        if not self.auto_refresh and not self.offline:
            warnings.append("Automatic updates are disabled for this process; use ufe_refresh_docs or the sync command.")
        if mode != "raw_pages":
            warnings.append("The published catalog may lag raw-page edits. Use ufe_refresh_docs(refresh_pages=true) for a full raw-page refresh.")
        else:
            warnings.append("Raw pages were fetched during the recorded sync; edits after that sync are not included.")
        update = state.get("last_update")
        if isinstance(update, dict) and update.get("index_revision") != snapshot.get("index_revision") and available:
            warnings.append("A different local documentation revision is available; repeat this query to read the current index.")
        status_for_due = {"available": available, "metadata": {"fetched_at": snapshot.get("fetched_at")}}
        due = _due_at(status_for_due, {}, now, self.refresh_hours)
        if same_snapshot and state.get("last_outcome") in ("failed", "checking"):
            finished = _past(state.get("last_finished_at"), now) or _past(state.get("last_attempt_at"), now)
            if finished is not None:
                due = finished + RETRY_SECONDS
        return {
            "state": label, "scope": mode,
            "snapshot_fetched_at": snapshot.get("fetched_at"), "snapshot_age_seconds": age,
            "check_overdue": overdue, "refresh_interval_hours": self.refresh_hours,
            "automatic_refresh": self.auto_refresh and not self.offline,
            "last_attempt_at": state.get("last_attempt_at"),
            "active_mode": state.get("check_mode") if running else None,
            "last_successful_check_at": snapshot.get("fetched_at") if fetched is not None else None,
            "next_check_at": _iso(max(now, due, self._retry_at)) if self.auto_refresh and not self.offline else None,
            "last_error": error, "last_update": update if isinstance(update, dict) else None,
            "warnings": warnings,
        }

    def decorate(self, result: dict) -> dict:
        return {**result, "freshness": self.freshness(result.get("snapshot"))}

    def status(self) -> dict:
        result = _cache_status(self.cache_dir)
        snapshot = snapshot_from_status(result) if result["available"] else None
        freshness = self.freshness(snapshot, available=result["available"])
        running = freshness["state"] == "refreshing" or (
            not self.offline and _refresh_running(self.cache_dir)
        )
        sync_state = "syncing" if running else "error" if freshness["last_error"] else "ready" if result["available"] else "empty"
        guidance = (
            "Documentation is downloading in the background. Check ufe_docs_status shortly."
            if not result["available"] and running else
            "No usable index is available. Run ufe-docs-mcp sync or use ufe_refresh_docs with network access. Offline mode never downloads."
            if not result["available"] else
            "Use the snapshot dates, freshness warnings and last_update summary when answering. Request ufe_refresh_docs for an immediate check."
        )
        return {**result, "offline": self.offline, "sync_state": sync_state,
                "snapshot": snapshot, "freshness": freshness, "guidance": guidance}
