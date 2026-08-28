# System Architecture: British Auction in RFQ System

This document provides a comprehensive analysis of the architectural design, directory boundaries, key components, data flow logic, database schemas, and verification algorithms implemented in the British Auction RFQ System.

---

## 1. High-Level Architectural Overview

The application utilizes a modular, decoupled layered architecture comprising:
1. **Presentation Layer (Frontend):** React 18/19 SPA powered by Vite, utilizing Axios for REST service consumption.
2. **API & Request Validation Layer (Backend Router):** FastAPI with Pydantic v2 schemas validating request structures.
3. **Core Business & Service Logic Layer (Services):** Dedicated services for database CRUD operations, deterministic reverse auction bid ranking, and timeline extension algorithms.
4. **Data Access & Storage Layer (ORM & DB):** SQLAlchemy 2.0 ORM executing queries on a PostgreSQL database, managed by Alembic migrations.

```
                  ┌───────────────────────────────┐
                  │     React + Vite Frontend     │
                  └───────────────┬───────────────┘
                                  │ JSON over HTTP REST
                                  ▼
                  ┌───────────────────────────────┐
                  │      FastAPI API Routers      │
                  └───────────────┬───────────────┘
                                  │ Validate Payload (Pydantic)
                                  ▼
                  ┌───────────────────────────────┐
                  │  Business Logic / Services    │
                  └───────────────┬───────────────┘
                                  │ Query & Transaction Scopes
                                  ▼
                  ┌───────────────────────────────┐
                  │     SQLAlchemy 2.0 ORM        │
                  └───────────────┬───────────────┘
                                  │ PostgreSQL Driver (psycopg2)
                                  ▼
                  ┌───────────────────────────────┐
                  │      PostgreSQL Database      │
                  └───────────────────────────────┘
```

---

## 2. Directory Structure & Boundaries

```text
british-auction-rfq/
│
├── backend/
│   ├── app/
│   │   ├── api/routes/          # HTTP request extraction, deserialization, & status mapping.
│   │   ├── core/                # Settings management and environment variables initialization.
│   │   ├── db/                  # Connection engine and session lifecycle dependencies.
│   │   ├── models/              # SQLAlchemy database mapping entities.
│   │   ├── schemas/             # Pydantic validation input/output structures.
│   │   └── services/            # Implementation of core domain algorithms.
│   ├── alembic/                 # Alembic migration scripts and environment setups.
│   └── tests/                   # Pytest automated test scripts.
│
├── frontend/
│   ├── src/
│   │   ├── components/          # Reusable presentation widgets.
│   │   ├── pages/               # Route view components mapping URL paths.
│   │   ├── services/            # API client configurations (Axios wrappers).
│   │   └── App.jsx              # Main routing tree configuration.
```

---

## 3. Key Bidding & Business Rules

### A. Bid Submission Validation
Whenever a supplier submits a bid, the backend validation pipeline executes the following checks:
1. **RFQ Context Check:** Confirms the RFQ exists and is currently in `AUCTION_ACTIVE` or `PUBLISHED` status.
2. **Supplier Association Check:** Confirms the supplier is invited to that specific RFQ (`rfq_suppliers` association).
3. **Price Ceiling Constraint:** Validates that the bid `amount` is strictly below the RFQ's `baseline_price`.
4. **Timeline Check:** Enforces that the bid is submitted after the auction `start_time` and before the current auction `end_time`.
5. **Forced Close Check:** Rejects any bid submitted after the absolute `forced_bid_close_time` limit.

### B. Reverse Auction Bid Ranking
Ranks are calculated dynamically based on the lowest submitted bid amount.
- **Rank Ordering:** Sorted by `amount` ascending (lowest bid is Rank 1, L1).
- **Tie-Breaking Rule:** Resolved deterministically by the earliest `submitted_at` timestamp. If timestamps are identical, the system uses the alphabetical ordering of bid `UUID`s.

### C. Time Extension Engine
To prevent sniping, bids received near the close time extend the auction:
- **Trigger Window:** The final `X` minutes of the scheduled closing time (`end_time`).
- **Extension Duration:** Adds `Y` minutes to the current `end_time` if an extension triggers.
- **Trigger Modes:**
  1. `BID_RECEIVED`: Any valid bid placed within the window triggers an extension.
  2. `ANY_RANK_CHANGE`: An extension triggers only if the bid shifts the relative rank of any active supplier.
  3. `L1_RANK_CHANGE`: An extension triggers only if the bid updates the L1 (Rank 1, lowest price) supplier.
- **Hard Boundary Capping:** If the extended `end_time` exceeds `forced_bid_close_time`, the system caps the new close time exactly at `forced_bid_close_time`. No further extensions can occur after this boundary is reached.

---

## 4. Database Schema Relationships

- **`buyers` & `rfqs`:** One-to-many relationship. A buyer hosts multiple RFQs.
- **`rfqs` & `rfq_items`:** One-to-many. An RFQ contains multiple detail line items.
- **`rfqs` & `suppliers`:** Many-to-many relationship resolved through the `rfq_suppliers` invitation join table.
- **`rfqs` & `auctions`:** One-to-one relationship. An RFQ contains one active config and scheduler.
- **`auctions` & `auction_rounds`:** One-to-many. An auction divides its lifespan into chronological round records.
- **`auctions` & `bids`:** One-to-many. An auction collects multiple bids from invited suppliers.
- **`rfqs` & `activity_logs`:** One-to-many. An audit log record tracking actions and triggers.

---

## 5. Security & Concurrency Controls
- **Environment Isolation:** Secrets and passwords are kept out of source control. Environment configurations are loaded from system parameters using `Pydantic Settings`.
- **Relational Integrity:** Cascading deletes are enforced on associated child tables (`rfq_items`, `auctions`, `bids`) to prevent database orphans.
- **Unique Constraints:** The database enforces a `UNIQUE(auction_id, supplier_id)` constraint on bids to prevent duplicate entries from the same supplier within the same auction context.
