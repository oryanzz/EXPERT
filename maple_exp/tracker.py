"""Accumulate EXP gained across periodic readings, including level-ups."""
from collections import Counter
from dataclasses import dataclass, replace

from .parse import Reading

# Same-level readings whose implied level total disagrees by more than this
# are OCR mistakes (an extra or missing digit), not real EXP changes.
_TOTAL_TOLERANCE = 0.02


@dataclass(frozen=True)
class Summary:
    minutes: float
    exp_gained: int
    exp_per_min: float
    exp_per_hour: float
    pct_gained: float
    levels_gained: int
    level: int | None
    pct: float
    exp_to_level: int | None
    eta_minutes: float | None


def _implied_total(r: Reading) -> int | None:
    return round(r.exp * 100 / r.pct) if r.pct > 0 else None


class Tracker:
    def __init__(self, t0: float, first: Reading):
        self.t0 = t0
        self.first = first
        self.last = first
        self.exp_gained = 0
        self.pct_gained = 0.0
        self.levels_gained = 0
        self._best = first  # highest-percent reading this level: most precise total
        self._votes = Counter([first.level] if first.level else [])

    def _level_total(self) -> int | None:
        return _implied_total(self._best)

    @staticmethod
    def _is_level_up(prev: Reading, cur: Reading) -> bool:
        # Decided from EXP alone: the level digits are the least reliable OCR field
        # (live: "LV.23" read as 30, or missed). A death costs a few percent; only a
        # new level drops the bar by more than half.
        return cur.exp < prev.exp and prev.pct - cur.pct > 50

    def _trusted_level(self) -> int | None:
        """Most common level read during the current level (ties: the earliest seen)."""
        return self._votes.most_common(1)[0][0] if self._votes else None

    def add(self, t: float, cur: Reading) -> bool:
        prev = self.last
        if self._is_level_up(prev, cur):
            total = self._level_total() or prev.exp
            self.exp_gained += (total - prev.exp) + cur.exp
            self.pct_gained += (100 - prev.pct) + cur.pct
            old = self._trusted_level()
            jumped = cur.level - old if old and cur.level and cur.level > old else 1
            self.levels_gained += jumped
            new = old + jumped if old else cur.level
            self._votes = Counter([new] if new else []) + Counter([cur.level] if cur.level else [])
            cur = replace(cur, level=self._trusted_level())
            self._best = cur
        else:
            if cur.level:
                self._votes[cur.level] += 1
            cur = replace(cur, level=self._trusted_level())
            if cur.pct >= 1 and self._best.pct >= 1:
                ref = self._level_total()
                if abs(_implied_total(cur) - ref) / ref > _TOTAL_TOLERANCE:
                    return False
            self.exp_gained += cur.exp - prev.exp
            self.pct_gained += cur.pct - prev.pct
            if cur.pct > self._best.pct:
                self._best = cur
        self.last = cur
        return True

    def summary(self, now: float) -> Summary:
        minutes = max(0.0, now - self.t0) / 60
        per_min = self.exp_gained / minutes if minutes > 0 else 0.0
        total = self._level_total()
        to_level = total - self.last.exp if total is not None else None
        eta = to_level / per_min if per_min > 0 and to_level is not None else None
        return Summary(
            minutes=minutes,
            exp_gained=self.exp_gained,
            exp_per_min=per_min,
            exp_per_hour=per_min * 60,
            pct_gained=self.pct_gained,
            levels_gained=self.levels_gained,
            level=self.last.level,
            pct=self.last.pct,
            exp_to_level=to_level,
            eta_minutes=eta,
        )
