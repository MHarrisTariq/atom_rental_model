"""
Smart Pricing demo API — aligns with Jira stories (lodging, not cars).

GET  /api/listings
GET  /api/pricing/{listing_id}
POST /api/simulation/run
GET  /api/admin/status
POST /api/admin/kill-switch
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:
    from .events import default_publisher
except ImportError:
    from events import default_publisher

try:
    from .observability import configure_logging, request_context_middleware, setup_prometheus
except ImportError:
    from observability import configure_logging, request_context_middleware, setup_prometheus

try:
    from .rate_limit import limiter, rate_limit_exceeded_handler
except ImportError:
    from rate_limit import limiter, rate_limit_exceeded_handler

try:
    from slowapi.errors import RateLimitExceeded
except ImportError:
    RateLimitExceeded = Exception  # type: ignore

try:
    from .auth import create_access_token, require_admin
except ImportError:
    from auth import create_access_token, require_admin

try:
    from .decision_engine import decide_simulation
except ImportError:
    from decision_engine import decide_simulation

try:
    from .pricing_engine import (
        ListingSignals,
        booking_probability_mock,
        compute_daily_prices,
        expected_revenue,
        parse_price,
    )
except ImportError:
    # Running as `python main.py` from the backend/ folder (not a package).
    from pricing_engine import (
        ListingSignals,
        booking_probability_mock,
        compute_daily_prices,
        expected_revenue,
        parse_price,
    )

try:
    from .storage import default_storage
except ImportError:
    from storage import default_storage

try:
    from .ml_conversion import default_model
except ImportError:
    from ml_conversion import default_model

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "Airbnb_Open_Data.csv"
_storage = default_storage(ROOT)
_conversion_model = default_model(ROOT)
_events = default_publisher()
configure_logging()

app = FastAPI(title="Smart Pricing (Lodging) Demo", version="1.0.0")
app.state.limiter = limiter
if RateLimitExceeded is not Exception:
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.middleware("http")(request_context_middleware)
setup_prometheus(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _log(action: str, payload: Dict[str, Any]) -> None:
    _storage.append_audit(action, payload)


def load_df() -> pd.DataFrame:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Missing dataset: {CSV_PATH}")
    return pd.read_csv(CSV_PATH, low_memory=False)


_df: Optional[pd.DataFrame] = None


def get_df() -> pd.DataFrame:
    global _df
    if _df is None:
        _df = load_df()
    return _df


def row_to_listing(row: pd.Series) -> ListingSignals:
    lid = str(int(row["id"])) if not pd.isna(row.get("id")) else "0"
    p = parse_price(row.get("price"))
    rr = float(pd.to_numeric(row.get("review rate number"), errors="coerce") or 3.5)
    rc = float(pd.to_numeric(row.get("number of reviews"), errors="coerce") or 0)
    av = float(pd.to_numeric(row.get("availability 365"), errors="coerce") or 200)
    lat = float(pd.to_numeric(row.get("lat"), errors="coerce") or 0)
    lon = float(pd.to_numeric(row.get("long"), errors="coerce") or 0)
    inst = str(row.get("instant_bookable", "")).strip().lower() in ("true", "t", "1", "yes")
    return ListingSignals(
        listing_id=lid,
        base_anchor=p if not (p is None or (isinstance(p, float) and (p != p))) and p > 0 else 150.0,
        neighbourhood_group=str(row.get("neighbourhood group") or ""),
        room_type=str(row.get("room type") or ""),
        lat=lat,
        long=lon,
        review_rate=rr,
        reviews_count=rc,
        availability_365=av,
        instant_bookable=inst,
    )


class PricingRequestQuery(BaseModel):
    days: int = Field(60, ge=7, le=90)
    from_date: Optional[str] = None


class HostSettingsBody(BaseModel):
    smart_pricing_enabled: bool = False
    min_price: float = Field(..., gt=0)
    max_price: float = Field(..., gt=0)
    base_price: Optional[float] = None
    pricing_goal: str = "balanced"  # revenue | occupancy | balanced
    risk_tolerance: str = "medium"  # low | medium | high
    update_frequency: str = "daily"
    discount_floor_protection: bool = True
    locked_dates: List[str] = []
    blackout_dates: List[str] = []


class SimulationBody(BaseModel):
    listing_id: str
    custom_price: float = Field(..., gt=0)


class KillSwitchBody(BaseModel):
    enabled: bool
    region: Optional[str] = None


class LoginBody(BaseModel):
    username: str
    password: str


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/login")
@limiter.limit("10/minute")
def login(request: Request, body: LoginBody) -> Dict[str, Any]:
    # Demo-only auth. Override via env vars for local testing without code changes.
    admin_user = os.environ.get("SMART_PRICING_ADMIN_USER", "admin")
    admin_pass = os.environ.get("SMART_PRICING_ADMIN_PASS", "admin")
    if body.username == admin_user and body.password == admin_pass:
        token = create_access_token(subject=body.username, role="admin", minutes=12 * 60)
        return {"access_token": token, "token_type": "bearer", "role": "admin"}
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/api/listings")
@limiter.limit("60/minute")
def listings(request: Request, limit: int = 80) -> Dict[str, Any]:
    df = get_df().head(min(max(limit, 1), 500))
    items = []
    for _, row in df.iterrows():
        items.append(
            {
                "id": str(int(row["id"])),
                "name": str(row.get("NAME") or "")[:80],
                "neighbourhood": str(row.get("neighbourhood") or ""),
                "neighbourhood_group": str(row.get("neighbourhood group") or ""),
                "room_type": str(row.get("room type") or ""),
                "price": parse_price(row.get("price")),
            }
        )
    return {"listings": items}


@app.get("/api/pricing/{listing_id}")
@limiter.limit("60/minute")
def get_pricing(
    request: Request,
    listing_id: str,
    days: int = 60,
    from_date: Optional[str] = None,
) -> Dict[str, Any]:
    df = get_df()
    hit = df[df["id"].astype(str) == str(listing_id)]
    if hit.empty:
        raise HTTPException(status_code=404, detail="Listing not found")
    row = hit.iloc[0]
    listing = row_to_listing(row)

    prefs = _storage.get_host_prefs(listing_id) or {}
    if not prefs:
        p = listing.base_anchor
        prefs = {
            "smart_pricing_enabled": True,
            "min_price": max(20.0, round(p * 0.6, 2)),
            "max_price": round(p * 1.5, 2),
            "base_price": round(p, 2),
            "pricing_goal": "balanced",
            "risk_tolerance": "medium",
            "update_frequency": "daily",
            "discount_floor_protection": True,
            "locked_dates": [],
            "blackout_dates": [],
        }

    state = _storage.get_state()
    start = date.today()
    if from_date:
        try:
            start = date.fromisoformat(from_date[:10])
        except ValueError:
            pass

    min_p = float(prefs["min_price"])
    max_p = float(prefs["max_price"])
    base = prefs.get("base_price")
    goal = str(prefs.get("pricing_goal", "balanced"))
    risk = str(prefs.get("risk_tolerance", "medium"))
    locked: Set[date] = set()
    black: Set[date] = set()
    for s in prefs.get("locked_dates") or []:
        try:
            locked.add(date.fromisoformat(str(s)[:10]))
        except ValueError:
            pass
    for s in prefs.get("blackout_dates") or []:
        try:
            black.add(date.fromisoformat(str(s)[:10]))
        except ValueError:
            pass

    calendar = compute_daily_prices(
        listing,
        min_price=min_p,
        max_price=max_p,
        user_base=float(base) if base else None,
        pricing_goal=goal,
        risk=risk,
        start=start,
        days=min(max(days, 7), 90),
        locked_dates=locked,
        blackout_dates=black,
        kill_switch=bool(state.get("kill_switch")),
    )

    suggested_try = round((min_p + max_p) / 2, 2)
    _events.publish("pricing.viewed", {"listing_id": listing_id})

    return {
        "listing": {
            "id": listing.listing_id,
            "name": str(row.get("NAME") or "")[:120],
            "neighbourhood_group": listing.neighbourhood_group,
            "room_type": listing.room_type,
        },
        "settings": prefs,
        "suggested_try_price": suggested_try,
        "kill_switch_active": bool(state.get("kill_switch")),
        "calendar": calendar,
    }


@app.post("/api/host/settings/{listing_id}")
@limiter.limit("30/minute")
def save_host_settings(
    request: Request, listing_id: str, body: HostSettingsBody, _: str = require_admin
) -> Dict[str, Any]:
    if body.max_price <= body.min_price:
        raise HTTPException(status_code=400, detail="max_price must be greater than min_price")
    if body.smart_pricing_enabled and body.min_price <= 0:
        raise HTTPException(status_code=400, detail="min/max required when Smart Pricing is on")

    prefs = {
        "smart_pricing_enabled": body.smart_pricing_enabled,
        "min_price": body.min_price,
        "max_price": body.max_price,
        "base_price": body.base_price,
        "pricing_goal": body.pricing_goal,
        "risk_tolerance": body.risk_tolerance,
        "update_frequency": body.update_frequency,
        "discount_floor_protection": body.discount_floor_protection,
        "locked_dates": body.locked_dates,
        "blackout_dates": body.blackout_dates,
    }
    _storage.set_host_prefs(listing_id, prefs)
    _log("host_settings_saved", {"listing_id": listing_id})
    _events.publish("host.settings_saved", {"listing_id": listing_id})
    return {"ok": True, "settings": prefs}


@app.post("/api/simulation/run")
@limiter.limit("60/minute")
def simulation_run(request: Request, body: SimulationBody) -> Dict[str, Any]:
    df = get_df()
    hit = df[df["id"].astype(str) == str(body.listing_id)]
    if hit.empty:
        raise HTTPException(status_code=404, detail="Listing not found")
    row = hit.iloc[0]
    listing = row_to_listing(row)
    demand = 1.02

    model_result = decide_simulation(
        listing=listing,
        min_price=max(20.0, listing.base_anchor * 0.6),
        max_price=listing.base_anchor * 1.5,
        conversion_model=_conversion_model,
    )

    if _conversion_model is not None:
        # Use real model when present.
        feats = {
            "price": float(body.custom_price),
            "review_rate": float(listing.review_rate or 0.0),
            "reviews_count": float(listing.reviews_count or 0.0),
            "availability_365": float(listing.availability_365 or 0.0),
            "instant_bookable": 1.0 if bool(listing.instant_bookable) else 0.0,
            "room_type_private": 1.0 if "private" in (listing.room_type or "").lower() else 0.0,
            "room_type_shared": 1.0 if "shared" in (listing.room_type or "").lower() else 0.0,
            "room_type_entire": 1.0 if "entire" in (listing.room_type or "").lower() else 0.0,
        }
        prob = float(_conversion_model.predict_proba(feats))
    else:
        prob = booking_probability_mock(body.custom_price, listing.base_anchor, demand)

    er = expected_revenue(body.custom_price, prob)
    _events.publish("simulation.ran", {"listing_id": body.listing_id, "price": body.custom_price})
    alts = sorted(
        [
            round(body.custom_price * 0.95, 2),
            body.custom_price,
            round(body.custom_price * 1.05, 2),
        ]
    )
    top3 = []
    for pr in alts:
        if _conversion_model is not None:
            feats = {
                "price": float(pr),
                "review_rate": float(listing.review_rate or 0.0),
                "reviews_count": float(listing.reviews_count or 0.0),
                "availability_365": float(listing.availability_365 or 0.0),
                "instant_bookable": 1.0 if bool(listing.instant_bookable) else 0.0,
                "room_type_private": 1.0 if "private" in (listing.room_type or "").lower() else 0.0,
                "room_type_shared": 1.0 if "shared" in (listing.room_type or "").lower() else 0.0,
                "room_type_entire": 1.0 if "entire" in (listing.room_type or "").lower() else 0.0,
            }
            p = float(_conversion_model.predict_proba(feats))
        else:
            p = booking_probability_mock(pr, listing.base_anchor, demand)
        top3.append(
            {"price": pr, "booking_probability": round(p, 4), "expected_revenue": round(expected_revenue(pr, p), 2)}
        )
    top3.sort(key=lambda x: x["expected_revenue"], reverse=True)
    return {
        "listing_id": body.listing_id,
        "custom_price": body.custom_price,
        "booking_probability": round(prob, 4),
        "expected_revenue": round(er, 2),
        "top_alternatives": top3[:3],
        "decision_engine": None
        if model_result is None
        else {
            "action": model_result.action,
            "recommended_price": None if model_result.price is None else round(model_result.price, 2),
            "conversion": None if model_result.conversion is None else round(model_result.conversion, 4),
            "expected_revenue": None
            if model_result.expected_revenue is None
            else round(model_result.expected_revenue, 2),
            "model_used": model_result.model_used,
        },
    }


@app.get("/api/admin/status")
@limiter.limit("30/minute")
def admin_status(request: Request, _: str = require_admin) -> Dict[str, Any]:
    df = get_df()
    state = _storage.get_state()
    return {
        "kill_switch": bool(state.get("kill_switch")),
        "regional_override": state.get("regional_override"),
        "listings_loaded": int(len(df)),
        "recent_audit": _storage.recent_audit(20),
    }


@app.post("/api/admin/kill-switch")
@limiter.limit("30/minute")
def kill_switch(request: Request, body: KillSwitchBody, _: str = require_admin) -> Dict[str, Any]:
    _storage.set_state(kill_switch=bool(body.enabled), regional_override=body.region)
    _log("kill_switch", {"enabled": body.enabled, "region": body.region})
    _events.publish("admin.kill_switch", {"enabled": body.enabled, "region": body.region})
    state = _storage.get_state()
    return {"ok": True, "kill_switch": bool(state.get("kill_switch"))}


# --- Static frontend (production): set SMART_PRICING_WEB_DIST to built Vite folder ---
_dist = os.environ.get("SMART_PRICING_WEB_DIST", str(ROOT / "frontend" / "dist"))
_static_path = Path(_dist)
if _static_path.exists():
    app.mount("/", StaticFiles(directory=str(_static_path), html=True), name="static")
else:

    @app.get("/")
    def root() -> Dict[str, Any]:
        return {
            "name": "Smart Pricing API (lodging demo)",
            "docs": "/docs",
            "hint": "Build UI: cd frontend && npm install && npm run build — then open http://127.0.0.1:8000 again. "
            "Or dev: cd frontend && npm run dev (proxies /api to :8000).",
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
