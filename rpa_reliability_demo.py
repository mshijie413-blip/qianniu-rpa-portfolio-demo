from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any


class SafetyStop(RuntimeError):
    pass


def normalize_order_id(value: Any) -> str:
    text = str(value).strip()
    if not text or not text.isdigit():
        raise SafetyStop("order id must be an exact digit string")
    return text


class MockPortal:
    def __init__(self, candidates: dict[str, list[str]], profiles: dict[str, list[dict[str, Any]]]):
        self.candidates = candidates
        self.profiles = {key: list(values) for key, values in profiles.items()}
        self.search_box = ""
        self.search_count: dict[str, int] = {}

    def search(self, order_id: str) -> list[str]:
        self.search_box = order_id
        self.search_count[order_id] = self.search_count.get(order_id, 0) + 1
        return list(self.candidates.get(order_id, []))

    def read_search_box(self) -> str:
        return self.search_box

    def read_profile(self, nickname: str) -> dict[str, Any]:
        values = self.profiles.get(nickname, [])
        if not values:
            raise SafetyStop("profile is unavailable")
        return deepcopy(values.pop(0) if len(values) > 1 else values[0])


def collect_one(order_id: str, portal: MockPortal) -> dict[str, Any]:
    normalized = normalize_order_id(order_id)
    candidates = portal.search(normalized)
    if portal.read_search_box() != normalized:
        raise SafetyStop("search box echo mismatch")
    if len(candidates) != 1:
        raise SafetyStop("search result must contain exactly one candidate")
    nickname = candidates[0]
    first, second = portal.read_profile(nickname), portal.read_profile(nickname)
    if first != second:
        raise SafetyStop("two consecutive profile reads are inconsistent")
    if first.get("buyer_nickname") != nickname:
        raise SafetyStop("candidate nickname does not match profile")
    required = {"buyer_nickname", "purchase_count", "cumulative_spend_cents", "average_order_value_cents", "note"}
    if set(first) != required:
        raise SafetyStop("profile fields are incomplete or unexpected")
    return first


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def open_history(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE IF NOT EXISTS completed_orders (order_id TEXT PRIMARY KEY)")
    return connection


def run_batch(rows: list[dict[str, Any]], portal: MockPortal, output_path: Path, history_path: Path) -> list[dict[str, Any]]:
    result = deepcopy(rows)
    grouped: dict[str, list[int]] = {}
    for index, row in enumerate(result):
        grouped.setdefault(normalize_order_id(row["main_order_id"]), []).append(index)

    connection = open_history(history_path)
    try:
        for order_id, indexes in grouped.items():
            if connection.execute("SELECT 1 FROM completed_orders WHERE order_id = ?", (order_id,)).fetchone():
                continue
            profile = collect_one(order_id, portal)
            for index in indexes:
                result[index].update(profile)
            atomic_write_json(output_path, result)
            connection.execute("INSERT INTO completed_orders(order_id) VALUES (?)", (order_id,))
            connection.commit()
    finally:
        connection.close()
    return result


def main() -> None:
    source = Path(sys.argv[1] if len(sys.argv) > 1 else "sample_orders.json")
    rows = json.loads(source.read_text(encoding="utf-8"))
    portal = MockPortal(
        {"800000000000000001": ["buyer_demo_001"], "800000000000000002": ["buyer_demo_002"]},
        {
            "buyer_demo_001": [{"buyer_nickname": "buyer_demo_001", "purchase_count": 3, "cumulative_spend_cents": 29900, "average_order_value_cents": 9967, "note": ""}],
            "buyer_demo_002": [{"buyer_nickname": "buyer_demo_002", "purchase_count": 1, "cumulative_spend_cents": 8900, "average_order_value_cents": 8900, "note": "synthetic demo"}],
        },
    )
    output = Path("demo_result.json")
    print(json.dumps(run_batch(rows, portal, output, Path("demo_history.sqlite3")), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
