"""Light schedule model: on time / hours / peak / ramp <-> controller steps.

The controller stores a list of UTC steps (start, duration, level). The UI edits
a simpler model in local time, and the steps are generated like the Rise app
does: a sunrise ramp up to the peak, a plateau at the peak, and a sunset ramp
back down, each ramp in equal steps at 1/4, 2/4, 3/4 of the peak.
"""
from __future__ import annotations

from .api import MAX_LINE, format_schedule

DAY = 86400
RAMP_STEPS = (3, 2, 1)  # fewer ramp steps are used only if the line would be too long


def _hms(seconds: int) -> str:
    seconds %= DAY
    return "%02d:%02d:%02d" % (seconds // 3600, seconds % 3600 // 60, seconds % 60)


def _secs(hms: str) -> int:
    h, m, s = (int(p) for p in hms.split(":"))
    return h * 3600 + m * 60 + s


def build_steps(model: dict, utc_offset: int) -> list[dict]:
    """Turn {on (local HH:MM:SS), hours, peak, ramp_min} into UTC controller steps."""
    start = _secs(model["on"]) - utc_offset
    total = round(float(model["hours"]) * 3600)
    peak = int(model["peak"])
    ramp = int(model["ramp_min"]) * 60
    if not 0 < total <= DAY:
        raise ValueError("light hours must be between 0 and 24")
    if not 1 <= peak <= 100:
        raise ValueError("peak brightness must be 1-100")
    if ramp < 0 or total - 2 * ramp < 60:
        raise ValueError("the sunrise and sunset ramps must leave at least a minute at peak")

    for n in RAMP_STEPS if ramp else (0,):
        step = ramp // n if n else 0
        if n and step < 1:
            continue
        levels = [max(1, round(peak * i / (n + 1))) for i in range(1, n + 1)]
        plan = [(step, lvl) for lvl in levels] + [(total - 2 * n * step, peak)] + [(step, lvl) for lvl in reversed(levels)]
        steps, t = [], start
        for duration, level in plan:
            steps.append({"start_utc": _hms(t), "duration_s": duration, "level": level})
            t += duration
        if len(format_schedule(steps)) <= MAX_LINE:
            return steps
    raise ValueError("schedule does not fit in the controller's command line")


def describe(steps: list[dict] | None, utc_offset: int) -> dict | None:
    """Best-effort model of whatever schedule is on the controller."""
    if not steps:
        return None
    peak = max(s["level"] for s in steps)
    ramp = 0
    for s in steps:
        if s["level"] >= peak:
            break
        ramp += s["duration_s"]
    return {
        "on": _hms(_secs(steps[0]["start_utc"]) + utc_offset),
        "hours": round(sum(s["duration_s"] for s in steps) / 3600, 2),
        "peak": peak,
        "ramp_min": ramp // 60,
    }


def to_local(steps: list[dict], utc_offset: int) -> list[dict]:
    """Same steps with local start times, for display."""
    return [
        {"start": _hms(_secs(s["start_utc"]) + utc_offset), "duration_min": round(s["duration_s"] / 60, 1), "level": s["level"]}
        for s in steps
    ]


def window(steps: list[dict], utc_offset: int) -> str:
    """'07:00-23:00' style summary in local time."""
    start = _secs(steps[0]["start_utc"]) + utc_offset
    end = start + sum(s["duration_s"] for s in steps)
    return f"{_hms(start)[:5]}-{_hms(end)[:5]}"
