# FloodSaathi — UI Design Document

> **Hackathon Edition** · Version 1.0 · References: PRD.md

---

## Design Principles

1. **Emergency-first legibility** — text ≥ 16 px body, ≥ 20 px headings; no decorative fonts.
2. **High contrast** — all text/background combinations meet WCAG AA (4.5:1 ratio).
3. **Mobile-friendly** — single-column layout at 360 px; sidebar collapses to a top menu on small screens.
4. **Hindi + English toggle** — every label, badge, and generated alert has both strings; UI language is toggled from the sidebar.
5. **Progressive disclosure** — raw data is hidden behind expanders; actionable information is front-and-centre.
6. **Offline-graceful** — stale-data banners instead of blank screens; cached maps always render.

---

## Color System

### Risk Palette

| Level | English | Hindi | Hex | Tailwind-equiv |
|-------|---------|-------|-----|----------------|
| Low | Low | कम | `#22C55E` | `green-500` |
| Medium | Medium | मध्यम | `#EAB308` | `yellow-500` |
| High | High | अधिक | `#F97316` | `orange-500` |
| Severe | Severe | गंभीर | `#EF4444` | `red-500` |

### Neutral Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `bg-dark` | `#0F172A` | Page background (dark mode) |
| `bg-card` | `#1E293B` | Card / sidebar background |
| `text-primary` | `#F1F5F9` | Body text on dark |
| `text-secondary` | `#94A3B8` | Metadata, timestamps |
| `border` | `#334155` | Card borders, dividers |
| `accent-blue` | `#3B82F6` | Shelter lines, links |
| `accent-teal` | `#14B8A6` | Volunteer lines |
| `accent-amber` | `#F59E0B` | Hospital lines |

### Status / Urgency

| Urgency | Colour | Label |
|---------|--------|-------|
| 1–2 | `#22C55E` | Low |
| 3 | `#EAB308` | Moderate |
| 4 | `#F97316` | High |
| 5 | `#EF4444` | Critical |

---

## Typography

| Role | Font | Size | Weight |
|------|------|------|--------|
| App title | System sans-serif | 24 px | 700 |
| Page heading | System sans-serif | 20 px | 600 |
| Section heading | System sans-serif | 16 px | 600 |
| Body / labels | System sans-serif | 15 px | 400 |
| Badge text | System sans-serif | 13 px | 700 |
| Monospace (JSON) | `monospace` | 13 px | 400 |

Streamlit default font stack is acceptable; override with `st.markdown` CSS injection for badge sizes only.

---

## Page Wireframes (ASCII)

### Page 1 — Home / Risk Map

```
┌─────────────────────────────────────────────────────────────────────┐
│  🌊 FloodSaathi            [EN | HI toggle]          [⚠ 3 Critical] │
├──────────────────┬──────────────────────────────────────────────────┤
│  SIDEBAR         │  RISK MAP                                        │
│                  │                                                  │
│  District        │  ┌─────────────────────────────────────────┐    │
│  [Dropdown ▼]    │  │                                         │    │
│                  │  │   [FOLIUM MAP — full width]             │    │
│  Map Layers      │  │                                         │    │
│  ☑ Hospitals     │  │   ● District cells coloured by risk     │    │
│  ☑ Shelters      │  │   ● Hover tooltip: "Severe — river      │    │
│  ☑ Volunteers    │  │     discharge 3× normal"                │    │
│  ☐ Requests      │  │                                         │    │
│                  │  │   [Legend: ■Low ■Med ■High ■Severe]     │    │
│  Last updated    │  └─────────────────────────────────────────┘    │
│  10:04 AM        │                                                  │
│  [Refresh ↺]     │  DISTRICT SUMMARY CARDS (horizontal scroll)     │
│                  │  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  [View Forecast] │  │Darbhanga │ │Morigaon  │ │Patna     │        │
│  [Submit Help]   │  │ SEVERE ■ │ │ HIGH  ■  │ │ MED   ■  │        │
│                  │  │ 3 open   │ │ 1 open   │ │ 0 open   │        │
│                  │  └──────────┘ └──────────┘ └──────────┘        │
└──────────────────┴──────────────────────────────────────────────────┘
```

---

### Page 2 — Help Request

```
┌─────────────────────────────────────────────────────────────────────┐
│  🌊 FloodSaathi  >  Submit Help Request                             │
├──────────────────┬──────────────────────────────────────────────────┤
│  SIDEBAR         │  SUBMIT A HELP REQUEST                           │
│  (same as P1)    │                                                  │
│                  │  Type your message in Hindi, English or Hinglish │
│                  │  ┌─────────────────────────────────────────┐    │
│                  │  │ "bhaiya paani ghar mein ghus gaya,      │    │
│                  │  │  5 log hain, ek budhiya hai..."         │    │
│                  │  └─────────────────────────────────────────┘    │
│                  │                                                  │
│                  │  Example messages:  [Example 1] [Example 2]     │
│                  │                                                  │
│                  │  [  Submit / भेजें  ]                           │
│                  │                                                  │
│                  │  ── PARSED REQUEST ──────────────────────────── │
│                  │  ┌─────────────────────────────────────────┐    │
│                  │  │ 📍 Location:   Morigaon, Assam           │    │
│                  │  │ 🚨 Urgency:    ■ 5 — Critical            │    │
│                  │  │ 🆘 Need:       Rescue                    │    │
│                  │  │ 👥 People:     5                          │    │
│                  │  │ ⚠️  Vulnerable: Elderly                  │    │
│                  │  │ 📝 Summary EN: Family trapped, 1 elderly │    │
│                  │  │ 📝 Summary HI: परिवार फंसा, 1 बुजुर्ग   │    │
│                  │  │ [▶ View raw JSON]                        │    │
│                  │  └─────────────────────────────────────────┘    │
│                  │                                                  │
│                  │  ── ASSIGNED RESOURCES ─────────────────────── │
│                  │  🏥 Hospital:  Morigaon District Hosp (1.2 km) │
│                  │  🏠 Shelter:   Govt School, Ward 4  (0.8 km)   │
│                  │  🙋 Volunteer: Arjun Singh, SEEDS   (0.3 km)   │
│                  │  [View on Map →]                                │
└──────────────────┴──────────────────────────────────────────────────┘
```

---

### Page 3 — Coordinator Dashboard

```
┌─────────────────────────────────────────────────────────────────────┐
│  🌊 FloodSaathi  >  Coordinator Dashboard       [Priya IAS, DM]    │
├──────────────────┬──────────────────────────────────────────────────┤
│  SIDEBAR         │  OPEN REQUESTS (sorted by urgency ▼)            │
│  Filter by:      │                                                  │
│  District [▼]    │  ┌─────────────────────────────────────────┐    │
│  Urgency  [▼]    │  │ ID   │Urgency│Location      │Need  │ETA │    │
│  Status   [▼]    │  ├─────────────────────────────────────────┤    │
│                  │  │ #042 │ ■ 5  │Morigaon Rd 3 │Rescue│8m  │    │
│  [Export CSV]    │  │ #039 │ ■ 4  │Darbhanga Blk │Med   │15m │    │
│  [Run Match ▶]   │  │ #037 │ ■ 4  │Patna Sector 7│Food  │12m │    │
│                  │  │ #031 │ ■ 3  │Muzaffarpur   │Shelt │20m │    │
│  STATS           │  └─────────────────────────────────────────┘    │
│  Total open: 14  │                                                  │
│  Critical:  3    │  ASSIGNMENTS TABLE                               │
│  Volunteers: 6   │  ┌─────────────────────────────────────────┐    │
│  Shelters:  4    │  │ Req │ Volunteer        │ Shelter     │Dist│    │
│  available  │  ├─────────────────────────────────────────┤    │
│                  │  │ #42 │ Arjun Singh      │ G.School W4 │0.8 │    │
│                  │  │ #39 │ Meena Devi       │ PHC Block B │1.2 │    │
│                  │  └─────────────────────────────────────────┘    │
│                  │                                                  │
│                  │  MAP (request pins + assignment lines)          │
│                  │  ┌─────────────────────────────────────────┐    │
│                  │  │  [FOLIUM MAP — colour lines to resources]│    │
│                  │  └─────────────────────────────────────────┘    │
└──────────────────┴──────────────────────────────────────────────────┘
```

---

### Page 4 — Alerts

```
┌─────────────────────────────────────────────────────────────────────┐
│  🌊 FloodSaathi  >  Alerts                                          │
├──────────────────┬──────────────────────────────────────────────────┤
│  SIDEBAR         │  GENERATE DISTRICT ALERT                        │
│  (same as P1)    │                                                  │
│                  │  District: [Morigaon        ▼]                  │
│                  │  Risk Level: [Severe         ▼]                  │
│                  │  Channel:  [Public / Volunteer / All ▼]         │
│                  │                                                  │
│                  │  [Generate Alert / अलर्ट बनाएं]                  │
│                  │                                                  │
│                  │  ── ENGLISH ─────────────────────────────────── │
│                  │  ┌─────────────────────────────────────────┐    │
│                  │  │ ⚠️  SEVERE FLOOD ALERT — Morigaon        │    │
│                  │  │ River discharge is 3× normal levels.    │    │
│                  │  │ Evacuate low-lying areas immediately.   │    │
│                  │  │ Report to: Govt School, Ward 4          │    │
│                  │  │ Helpline: 1070 (NDMA)                   │    │
│                  │  └─────────────────────────────────────────┘    │
│                  │                                                  │
│                  │  ── HINDI ───────────────────────────────────── │
│                  │  ┌─────────────────────────────────────────┐    │
│                  │  │ ⚠️  गंभीर बाढ़ चेतावनी — मोरीगांव        │    │
│                  │  │ नदी का जलस्तर सामान्य से 3 गुना है।     │    │
│                  │  │ निचले इलाकों से तुरंत निकलें।           │    │
│                  │  │ यहाँ जाएं: सरकारी स्कूल, वार्ड 4        │    │
│                  │  │ हेल्पलाइन: 1070 (NDMA)                  │    │
│                  │  └─────────────────────────────────────────┘    │
│                  │                                                  │
│                  │  [📤 Mock Send Alert]  ← does not send real SMS │
│                  │                                                  │
│                  │  ALERT HISTORY                                   │
│                  │  ┌─────────────────────────────────────────┐    │
│                  │  │ 09:45 │ Morigaon │ Severe │ Sent (mock) │    │
│                  │  │ 08:30 │ Darbhanga│ High   │ Sent (mock) │    │
│                  │  └─────────────────────────────────────────┘    │
└──────────────────┴──────────────────────────────────────────────────┘
```

---

## Reusable Components

### `RiskBadge`
```
Props: level ("low"|"medium"|"high"|"severe"), lang ("en"|"hi")
Renders: coloured pill with icon + label
Example: [■ Severe / गंभीर]
States: normal, pulsing (for severe, animate on dashboard)
```

### `RequestCard`
```
Props: request (parsed JSON), compact (bool)
Renders:
  Header: #ID — urgency badge — need type
  Body:   location, people_count, vulnerable_groups
  Footer: timestamp, status chip, [Assign] button
States: new (white border), assigned (teal border), resolved (grey, faded)
```

### `ResourceMarker`
```
Folium marker with custom icon per type:
  Hospital  → red cross icon, popup: name + distance
  Shelter   → blue house icon, popup: name + capacity
  Volunteer → green person icon, popup: name + skills
```

---

## Empty / Loading / Error States

| State | Trigger | UI |
|-------|---------|-----|
| **Loading** | API call in progress | `st.spinner("Fetching data…")` centred on card area |
| **Empty** | No requests in queue | Illustration + "No open requests in this district" |
| **Stale cache** | API failed, using cache | Yellow banner: "⚠ Showing cached data from HH:MM" |
| **Error** | Unrecoverable exception | Red banner: "Unable to load data. Retry or contact admin." + traceback hidden behind expander |
| **Fallback triage** | Claude API unavailable | Orange banner: "Using keyword-based triage — verify results manually." |

---

## Accessibility Checklist

- [ ] All colour cues have a text/icon duplicate (never colour alone).
- [ ] Every interactive element has an `aria-label` via `st.button(help=…)`.
- [ ] Contrast ratio ≥ 4.5:1 for all text on background pairs (verify with contrast checker).
- [ ] Font size ≥ 15 px throughout; no `small` tags for critical info.
- [ ] Map tooltips repeat badge label in plain text.
- [ ] Hindi text uses Devanagari Unicode (no transliteration fallback for screen readers).
- [ ] Tab order follows visual top-to-bottom, left-to-right.
- [ ] Spinner announces loading state for screen readers via `st.status`.
