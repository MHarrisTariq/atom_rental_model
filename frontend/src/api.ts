const API = "";

export type ListingSummary = {
  id: string;
  name: string;
  neighbourhood: string;
  neighbourhood_group: string;
  room_type: string;
  price: number;
};

export type CalendarDay = {
  date: string;
  recommended_price: number | null;
  confidence: number;
  tags: string[];
  components: Record<string, number>;
  blocked?: boolean;
};

export async function fetchListings(): Promise<ListingSummary[]> {
  const r = await fetch(`${API}/api/listings`);
  if (!r.ok) throw new Error(await r.text());
  const j = await r.json();
  return j.listings as ListingSummary[];
}

export async function fetchPricing(listingId: string, days = 60): Promise<{
  listing: { id: string; name: string; neighbourhood_group: string; room_type: string };
  settings: Record<string, unknown>;
  suggested_try_price: number;
  kill_switch_active: boolean;
  calendar: CalendarDay[];
}> {
  const r = await fetch(`${API}/api/pricing/${listingId}?days=${days}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function saveHostSettings(
  listingId: string,
  body: Record<string, unknown>
): Promise<void> {
  const r = await fetch(`${API}/api/host/settings/${listingId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
}

export async function runSimulation(
  listingId: string,
  customPrice: number
): Promise<{
  booking_probability: number;
  expected_revenue: number;
  top_alternatives: { price: number; booking_probability: number; expected_revenue: number }[];
}> {
  const r = await fetch(`${API}/api/simulation/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ listing_id: listingId, custom_price: customPrice }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function fetchAdmin(): Promise<{
  kill_switch: boolean;
  listings_loaded: number;
  recent_audit: { ts: string; action: string }[];
}> {
  const r = await fetch(`${API}/api/admin/status`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function setKillSwitch(enabled: boolean, region?: string): Promise<void> {
  const r = await fetch(`${API}/api/admin/kill-switch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled, region: region || null }),
  });
  if (!r.ok) throw new Error(await r.text());
}
