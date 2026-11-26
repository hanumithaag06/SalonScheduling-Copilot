# Stylify: Executive Presentation & Architectural Review

**Project Title**: Stylify: Intelligent Salon Scheduling and Appointment Management Platform  
**System Architecture**: Salon Scheduling Copilot & Concurrency Engine  
**Target Audience**: Executive Stakeholders, Technical Evaluators, and Engineering Leadership

---

### Slide 1: Title & Executive Summary
- **Title**: Stylify: Intelligent Salon Scheduling and Appointment Platform
- **Subtitle**: Collision-Free Booking, Explainable Recommendations, and AI Conversational Copilot
- **Engineering Team**: Stylify Platform Team
- **Key Highlights**:
  - Pure computational algorithm design with zero framework lock-in.
  - PostgreSQL mathematical exclusion locks eliminating double-booking race conditions.
  - 5-minute pre-booking holds, automated waitlist cascading, and full admin analytics.

---

### Slide 2: Problem Statement & Industry Bottlenecks
- **The Double-Booking Epidemic**:
  - Concurrent web users selecting the same slot at peak hours lead to double-bookings and customer churn.
- **Suboptimal Capacity Utilization**:
  - Static calendars leave fragmented 15–30 minute gaps that cannot accommodate longer services (e.g. balayage, keratin).
- **Manual Overhead**:
  - Salon staff spend 20+ hours weekly manually rescheduling cancellations and answering repetitive phone inquiries.
- **Black-Box AI Failures**:
  - Naive LLM chatbots hallucinate availability, create phantom appointments, and bypass business logic.

---

### Slide 3: Proposed System Architecture
- **Monolithic Clean Layered Architecture**:
  - **Client Tier**: React 19 + Tailwind CSS v4 + FullCalendar + Recharts (Vercel).
  - **API Tier**: FastAPI Async Monolith + Pydantic v2 + APScheduler (Render).
  - **Data Tier**: PostgreSQL 16 + `btree_gist` Exclusion Constraints (Supabase).
- **Core Design Principles**:
  - Pure Python functional core (`slot_engine`, `recommender`, `intent_parser`, `waitlist_engine`) completely decoupled from DB/HTTP for deterministic unit testability.
  - Strict UTC timestamp persistence; ISO-8601 boundary enforcement.

---

### Slide 4: Collision Prevention & Concurrency Guard
- **The Two-Tier Defense Model**:
  1. **Application-Level Pre-Flight Check**:
     - Slot engine verifies real-time gaps, lead times (min 30 min), buffer times (15 min), and active holds.
  2. **Database-Level Exclusion Lock (Final Barrier)**:
     ```sql
     ALTER TABLE bookings ADD CONSTRAINT no_overlapping_stylist_bookings
     EXCLUDE USING gist (
       stylist_id WITH =,
       tstzrange(start_ts, end_ts) WITH &&
     ) WHERE (status = 'confirmed');
     ```
- **Concurrency Test Verification**:
  - Two parallel asynchronous HTTP requests targeting the same slot: exactly 1 succeeds with HTTP 201; the second fails gracefully with HTTP 409 `SLOT_TAKEN`.

---

### Slide 5: Dynamic 15-Minute Slot Engine Algorithm
- **Algorithm Flow**:
  1. Retrieve stylist working hours for given weekday; filter out overlapping time-off entries.
  2. Overlay confirmed bookings and unexpired holds expanded by service duration and configurable buffers.
  3. Scan the working window in discrete 15-minute step increments: $t, t + 15, t + 30...$
  4. Ensure $[t, t + \text{duration}]$ is strictly contained within working hours and intersects zero busy intervals.
  5. Enforce minimum advance lead time against current UTC reference time.
- **Computational Complexity**:
  - $\mathcal{O}(N \log N + M)$ where $N$ is busy intervals and $M$ is total step intervals per working day.

---

### Slide 6: Explainable Recommender Engine
- **Why Rule-Based Over Black-Box ML?**:
  - Transparent, auditable, and instantly justifiable to examiners and customers.
- **Multi-Factor Scoring Formula**:
  $$\text{Score}(s, \text{slot}) = 3 \times \min\left(1.0, \frac{\text{past\_bookings}}{3}\right) + 2 \times \mathbb{I}(\text{time\_pref}) + 1 \times \mathbb{I}(\text{specialist}) + 1 \times \mathbb{I}(\text{gap\_fill})$$
- **Scoring Components**:
  - **+3 Client Loyalty**: Scaled boost based on past completed visits with that stylist (capped at 3).
  - **+2 Time Window Match**: Slot start hour aligns with client's preferred daypart (morning/afternoon/evening).
  - **+1 Specialization**: Stylist has specific service tags in their profile.
  - **+1 Calendar Optimization**: Slot is directly adjacent to an existing booking, preventing unbookable dead gaps.
- **Output**: Top 3 ranked picks, each paired with an auto-generated plain-language reasoning sentence.

---

### Slide 7: 5-Minute Holds & Automated Waitlist Cascade
- **Pre-Booking Holds (`POST /holds`)**:
  - Customer holds a chosen slot for 300 seconds while reviewing pricing and details.
  - Filtered out at read time by `slot_engine`; background APScheduler job purges expired records.
  - Converted into confirmed booking upon checkout via `hold_id`.
- **FIFO Waitlist Cascade**:
  - When a booking is cancelled, the system evaluates all eligible queue entries matching service, date, and time preference.
  - Earliest subscriber receives an exclusive 15-minute claim offer.
  - Unclaimed offers expire and automatically cascade to the next eligible customer.

---

### Slide 8: Conversational AI Booking Copilot
- **The Assistant Guardrail Boundary**:
  - Natural language models MUST NEVER write booking rows directly.
- **Extraction Schema**:
  - Extracts `{service, date, time_pref, max_price, missing_fields}` via JSON mode.
- **Local Fallback Engine**:
  - Operates 100% offline using `rapidfuzz` (token set ratio) and `dateparser` when `LLM_API_KEY` is not present.
- **Clarification Over Hallucination**:
  - If mandatory fields (`service` or `date`) are missing, the assistant asks a targeted follow-up question rather than guessing.

---

### Slide 9: Admin Operations & Visual Analytics
- **FullCalendar Multi-Stylist Resource Matrix**:
  - Individual vertical column per stylist (Jordan, Taylor, Morgan) showing concurrent day schedules.
- **Recharts Operational Dashboard**:
  - Daily booking volume trend line.
  - Gross revenue by service category bar chart.
  - Stylist capacity utilization rate percentage bars.
  - Weekly day-by-hour appointment intensity heatmap.
- **Admin Overrides**:
  - Proxy booking on behalf of walk-in or phone-in clients.
  - Emergency admin cancellation with immediate waitlist cascade.
  - One-click CSV export of complete booking ledgers.

---

### Slide 10: Testing, Verification & Viva Defense Summary
- **Test Metrics**:
  - **99 passing tests** across 15 test modules.
  - **Core Logic Coverage**: `intent_parser` (92%), `recommender` (94%), `slot_engine` (94%), `waitlist_engine` (93%), `analytics_service` (98%).
- **CI/CD Pipeline**:
  - GitHub Actions runs PostgreSQL service container, Alembic migrations, Pytest coverage, and Vite build on every push.
- **Conclusion**:
  - Stylify successfully proves that modern salon scheduling requires mathematical concurrency control, explainable algorithms, and guarded conversational AI.
