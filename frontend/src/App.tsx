import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CalendarDay,
  fetchAdmin,
  fetchListings,
  fetchPricing,
  ListingSummary,
  runSimulation,
  saveHostSettings,
  setKillSwitch,
} from "./api";

type Tab = "host" | "sim" | "admin";

function formatMoney(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
}

export default function App() {
  const [tab, setTab] = useState<Tab>("host");
  const [listings, setListings] = useState<ListingSummary[]>([]);
  const [listingId, setListingId] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [smartOn, setSmartOn] = useState(true);
  const [minP, setMinP] = useState<number>(80);
  const [maxP, setMaxP] = useState<number>(400);
  const [baseP, setBaseP] = useState<number | "">("");
  const [goal, setGoal] = useState("balanced");
  const [risk, setRisk] = useState("medium");
  const [freq, setFreq] = useState("daily");
  const [discountFloor, setDiscountFloor] = useState(true);
  const [lockedDates, setLockedDates] = useState("");
  const [blackoutDates, setBlackoutDates] = useState("");

  const [suggested, setSuggested] = useState<number | null>(null);
  const [killActive, setKillActive] = useState(false);
  const [calendar, setCalendar] = useState<CalendarDay[]>([]);
  const [listingName, setListingName] = useState("");

  const [modalDay, setModalDay] = useState<CalendarDay | null>(null);

  const [simPrice, setSimPrice] = useState<number>(200);
  const [simResult, setSimResult] = useState<{
    booking_probability: number;
    expected_revenue: number;
    top_alternatives: { price: number; booking_probability: number; expected_revenue: number }[];
  } | null>(null);

  const [admin, setAdmin] = useState<{
    kill_switch: boolean;
    listings_loaded: number;
    recent_audit: { ts: string; action: string }[];
  } | null>(null);

  const loadListings = useCallback(async () => {
    setErr(null);
    const items = await fetchListings();
    setListings(items);
    setListingId((prev) => prev || (items.length ? items[0].id : ""));
  }, []);

  const loadPricing = useCallback(async () => {
    if (!listingId) return;
    setLoading(true);
    setErr(null);
    try {
      const d = await fetchPricing(listingId, 60);
      setListingName(d.listing.name);
      setSuggested(d.suggested_try_price);
      setKillActive(d.kill_switch_active);
      setCalendar(d.calendar);
      const s = d.settings as Record<string, unknown>;
      setSmartOn(Boolean(s.smart_pricing_enabled ?? true));
      setMinP(Number(s.min_price ?? 80));
      setMaxP(Number(s.max_price ?? 400));
      setBaseP(s.base_price != null ? Number(s.base_price) : "");
      setGoal(String(s.pricing_goal ?? "balanced"));
      setRisk(String(s.risk_tolerance ?? "medium"));
      setFreq(String(s.update_frequency ?? "daily"));
      setDiscountFloor(Boolean(s.discount_floor_protection ?? true));
      setLockedDates(Array.isArray(s.locked_dates) ? (s.locked_dates as string[]).join(", ") : "");
      setBlackoutDates(Array.isArray(s.blackout_dates) ? (s.blackout_dates as string[]).join(", ") : "");
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }, [listingId]);

  useEffect(() => {
    loadListings().catch((e) => setErr(String(e)));
  }, []);

  useEffect(() => {
    if (listingId) loadPricing().catch((e) => setErr(String(e)));
  }, [listingId, loadPricing]);

  const parseDateList = (s: string) =>
    s
      .split(/[,;\s]+/)
      .map((x) => x.trim())
      .filter(Boolean);

  const onSaveSettings = async () => {
    if (!listingId) return;
    if (smartOn && maxP <= minP) {
      setErr("Max price must be greater than min price.");
      return;
    }
    setErr(null);
    setLoading(true);
    try {
      await saveHostSettings(listingId, {
        smart_pricing_enabled: smartOn,
        min_price: minP,
        max_price: maxP,
        base_price: baseP === "" ? null : baseP,
        pricing_goal: goal,
        risk_tolerance: risk,
        update_frequency: freq,
        discount_floor_protection: discountFloor,
        locked_dates: parseDateList(lockedDates),
        blackout_dates: parseDateList(blackoutDates),
      });
      await loadPricing();
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  };

  const onSim = async () => {
    if (!listingId) return;
    setErr(null);
    setLoading(true);
    try {
      const r = await runSimulation(listingId, simPrice);
      setSimResult(r);
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  };

  const onLoadAdmin = async () => {
    setErr(null);
    try {
      const a = await fetchAdmin();
      setAdmin(a);
    } catch (e) {
      setErr(String(e));
    }
  };

  useEffect(() => {
    if (tab === "admin") onLoadAdmin().catch((e) => setErr(String(e)));
  }, [tab]);

  const weekRows = useMemo(() => {
    const rows: CalendarDay[][] = [];
    if (!calendar.length) return rows;
    let row: CalendarDay[] = [];
    const first = new Date(calendar[0].date + "T12:00:00");
    const pad = first.getDay();
    for (let i = 0; i < pad; i++) row.push({ date: "", recommended_price: null, confidence: 0, tags: [], components: {}, blocked: true } as CalendarDay);
    calendar.forEach((d) => {
      row.push(d);
      if (row.length === 7) {
        rows.push(row);
        row = [];
      }
    });
    if (row.length) {
      while (row.length < 7) row.push({ date: "", recommended_price: null, confidence: 0, tags: [], components: {}, blocked: true } as CalendarDay);
      rows.push(row);
    }
    return rows;
  }, [calendar]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <h1>Smart Pricing</h1>
          <span>Lodging nightly rates · guardrails · explainability</span>
        </div>
        <nav className="tabs" aria-label="Primary">
          <button type="button" className={tab === "host" ? "active" : ""} onClick={() => setTab("host")}>
            Host
          </button>
          <button type="button" className={tab === "sim" ? "active" : ""} onClick={() => setTab("sim")}>
            Simulation
          </button>
          <button type="button" className={tab === "admin" ? "active" : ""} onClick={() => setTab("admin")}>
            Admin
          </button>
        </nav>
      </header>

      {err && <div className="err">{err}</div>}

      {tab === "host" && (
        <div className="grid host">
          <div className="card">
            <h2>Listing</h2>
            <label htmlFor="listing">Select listing</label>
            <select
              id="listing"
              value={listingId}
              onChange={(e) => setListingId(e.target.value)}
              disabled={loading}
            >
              {listings.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name.slice(0, 50)} — {l.neighbourhood}
                </option>
              ))}
            </select>
            <p className="hint">{listingName}</p>

            <div className="switch-row" style={{ marginTop: 16 }}>
              <div>
                <strong>Smart Pricing</strong>
                <div className="hint">Requires min/max when enabled</div>
              </div>
              <button
                type="button"
                className={`switch ${smartOn ? "on" : ""}`}
                aria-pressed={smartOn}
                onClick={() => setSmartOn(!smartOn)}
              />
            </div>

            <div className="row2" style={{ marginTop: 12 }}>
              <div>
                <label>Min price</label>
                <input type="number" value={minP} onChange={(e) => setMinP(Number(e.target.value))} disabled={!smartOn} />
              </div>
              <div>
                <label>Max price</label>
                <input type="number" value={maxP} onChange={(e) => setMaxP(Number(e.target.value))} disabled={!smartOn} />
              </div>
            </div>

            <div style={{ marginTop: 12 }}>
              <label>Base price (optional anchor)</label>
              <input
                type="number"
                value={baseP === "" ? "" : baseP}
                placeholder="e.g. 250"
                onChange={(e) => setBaseP(e.target.value === "" ? "" : Number(e.target.value))}
              />
            </div>

            {suggested != null && (
              <p className="hint">
                Suggested try: <strong>{formatMoney(suggested)}</strong>
              </p>
            )}

            {killActive && <span className="badge warn">Kill switch active — prices frozen</span>}

            <h2 style={{ marginTop: 20 }}>Preferences</h2>
            <div className="row2">
              <div>
                <label>Pricing goal</label>
                <select value={goal} onChange={(e) => setGoal(e.target.value)}>
                  <option value="revenue">Revenue</option>
                  <option value="occupancy">Occupancy</option>
                  <option value="balanced">Balanced</option>
                </select>
              </div>
              <div>
                <label>Risk tolerance</label>
                <select value={risk} onChange={(e) => setRisk(e.target.value)}>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
            </div>
            <div style={{ marginTop: 12 }}>
              <label>Update frequency</label>
              <select value={freq} onChange={(e) => setFreq(e.target.value)}>
                <option value="hourly">Hourly</option>
                <option value="daily">Daily</option>
                <option value="event_driven">Event-driven</option>
              </select>
            </div>

            <div className="switch-row">
              <div>
                <strong>Discount floor protection</strong>
                <div className="hint">Prevent promos below min unless allowed</div>
              </div>
              <button
                type="button"
                className={`switch ${discountFloor ? "on" : ""}`}
                aria-pressed={discountFloor}
                onClick={() => setDiscountFloor(!discountFloor)}
              />
            </div>

            <div style={{ marginTop: 12 }}>
              <label>Locked dates (YYYY-MM-DD, comma-separated)</label>
              <textarea value={lockedDates} onChange={(e) => setLockedDates(e.target.value)} placeholder="2026-04-01, 2026-04-02" />
            </div>
            <div style={{ marginTop: 12 }}>
              <label>Blackout dates</label>
              <textarea value={blackoutDates} onChange={(e) => setBlackoutDates(e.target.value)} placeholder="2026-12-24" />
            </div>

            <button type="button" className="btn primary" style={{ marginTop: 16, width: "100%" }} onClick={onSaveSettings} disabled={loading || (smartOn && maxP <= minP)}>
              Save & refresh preview
            </button>
          </div>

          <div className="card">
            <div className="calendar-head">
              <h2 style={{ margin: 0 }}>Price preview (60 days)</h2>
              <span className="badge">Click a day for breakdown</span>
            </div>
            <div className="calendar-grid" style={{ marginBottom: 8 }}>
              {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
                <div key={d} className="dow">
                  {d}
                </div>
              ))}
            </div>
            {weekRows.map((wr, ri) => (
              <div key={ri} className="calendar-grid" style={{ marginBottom: 6 }}>
                {wr.map((cell, ci) => {
                  if (!cell.date) return <div key={ci} className="day-cell" style={{ visibility: "hidden" }} />;
                  const blocked = cell.blocked;
                  const d = new Date(cell.date + "T12:00:00");
                  return (
                    <button
                      type="button"
                      key={cell.date}
                      className={`day-cell ${blocked ? "blackout" : ""}`}
                      onClick={() => !blocked && cell.recommended_price != null && setModalDay(cell)}
                      disabled={blocked || cell.recommended_price == null}
                    >
                      <div className="day-num">{d.getDate()}</div>
                      {blocked ? (
                        <div className="day-price" style={{ fontSize: "0.8rem" }}>
                          —
                        </div>
                      ) : (
                        <>
                          <div className="day-price">{formatMoney(cell.recommended_price!)}</div>
                          <div className="day-meta">{(cell.confidence * 100).toFixed(0)}% conf</div>
                          <div className="day-meta">{cell.tags.slice(0, 2).join(" · ")}</div>
                        </>
                      )}
                    </button>
                  );
                })}
              </div>
            ))}
            {!calendar.length && <p className="hint">Loading calendar…</p>}
          </div>
        </div>
      )}

      {tab === "sim" && (
        <div className="card" style={{ maxWidth: 640 }}>
          <h2>Simulation (Jira Epic 5)</h2>
          <p className="hint">POST /api/simulation/run — custom price vs booking probability & expected revenue</p>
          <div className="row2">
            <div>
              <label>Listing</label>
              <select value={listingId} onChange={(e) => setListingId(e.target.value)}>
                {listings.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.id}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label>Custom price ($)</label>
              <input type="number" value={simPrice} onChange={(e) => setSimPrice(Number(e.target.value))} />
            </div>
          </div>
          <button type="button" className="btn primary" style={{ marginTop: 14 }} onClick={onSim} disabled={loading || !listingId}>
            Run simulation
          </button>
          {simResult && (
            <div style={{ marginTop: 20 }}>
              <div className="stat-grid">
                <div className="stat">
                  <div className="v">{(simResult.booking_probability * 100).toFixed(1)}%</div>
                  <div className="k">Booking probability</div>
                </div>
                <div className="stat">
                  <div className="v">{formatMoney(simResult.expected_revenue)}</div>
                  <div className="k">Expected revenue</div>
                </div>
              </div>
              <h3 style={{ marginTop: 20, fontSize: "1rem" }}>Top alternatives</h3>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
                <thead>
                  <tr style={{ color: "var(--muted)", textAlign: "left" }}>
                    <th style={{ padding: "8px 0" }}>Price</th>
                    <th>P( book )</th>
                    <th>E[ revenue ]</th>
                  </tr>
                </thead>
                <tbody>
                  {simResult.top_alternatives.map((a) => (
                    <tr key={a.price}>
                      <td style={{ padding: "6px 0" }}>{formatMoney(a.price)}</td>
                      <td>{(a.booking_probability * 100).toFixed(1)}%</td>
                      <td>{formatMoney(a.expected_revenue)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === "admin" && (
        <div className="grid">
          <div className="card">
            <h2>Admin & observability (Epic 7)</h2>
            <p className="hint">Kill switch + audit trail (demo)</p>
            <div className="stat-grid" style={{ marginTop: 12 }}>
              <div className="stat">
                <div className="v">{admin?.listings_loaded ?? "—"}</div>
                <div className="k">Listings in dataset</div>
              </div>
              <div className="stat">
                <div className="v">{admin?.kill_switch ? "ON" : "OFF"}</div>
                <div className="k">Kill switch</div>
              </div>
            </div>
            <div style={{ marginTop: 16, display: "flex", gap: 12, flexWrap: "wrap" }}>
              <button
                type="button"
                className="btn"
                onClick={async () => {
                  await setKillSwitch(true);
                  await onLoadAdmin();
                  await loadPricing();
                }}
              >
                Enable kill switch
              </button>
              <button
                type="button"
                className="btn primary"
                onClick={async () => {
                  await setKillSwitch(false);
                  await onLoadAdmin();
                  await loadPricing();
                }}
              >
                Disable kill switch
              </button>
            </div>
          </div>
          <div className="card">
            <h2>Recent audit</h2>
            <ul style={{ margin: 0, paddingLeft: 18, color: "var(--muted)", fontSize: "0.9rem" }}>
              {(admin?.recent_audit ?? []).slice().reverse().map((a, i) => (
                <li key={i} style={{ marginBottom: 6 }}>
                  {a.ts} — {a.action}
                </li>
              ))}
            </ul>
            {!admin?.recent_audit?.length && <p className="hint">No events yet</p>}
          </div>
        </div>
      )}

      {modalDay && (
        <div className="modal-backdrop" role="dialog" aria-modal onClick={() => setModalDay(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>{modalDay.date}</h3>
            <p>
              <strong>{modalDay.recommended_price != null ? formatMoney(modalDay.recommended_price) : "—"}</strong> · Confidence{" "}
              {(modalDay.confidence * 100).toFixed(0)}%
            </p>
            <p className="hint">Tags: {modalDay.tags.join(", ")}</p>
            <h4 style={{ margin: "16px 0 8px" }}>Price components</h4>
            <div className="kv">
              {Object.entries(modalDay.components).map(([k, v]) => (
                <div key={k}>
                  <div>{k}</div>
                  <div>{typeof v === "number" ? v.toFixed(4) : String(v)}</div>
                </div>
              ))}
            </div>
            <button type="button" className="btn" style={{ marginTop: 16 }} onClick={() => setModalDay(null)}>
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
