"""Lightweight Prometheus-compatible metrics collector and exporter.

Design notes (documented semantics):
- Counters and histograms are cumulative over the process lifetime and are
  process-local: each API replica exposes its own values at /api/metrics, and
  a Prometheus server aggregates by summing across scrape targets.
- Histograms use standard cumulative buckets so `histogram_quantile()` works.
- Labels are bounded: only fixed enum-ish values (method, normalized route
  template, status class, outcome/status enums) may be used. Callers must not
  pass scan IDs, filenames, hashes, or request IDs as label values.
"""

from __future__ import annotations

import re
import threading
from typing import Any

# Standard histogram buckets (seconds) tuned for HTTP + CPU inference.
DEFAULT_BUCKETS: tuple[float, ...] = (
    0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0,
)

_LABEL_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_LABEL_VALUE_RE = re.compile(r"^[A-Za-z0-9_\-\.\/\{\}]{1,128}$")


def _validate_label_value(name: str, value: str) -> str:
    """Reject unbounded or injection-prone label values (defense in depth)."""
    if not _LABEL_VALUE_RE.match(value):
        raise ValueError(f"Invalid metric label value for '{name}'")
    return value


class MetricsRegistry:
    """Thread-safe Prometheus metrics registry with bounded labels."""

    def __init__(self, buckets: tuple[float, ...] = DEFAULT_BUCKETS) -> None:
        self._lock = threading.Lock()
        self._buckets = buckets
        # name -> (labels tuple) -> value
        self._counters: dict[str, dict[tuple[tuple[str, str], ...], float]] = {}
        self._gauges: dict[str, dict[tuple[tuple[str, str], ...], float]] = {}
        # name -> labels -> [bucket_counts..., count, sum]
        self._histograms: dict[str, dict[tuple[tuple[str, str], ...], list[float]]] = {}
        self._help: dict[str, str] = {}

    # -- registration helpers -------------------------------------------------

    def _register_help(self, name: str, text: str) -> None:
        self._help.setdefault(name, text)

    def _series_key(self, labels: dict[str, str] | None) -> tuple[tuple[str, str], ...]:
        if not labels:
            return ()
        for k, v in labels.items():
            if not _LABEL_NAME_RE.match(k):
                raise ValueError(f"Invalid metric label name '{k}'")
            _validate_label_value(k, v)
        return tuple(sorted((k, v) for k, v in labels.items()))

    # -- mutation API ---------------------------------------------------------

    def inc_counter(
        self, name: str, labels: dict[str, str] | None = None, value: float = 1.0
    ) -> None:
        with self._lock:
            series = self._counters.setdefault(name, {})
            key = self._series_key(labels)
            series[key] = series.get(key, 0.0) + value

    def set_gauge(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        with self._lock:
            series = self._gauges.setdefault(name, {})
            series[self._series_key(labels)] = value

    def observe_histogram(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        with self._lock:
            series = self._histograms.setdefault(name, {})
            key = self._series_key(labels)
            if key not in series:
                # bucket counts + count + sum, all cumulative
                series[key] = [0.0] * (len(self._buckets) + 2)
            obs = series[key]
            for i, bound in enumerate(self._buckets):
                if value <= bound:
                    obs[i] += 1.0
            obs[-2] += 1.0  # _count
            obs[-1] += value  # _sum

    # -- convenience instrumented helpers -------------------------------------

    def observe_http_request(
        self, method: str, route: str, status_code: int, duration_seconds: float
    ) -> None:
        """Record one HTTP request (count + duration histogram). Called once."""
        labels = {
            "method": method,
            "route": route,
            "status_class": f"{status_code // 100}xx",
        }
        self.inc_counter("http_requests_total", labels)
        self.observe_histogram(
            "http_request_duration_seconds",
            duration_seconds,
            {"method": method, "route": route},
        )

    # -- exposition -----------------------------------------------------------

    def render(self) -> str:
        """Render metrics in Prometheus text exposition format (v0.0.4)."""
        with self._lock:
            lines: list[str] = []

            for name, text in self._help.items():
                lines.append(f"# HELP {name} {text}")

            for name, series in self._counters.items():
                self._register_help(name, "Cumulative counter (process-local).")
                lines.append(f"# TYPE {name} counter")
                for key, val in sorted(series.items()):
                    lines.append(_fmt_sample(name, key, _fmt_val(val)))

            for name, series in self._gauges.items():
                self._register_help(name, "Current gauge value (process-local).")
                lines.append(f"# TYPE {name} gauge")
                for key, val in sorted(series.items()):
                    lines.append(_fmt_sample(name, key, _fmt_val(val)))

            for name, series in self._histograms.items():
                self._register_help(name, "Cumulative histogram (process-local).")
                lines.append(f"# TYPE {name} histogram")
                for key, obs in sorted(series.items()):
                    for i, bound in enumerate(self._buckets):
                        lines.append(
                            _fmt_sample(f"{name}_bucket", key + (("le", f"{bound:g}"),), _fmt_val(obs[i]))
                        )
                    lines.append(
                        _fmt_sample(f"{name}_bucket", key + (("le", "+Inf"),), _fmt_val(obs[-2]))
                    )
                    lines.append(_fmt_sample(f"{name}_count", key, _fmt_val(obs[-2])))
                    lines.append(_fmt_sample(f"{name}_sum", key, _fmt_val(obs[-1])))

            return "\n".join(lines) + "\n"


def _fmt_sample(name: str, labels: tuple[tuple[str, str], ...], value: str) -> str:
    if labels:
        label_str = ",".join(f'{k}="{v}"' for k, v in labels)
        return f"{name}{{{label_str}}} {value}"
    return f"{name} {value}"


def _fmt_val(value: float) -> str:
    return f"{value:g}"


def normalize_route(request_path: str, route_template: str | None) -> str:
    """Return bounded route label: FastAPI route template when matched,
    else the raw path with UUID/numeric segments collapsed."""
    if route_template:
        return route_template
    segments = request_path.split("/")
    collapsed = [
        "id" if (seg and (seg.isdigit() or _UUID_RE.match(seg))) else seg
        for seg in segments
    ]
    return "/".join(collapsed)


_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

# Global metrics registry instance
registry = MetricsRegistry()
