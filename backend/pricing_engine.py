"""
Lodging Smart Pricing — core computation (Jira Epic 1 style).

raw_price = base × season × demand × supply × dow × lead_time × quality
final_price = clamp(raw_price, min_price, max_price)

All multipliers are positive; smoothing can be applied per day.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

PRICE_RE = re.compile(r"[^\d.\-]+")


def parse_price(x: Any) -> float:
    if x is None:
        return float("nan")
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if not s:
        return float("nan")
    s = PRICE_RE.sub("", s)
    try:
        return float(s)
    except ValueError:
        return float("nan")


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


@dataclass
class ListingSignals:
    """Derived from CSV row + optional host settings."""

    listing_id: str
    base_anchor: float
    neighbourhood_group: str
    room_type: str
    lat: float
    long: float
    review_rate: float
    reviews_count: float
    availability_365: float
    instant_bookable: bool


def _quality_multiplier(review_rate: float, reviews_count: float) -> float:
    rr = review_rate if not math.isnan(review_rate) else 3.5
    rc = reviews_count if not math.isnan(reviews_count) else 0.0
    q = 0.85 + 0.03 * (rr - 3.0) + 0.02 * min(rc / 100.0, 1.0)
    return clamp(q, 0.75, 1.25)


def _demand_multiplier(seed: int, day_index: int) -> float:
    # pseudo demand oscillation + mild drift
    t = (seed % 97) / 97.0
    wave = 0.92 + 0.08 * math.sin((day_index + t * 20) / 5.0)
    return clamp(wave, 0.85, 1.15)


def _supply_multiplier(availability_365: float) -> float:
    if math.isnan(availability_365):
        availability_365 = 200.0
    # lower availability (more booked) -> tighter supply -> higher price pressure
    occ_proxy = 1.0 - min(max(availability_365 / 365.0, 0.0), 1.0)
    return clamp(0.92 + 0.20 * occ_proxy, 0.90, 1.18)


def _season_multiplier(d: date) -> float:
    # simple NYC-ish summer peak
    m = d.month
    if m in (6, 7, 8):
        return 1.08
    if m in (11, 12, 1):
        return 0.96
    return 1.0


def _dow_multiplier(d: date) -> float:
    return 1.06 if d.weekday() >= 5 else 1.0


def _lead_time_multiplier(days_ahead: int) -> float:
    # farther out -> slightly lower urgency
    if days_ahead <= 3:
        return 1.05
    if days_ahead <= 14:
        return 1.0
    return 0.97


def confidence_score(
    comps_count: int,
    variance_ratio: float,
) -> float:
    # 0..1 higher is better
    c = 0.55 + 0.25 * min(comps_count / 50.0, 1.0) - 0.15 * min(variance_ratio, 1.0)
    return float(clamp(c, 0.2, 0.95))


def explanation_tags(
    *,
    season_m: float,
    dow_m: float,
    demand_m: float,
    supply_m: float,
) -> List[str]:
    tags: List[str] = []
    if season_m > 1.03:
        tags.append("Seasonal peak")
    if dow_m > 1.02:
        tags.append("Weekend")
    if demand_m > 1.04:
        tags.append("High demand")
    if supply_m > 1.05:
        tags.append("Tight supply")
    if not tags:
        tags.append("Market baseline")
    return tags[:5]


def compute_daily_prices(
    listing: ListingSignals,
    *,
    min_price: float,
    max_price: float,
    user_base: Optional[float],
    pricing_goal: str,
    risk: str,
    start: date,
    days: int,
    locked_dates: Optional[set] = None,
    blackout_dates: Optional[set] = None,
    kill_switch: bool = False,
) -> List[Dict[str, Any]]:
    locked_dates = locked_dates or set()
    blackout_dates = blackout_dates or set()

    base = user_base if user_base and user_base > 0 else listing.base_anchor
    qm = _quality_multiplier(listing.review_rate, listing.reviews_count)
    sm = _supply_multiplier(listing.availability_365)

    goal_adj = {"revenue": 1.03, "occupancy": 0.97, "balanced": 1.0}.get(
        pricing_goal.lower(), 1.0
    )
    risk_adj = {"low": 0.98, "medium": 1.0, "high": 1.04}.get(risk.lower(), 1.0)

    seed = hash(listing.listing_id) & 0xFFFFFFFF

    out: List[Dict[str, Any]] = []
    for i in range(days):
        d = start + timedelta(days=i)
        if d in blackout_dates:
            out.append(
                {
                    "date": d.isoformat(),
                    "recommended_price": None,
                    "confidence": 0.0,
                    "tags": ["Blackout"],
                    "components": {},
                    "blocked": True,
                }
            )
            continue

        dm = _demand_multiplier(seed, i)
        season_m = _season_multiplier(d)
        dow_m = _dow_multiplier(d)
        lt_m = _lead_time_multiplier(i)

        raw = (
            base
            * season_m
            * dm
            * sm
            * dow_m
            * lt_m
            * qm
            * goal_adj
            * risk_adj
        )

        # Smoothing vs previous (simple)
        if out and out[-1].get("recommended_price") is not None and not out[-1].get("blocked"):
            prev = float(out[-1]["recommended_price"])
            raw = prev * 0.35 + raw * 0.65

        final = clamp(raw, min_price, max_price) if not kill_switch else clamp(base, min_price, max_price)

        if d in locked_dates:
            final = clamp(base, min_price, max_price)

        comps_count = 12 + (seed % 20)
        var_ratio = 0.15 + (abs(math.sin(i / 7.0)) * 0.1)
        conf = confidence_score(comps_count, var_ratio)
        tags = explanation_tags(
            season_m=season_m, dow_m=dow_m, demand_m=dm, supply_m=sm
        )

        components = {
            "base": round(base, 2),
            "season": round(season_m, 4),
            "demand": round(dm, 4),
            "supply": round(sm, 4),
            "dow": round(dow_m, 4),
            "lead_time": round(lt_m, 4),
            "quality": round(qm, 4),
            "goal": round(goal_adj, 4),
            "risk": round(risk_adj, 4),
        }

        out.append(
            {
                "date": d.isoformat(),
                "recommended_price": round(final, 2),
                "confidence": round(conf, 3),
                "tags": tags,
                "components": components,
                "blocked": False,
            }
        )

    return out


def booking_probability_mock(
    price: float,
    anchor: float,
    demand_hint: float,
) -> float:
    # smooth logistic-ish curve around anchor
    ratio = price / max(anchor, 1.0)
    p = 0.65 - 0.35 * max(0.0, ratio - 1.0) + 0.05 * (demand_hint - 1.0)
    return float(clamp(p, 0.05, 0.92))


def expected_revenue(price: float, prob: float) -> float:
    return float(price * prob)
