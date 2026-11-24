# Stylify: 2-3 Minute Project Demonstration Video Script

**Target Duration**: 2 minutes 45 seconds  
**Tone**: Professional, technical, concise, and academic.  
**Presenter**: Lead Developer / Student Presenter

---

## Scene 1: Introduction & The Core Problem (0:00 - 0:30)

| Timestamp | Visual / Screen Action | Spoken Voiceover Narration |
| :--- | :--- | :--- |
| **0:00 - 0:15** | Browser open on Stylify Home (`/`). Smooth scroll down to highlight value props. | *"Hello everyone. Welcome to the demonstration of Stylify: our Intelligent Salon Scheduling and Appointment Platform. Salon booking systems routinely suffer from two critical flaws: double-booking race conditions during peak traffic, and rigid interfaces that fail to recommend optimal times based on client loyalty and stylist workload."* |
| **0:15 - 0:30** | Switch to the Services page (`/services`). Click category filters ("Hair", "Color", "Nails"). | *"Stylify solves this by pairing a deterministic pure Python slot engine with PostgreSQL mathematical exclusion constraints, a 5-minute pre-booking hold mechanism, and an explainable AI booking assistant."* |

---

## Scene 2: Conversational AI Assistant & Intent Parsing (0:30 - 1:05)

| Timestamp | Visual / Screen Action | Spoken Voiceover Narration |
| :--- | :--- | :--- |
| **0:30 - 0:45** | Click the floating purple **"Ask Stylify AI"** button. The chat drawer slides open. Type: *"Can I get balayage highlights next Monday under $160?"* | *"Let's test our AI Booking Assistant. Instead of navigating dropdowns, a customer types plain English. Stylify uses a hybrid natural language parser with fuzzy service matching, date normalization, and budget constraints."* |
| **0:45 - 1:05** | Chat replies with parsed intent and 3 recommended cards with scores and plain-language reasons. Click **"Book this slot"** on the first pick. | *"Notice the crucial safety guarantee: the assistant extracted service, date, and budget, but NEVER creates booking rows directly. It provides explainable picks, like '+3 Loyalty match' and '+2 Preferred afternoon'. Clicking 'Book this slot' loads directly into our 5-step booking wizard."* |

---

## Scene 3: Booking Wizard, 5-Minute Hold & Concurrency Guard (1:05 - 1:40)

| Timestamp | Visual / Screen Action | Spoken Voiceover Narration |
| :--- | :--- | :--- |
| **1:05 - 1:20** | Wizard Step 3 loads available 15-minute slots. Click a slot (e.g. 10:00 AM). Step 4 opens with the **HoldCountdown** timer running (`04:58...`). | *"When a client selects a slot, Stylify immediately generates a 5-minute database hold. Other clients visiting this page now see this slot removed from availability, eliminating checkout collisions. Notice the live countdown banner."* |
| **1:20 - 1:40** | Click **"Confirm Booking"**. Step 5 displays green confirmation checkmark with Booking `#101`. Switch to terminal and highlight `btree_gist` constraint. | *"Clicking confirm converts the hold into a confirmed appointment. Under the hood, PostgreSQL's `btree_gist` exclusion constraint guarantees that even if two simultaneous network requests arrive at the exact microsecond, exactly one succeeds and the other receives HTTP 409 SLOT_TAKEN."* |

---

## Scene 4: Cancellation, Waitlist Cascade & Notifications (1:40 - 2:10)

| Timestamp | Visual / Screen Action | Spoken Voiceover Narration |
| :--- | :--- | :--- |
| **1:40 - 1:55** | Go to `/my-bookings`. Click **"Cancel"** on an appointment. Confirmation modal opens and is submitted. | *"Now let's observe our automated waitlist cascade. Clients can queue for fully booked dates. When an appointment is cancelled outside the 2-hour window, Stylify instantly finds the earliest matching waitlist entry."* |
| **1:55 - 2:10** | Open another customer session. The Notification Bell badge lights up with **"1 new"**. Open `/waitlist` to reveal the **"Claim Slot (15-min Window)"** banner. | *"The waitlisted customer receives an in-app alert and has a 15-minute exclusive window to claim the newly opened slot before it cascades to the next client in FIFO order."* |

---

## Scene 5: Administrator Portal & Visual Analytics (2:10 - 2:35)

| Timestamp | Visual / Screen Action | Spoken Voiceover Narration |
| :--- | :--- | :--- |
| **2:10 - 2:25** | Log in as Admin (`admin@stylify.com`) and navigate to `/admin/dashboard`. Hover over Recharts area chart and weekly heatmap. | *"For salon managers, our Admin Portal provides real-time operational analytics powered by Recharts: daily booking trends, gross revenue by service, stylist utilization percentages, and a weekly day-by-hour heatmap."* |
| **2:25 - 2:35** | Click **"Stylist Calendar"** tab (`/admin/calendar`). Show FullCalendar column per stylist. Click **"Export Bookings CSV"**. | *"FullCalendar displays dedicated columns for Jordan, Taylor, and Morgan, providing complete schedule visibility. One click downloads a complete bookings CSV for accounting."* |

---

## Scene 6: Architecture, Testing & Conclusion (2:35 - 2:45)

| Timestamp | Visual / Screen Action | Spoken Voiceover Narration |
| :--- | :--- | :--- |
| **2:35 - 2:45** | Display VS Code terminal running `pytest` (`99 passed`) and GitHub Actions badge. Return to Stylify landing page. | *"Stylify is verified by a 99-test comprehensive test suite with 92% core engine coverage, deployed on Supabase, Render, and Vercel. Thank you for watching!"* |
