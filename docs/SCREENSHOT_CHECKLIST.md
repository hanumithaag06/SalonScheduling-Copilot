# Stylify: Submission Screenshot Checklist

This checklist documents the essential screenshots required for the academic project submission, final viva presentation, and examiner evaluation portfolio.

---

## 1. Customer Experience Flow

- [ ] **SS-01: Landing Page (`/`)**
  - **View**: Hero banner with gradient styling, quick booking call-to-actions, and core value proposition cards (Zero Double-Booking, Explainable Recommendations, 5-Minute Holds).
  - **Key Details**: Clean Tailwind typography and bottom-right floating AI Assistant badge.

- [ ] **SS-02: Services & Stylists Showcase (`/services`)**
  - **View**: Catalog grid with category filter tabs ("All", "Hair", "Color", "Treatments", "Nails"), duration badges, prices, and stylist experience cards.
  - **Key Details**: "Book This Service" CTA on service cards.

- [ ] **SS-03: Booking Wizard — Slot Calculation & Recommendations (`/book` Step 3)**
  - **View**: Available 15-minute slot blocks returned by `slot_engine.py` alongside the purple **"Top Recommended Picks for You"** card.
  - **Key Details**: Recommendation score badges (`+3 Loyalty match`, `+2 Matches preferred morning`) and plain-language reasoning strings.

- [ ] **SS-04: Booking Wizard — Active 5-Minute Pre-Booking Hold (`/book` Step 4)**
  - **View**: Visual `HoldCountdown` component with real-time `mm:ss` countdown timer banner, appointment summary details, and "Confirm Booking" button.
  - **Key Details**: Proves that the slot is locked in the database prior to final checkout.

- [ ] **SS-05: Booking Wizard — Confirmation Screen (`/book` Step 5)**
  - **View**: Green checkmark modal with generated appointment ID (`#101`), stylist, duration, and status `CONFIRMED`.

- [ ] **SS-06: Customer Appointment Management (`/my-bookings`)**
  - **View**: List of upcoming and past customer bookings with status badges (`CONFIRMED`, `CANCELLED`).
  - **Key Details**: Reschedule modal open showing new date/time slot picker, and cancellation window warning banner.

- [ ] **SS-07: Waitlist & Offer Claim (`/waitlist`)**
  - **View**: Waitlist submission form, active queue entries, and the pulsing **"Claim Slot (15-min Window)"** banner on an offered opening.

- [ ] **SS-08: Header Notification Bell Dropdown**
  - **View**: Expanded bell dropdown in the navigation bar showing unread badges, booking confirmations, and waitlist offer alerts.

- [ ] **SS-09: Conversational AI Booking Assistant (`AssistantChat.jsx`)**
  - **View**: Open chat drawer on the bottom-right showing user natural language prompt:
    `"Deluxe cut and styling next Tuesday morning max 80"`
  - **Key Details**: Extracted intent bubble, explainable slot cards, and architectural safety banner: *"Assistant provides suggestions. Confirmations happen on review."*

---

## 2. Administrator Operations Portal

- [ ] **SS-10: Admin Analytics Dashboard (`/admin/dashboard`)**
  - **View**: Four top KPI cards (Total Bookings, Total Revenue, Cancellation Rate, Stylist Load %).
  - **Key Details**: Recharts Bookings per Day area chart, Revenue per Service bar chart, and Stylist Utilization percentage bars.

- [ ] **SS-11: Weekly Day-by-Hour Heatmap Grid (`/admin/dashboard`)**
  - **View**: Color-intensity matrix showing appointment density across Monday–Sunday and hours 09:00 to 18:00.

- [ ] **SS-12: Stylist Daily Calendar (`/admin/calendar`)**
  - **View**: FullCalendar `resourceTimeGridDay` view featuring vertical columns for each stylist (Jordan Master, Taylor Fade, Morgan Colorist) with colored appointment event blocks.

- [ ] **SS-13: Admin Bookings Ledger & Proxy Booking (`/admin/bookings`)**
  - **View**: Comprehensive tabular ledger with status/stylist filters, "Export Bookings CSV" button, and open "Book on Behalf of Client" modal.

---

## 3. Terminal & Quality Verification

- [ ] **SS-14: Test Suite Terminal Output**
  - **View**: Terminal screenshot of `pytest --cov=app --cov-report=term-missing` displaying:
    `99 passed in 31.31s` with pure engine coverage >= 92%.

- [ ] **SS-15: Database Exclusion Constraint Verification**
  - **View**: `psql` or pgAdmin terminal showing `\d bookings` with `btree_gist` exclusion constraint:
    `EXCLUDE USING gist (stylist_id WITH =, tstzrange(start_ts, end_ts) WITH &&) WHERE (status = 'confirmed')`
