from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class AnalysisEntry:
    name: str
    wins: int
    losses: int
    matches: int
    value: float


@dataclass(frozen=True)
class AnalysisSummary:
    mode: str
    metric_label: str
    total_names: int
    total_comparisons: int | None
    ranking: list[AnalysisEntry]


def load_state(path: Path | None) -> dict:
    if path is None:
        raise ValueError("Analysis requires --state <path> to read a persisted ranking state.")
    if not path.exists():
        raise FileNotFoundError(f"Could not find ranking state file: {path}")
    with path.open(encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        raise ValueError("Ranking state must be a JSON object.")
    return payload


def summarize_state(payload: dict) -> AnalysisSummary:
    mode = str(payload.get("mode", "count"))
    metric_label = "rating" if mode == "elo" else "score"
    names = _ordered_names(payload)
    entry_map = _entries_by_name(payload, mode)
    ranking = [entry_map[name] for name in names]
    ranking.sort(key=lambda entry: (-entry.value, -entry.wins, entry.losses, entry.name.lower()))
    return AnalysisSummary(
        mode=mode,
        metric_label=metric_label,
        total_names=len(names),
        total_comparisons=_total_comparisons(payload, entry_map.values()),
        ranking=ranking,
    )


def top_entries(summary: AnalysisSummary, limit: int = 10) -> list[AnalysisEntry]:
    return summary.ranking[: max(0, limit)]


def bottom_entries(summary: AnalysisSummary, limit: int = 10) -> list[AnalysisEntry]:
    if limit <= 0:
        return []
    return list(reversed(summary.ranking[-limit:]))


def format_analysis(summary: AnalysisSummary, limit: int = 10) -> str:
    top = top_entries(summary, limit=limit)
    bottom = bottom_entries(summary, limit=limit)
    lines = [
        f"Top {len(top)} names:",
        *_format_section(top, summary.metric_label),
        "",
        f"Bottom {len(bottom)} names:",
        *_format_section(bottom, summary.metric_label),
        "",
        "Summary:",
        f"- Names: {summary.total_names}",
    ]
    if summary.total_comparisons is not None:
        lines.append(f"- Comparisons: {summary.total_comparisons}")
    return "\n".join(lines)


def _ordered_names(payload: dict) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for raw_name in payload.get("names", []):
        if not raw_name or raw_name in seen:
            continue
        seen.add(raw_name)
        names.append(str(raw_name))
    for entry in payload.get("entries", []):
        name = str(entry.get("name", ""))
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def _entries_by_name(payload: dict, mode: str) -> dict[str, AnalysisEntry]:
    result: dict[str, AnalysisEntry] = {}
    for name in _ordered_names(payload):
        result[name] = AnalysisEntry(name=name, wins=0, losses=0, matches=0, value=_default_value(mode))
    for raw_entry in payload.get("entries", []):
        name = str(raw_entry.get("name", ""))
        if not name:
            continue
        wins = int(raw_entry.get("wins", 0))
        losses = int(raw_entry.get("losses", 0))
        matches = int(raw_entry.get("matches", wins + losses))
        value_key = "rating" if mode == "elo" else "score"
        default_value = float(wins) if mode != "elo" else 1000.0
        value = float(raw_entry.get(value_key, default_value))
        result[name] = AnalysisEntry(name=name, wins=wins, losses=losses, matches=matches, value=value)
    return result


def _default_value(mode: str) -> float:
    return 1000.0 if mode == "elo" else 0.0


def _total_comparisons(payload: dict, entries: Sequence[AnalysisEntry]) -> int | None:
    if "comparisons" in payload:
        return int(payload["comparisons"])
    matches_total = sum(entry.matches for entry in entries)
    if matches_total > 0:
        return matches_total // 2
    wins_total = sum(entry.wins for entry in entries)
    return wins_total if wins_total > 0 else None


def _format_section(entries: Sequence[AnalysisEntry], metric_label: str) -> list[str]:
    if not entries:
        return ["(none)"]
    lines: list[str] = []
    for index, entry in enumerate(entries, start=1):
        value = f"{entry.value:.2f}" if metric_label == "rating" else str(int(entry.value))
        lines.append(f"{index}. {entry.name} ({metric_label}: {value})")
    return lines
