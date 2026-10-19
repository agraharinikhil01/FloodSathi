# FloodSaathi — Product Requirements Document

> **Hackathon Edition** · Version 1.0 · 2026-10-19

---

## Vision

FloodSaathi ("Flood Companion") is a decision-support tool that gives flood-affected citizens, volunteers, and district coordinators a shared operational picture — turning fragmented WhatsApp messages and phone calls into structured, actionable data so help reaches the right people faster.

---

## Problem Statement

India's annual flood season (Assam, Bihar, Kerala) kills hundreds and displaces millions. Three failure modes repeat every year:

1. **Late warnings** — official IMD/NDMA alerts reach field coordinators hours after water levels are already dangerous.
2. **Scattered coordination** — rescue requests arrive as unstructured Hindi/English/Hinglish voice notes and texts across dozens of WhatsApp groups.
3. **Resource blindness** — volunteers, shelters, and boats have no shared map; duplication and gaps coexist in the same district.

---

## Personas

| Persona | Name | Context | Key Pain |
|---------|------|---------|----------|
| **Affected Citizen** | Riya, 34, Muzaffarpur | Sends "bhaiya paani ghar mein ghus gaya 5 log hain" from a feature phone | Does not know where to go or how to be found |
| **Volunteer / NGO** | Arjun, 28, SEEDS NGO | Manages a team of 12, gets 80 WhatsApp messages a day | Cannot prioritise or locate requests on a map |
| **District Coordinator** | Priya IAS, 41, District DM | Accountable for 500 000 people, no live dashboard | Relies on phone calls; cannot track resource deployment |

---

## User Stories

| ID | As a… | I want to… | So that… |
|----|--------|------------|----------|
| US-01 | Citizen | See the current risk level of my district on a colour-coded map | I can decide whether to evacuate before water rises |
| US-02 | Citizen | Submit a help request in Hindi, English, or Hinglish | I am understood even if I cannot type formally |
| US-03 | Volunteer | See all open requests ranked by urgency on a map | I go to the highest-priority case first |
| US-04 | Volunteer | Know which shelter or resource is assigned to a request | I do not waste time finding one myself |
| US-05 | Coordinator | View a 48-hour rain + river discharge forecast per district | I pre-position resources before the peak |
| US-06 | Coordinator | Generate a Hindi/English public alert for a district | I communicate consistently without drafting text manually |
| US-07 | Coordinator | See a queue of triaged requests with urgency and location | I can oversee the full district operation in one screen |

---

## MVP Features

### F1 — Risk Map
**Description:** A district-level grid coloured Low / Medium / High / Severe, updated every hour, with a one-sentence plain-language explanation of the dominant risk factor.

**Acceptance Criteria:**
- [ ] Every monitored district shows exactly one of four badge colours (green / yellow / orange / red).
- [ ] Clicking a district cell shows the explanation string, e.g. "River discharge 3× normal + 48 h cumulative rain > 150 mm."
- [ ] Map re-fetches risk scores on page load; cached data ≤ 1 h old is used if the API is unavailable.
- [ ] Colour scheme passes WCAG AA contrast ratio for all four levels.

---

### F2 — 48-Hour Forecast
**Description:** Per-district rain accumulation and river-discharge trend charts sourced from Open-Meteo Forecast and Open-Meteo Flood APIs, displayed as a 48-bar time series.

**Acceptance Criteria:**
- [ ] Chart shows 48 hourly bars for precipitation (mm) and river discharge (m³/s).
- [ ] If the live API call fails, a cached JSON file (`data/cache/`) is used and a banner reads "Showing cached data from [timestamp]."
- [ ] Each API call has a 5-second timeout and one automatic retry.
- [ ] Charts are legible at 360 px wide (mobile viewport).

---

### F3 — Help Request Triage
**Description:** A free-text box accepts Hindi, English, or Hinglish messages. Claude converts the message into a structured JSON object with fields: `location`, `urgency` (1–5), `need` (rescue / medical / food / shelter), `people_count`, `vulnerable_groups` (elderly / children / pregnant / disabled), `summary_en`, `summary_hi`.

**Acceptance Criteria:**
- [ ] System extracts all 7 fields for ≥ 27 / 30 labelled test messages (90 % accuracy).
- [ ] JSON card renders within 3 seconds of submission on a standard laptop.
- [ ] Urgency 4–5 requests are visually flagged in red immediately after parsing.
- [ ] If the Claude API is unavailable, a rule-based fallback extracts at least `urgency` and `need` using keyword matching.

---

### F4 — Resource Matching
**Description:** For each triaged request, the system assigns the nearest available shelter, hospital, and volunteer using Haversine distance, then plots a line on the Folium map between the request pin and each assigned resource.

**Acceptance Criteria:**
- [ ] Matching runs in < 10 seconds for a queue of 100 requests.
- [ ] Assignment respects volunteer `available` flag and shelter `capacity > 0`.
- [ ] Map lines are colour-coded by resource type (blue = shelter, green = volunteer, orange = hospital).
- [ ] Re-running matching on the same queue produces the same result (deterministic).

---

## Non-Goals

- **No real SMS sending** — the "Send Alert" button is a mock for the demo.
- **No real personal data** — all citizens in the demo are synthetic; no real phone numbers, names, or Aadhaar data are stored.
- **Not a replacement for IMD/NDMA** — FloodSaathi is a decision-support layer, not an authoritative warning system.
- **No multi-tenant auth** — a single shared coordinator login is sufficient for the hackathon.

---

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| Triage accuracy | ≥ 90 % (27/30 messages) | Manual label set in `tests/triage_labels.json` |
| Request-to-assignment time | < 10 s | Timed locally with `pytest` benchmark |
| Risk model validation | Risk level matches known severity for ≥ 3 districts in 2024 Assam flood | Manual cross-check against IMD bulletin |
| Map load time | < 4 s on a 4G connection | Streamlit profiler |

---

## Hackathon Timeline (24–48 Hours)

| Hour | Milestone |
|------|-----------|
| 0–2 | Repo scaffold, `.env.example`, DB schema, seed script |
| 2–6 | Open-Meteo + Flood API integration + caching |
| 6–10 | Risk scoring engine (rule-based) + Risk Map page |
| 10–14 | Claude triage integration + fallback keyword parser |
| 14–18 | Resource Matching engine + Folium map |
| 18–22 | Coordinator Dashboard + Alerts page |
| 22–26 | Forecast charts, Hindi/English toggle, UI polish |
| 26–30 | Tests, validation against 2024 Assam flood data |
| 30–36 | README, demo GIF, slide deck |
| 36–48 | Buffer: bug fixes, judge Q&A prep |

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Open-Meteo API rate-limit or downtime | Medium | High | Local JSON cache files in `data/cache/`; demo never fails |
| Claude API latency > 5 s | Medium | Medium | Streaming response + keyword-based fallback parser |
| Geocoding failure for Hinglish locations | High | Medium | Nominatim with fuzzy search; fallback to district centroid |
| SQLite concurrency under Streamlit reruns | Low | Medium | Single-writer pattern; WAL mode enabled |
| No real flood data to validate | Medium | Medium | Use 2024 Assam IMD bulletins as ground truth |
