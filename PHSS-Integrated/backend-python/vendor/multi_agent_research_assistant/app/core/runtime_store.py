"""In-memory runtime store for stateless-friendly deployments."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Deque, Dict, List

from app.core.config import settings


@dataclass
class RuntimeStore:
    """Stores recent research runs in process memory."""

    _lock: Lock = field(default_factory=Lock)
    _results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    _history: Deque[str] = field(default_factory=lambda: deque(maxlen=settings.HISTORY_LIMIT))

    def save_result(self, result: Dict[str, Any]) -> None:
        with self._lock:
            thread_id = result["thread_id"]
            payload = {**result, "updated_at": datetime.now(timezone.utc)}
            is_new = thread_id not in self._results
            self._results[thread_id] = payload
            if is_new:
                self._history.appendleft(thread_id)

    def get_result(self, thread_id: str) -> Dict[str, Any] | None:
        with self._lock:
            result = self._results.get(thread_id)
            return dict(result) if result else None

    def list_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            items: List[Dict[str, Any]] = []
            for thread_id in list(self._history)[:limit]:
                result = self._results.get(thread_id)
                if result:
                    items.append(dict(result))
            return items

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            results = list(self._results.values())
            total = len(results)
            successful = sum(1 for item in results if item.get("status") == "completed")
            failed = sum(1 for item in results if item.get("status") == "failed")
            completed_times = [
                item.get("execution_time")
                for item in results
                if item.get("execution_time") is not None and item.get("status") == "completed"
            ]
            today = datetime.now(timezone.utc).date()
            queries_today = sum(
                1
                for item in results
                if item.get("created_at") and item["created_at"].date() == today
            )

            return {
                "total_queries": total,
                "successful_queries": successful,
                "failed_queries": failed,
                "avg_latency": round(sum(completed_times) / len(completed_times), 2) if completed_times else 0.0,
                "total_cost": 0.0,
                "active_users": total,
                "queries_today": queries_today,
            }


runtime_store = RuntimeStore()