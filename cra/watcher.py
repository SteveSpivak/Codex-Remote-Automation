from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Optional

from .audit import append_jsonl
from .discovery import SENTRY_SCOPE_PATH, discover_codex_environment, load_json, summarize_breadcrumbs

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:  # pragma: no cover - environment dependent
    FileSystemEventHandler = object
    Observer = None


def summarize_scope_file(path: Path = SENTRY_SCOPE_PATH) -> Dict[str, object]:
    payload = load_json(path)
    summary = summarize_breadcrumbs(payload)
    summary["path"] = str(path)
    return summary


class SentryScopeEventHandler(FileSystemEventHandler):
    def __init__(self, scope_path: Path, sink: Callable[[Dict[str, object]], None]) -> None:
        self.scope_path = scope_path.resolve()
        self.sink = sink

    def on_modified(self, event) -> None:  # pragma: no cover - filesystem integration
        if Path(event.src_path).resolve() != self.scope_path:
            return
        self.sink(summarize_scope_file(self.scope_path))


def run_watch(scope_path: Path = SENTRY_SCOPE_PATH, audit_path: Optional[Path] = None) -> None:
    if Observer is None:  # pragma: no cover - environment dependent
        raise RuntimeError("watchdog is not installed. Install requirements.txt to enable file watching.")

    resolved_scope_path = scope_path.resolve()
    resolved_parent = resolved_scope_path.parent

    def sink(summary: Dict[str, object]) -> None:
        if audit_path:
            append_jsonl(audit_path, "sentry_scope_summary", summary)
        print(summary)

    handler = SentryScopeEventHandler(resolved_scope_path, sink)
    observer = Observer()
    observer.schedule(handler, str(resolved_parent), recursive=False)
    observer.start()
    print(discover_codex_environment().to_dict())
    print(summarize_scope_file(resolved_scope_path))
    try:  # pragma: no cover - runtime behavior
        observer.join()
    finally:
        observer.stop()
        observer.join()
