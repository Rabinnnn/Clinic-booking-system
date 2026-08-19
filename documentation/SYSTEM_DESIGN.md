# Clinic Booking System

This is a platform that helps with booking appointments for a small clinic with 5 doctors. Patients can view free 30‑minute slots for a given doctor on a given day, book one, cancel, or reschedule. The design is built with Django and Django REST Framework (DRF), using PostgreSQL as the production database. 

---

## Section 1 – System Design


### 1. Data Models

We identify three core domain entities.

#### 1.1 Doctor
- **Purpose**: Represents a physician with fixed working hours.
- **Fields**:
  - `id` (auto‑generated primary key)
  - `name` – display name
  - `working_hours_start` – time of day when slots begin (e.g., 09:00)
  - `working_hours_end` – time of day when slots end (e.g., 17:00)
- **Assumptions**:
  - Working hours are the same for every weekday (we can later add `working_days` as a JSON field or a separate `Schedule` model if per‑day overrides are needed).
  - All doctors use 30‑minute slots; this is fixed by business rule.

#### 1.2 Patient
- **Purpose**: Represents a person who books appointments.
- **Fields**:
  - `id`, `name`, `email` (unique), `phone` (optional).
- **Assumptions**: Patients are registered before booking (simplified; no authentication required for this assessment).

#### 1.3 Appointment
- **Purpose**: The central record of a booking.
- **Fields**:
  - `id`
  - `doctor` – foreign key to `Doctor`
  - `patient` – foreign key to `Patient`
  - `start_time` – datetime (UTC)
  - `end_time` – datetime (UTC), computed as `start_time + 30 minutes`
  - `status` – choice of `scheduled` or `cancelled` (default `scheduled`)
  - `cancellation_reason` – text, nullable (only populated when status is `cancelled`)
  - `created_at`, `updated_at` – audit timestamps
- **Constraints**:
  - A partial unique constraint on `(doctor, start_time)` **only when `status = 'scheduled'`**. This prevents double‑booking at the database level while allowing multiple cancelled records for the same slot (for audit history).
  - Indexes on `(doctor, start_time)` for fast availability queries and on `patient` for the bonus endpoint.

---

### 2. Component Layers (Django‑style)

We separate responsibilities into clear layers to keep code maintainable and testable.

| Layer | Responsibility | Django/DRF implementation |
|-------|----------------|---------------------------|
| **Models** | Define data schema, relationships, and database‑level constraints. | `django.db.models` |
| **Serializers** | Validate incoming request data and shape outgoing JSON responses. | DRF `ModelSerializer` with custom `validate()` methods |
| **Views** | Handle HTTP requests, call service functions, and return HTTP responses. | DRF `APIView` (or `ViewSet`) – each endpoint has its own view |
| **Service layer** | Contains core business logic: availability generation, booking, cancellation, reschedule. | Plain Python functions in `appointments/services.py` (or similar) |
| **Exceptions** | Custom exception classes for domain errors (e.g., `SlotUnavailable`, `InvalidOperation`) mapped to HTTP status codes via a custom DRF exception handler. | `APIException` subclasses |
| **URLs** | Route endpoints to views. | `urlpatterns` in each app |

This layered approach keeps views thin, makes business logic reusable, and simplifies unit testing (we can test service functions without the HTTP layer).

---

### 3. Key Design Decisions

#### 3.1 On‑the‑fly Slot Generation
- **Decision**: We do **not** store a separate table of time slots. Instead, for a given doctor and date, we generate all possible 30‑minute slots programmatically from `working_hours_start` to `working_hours_end`, then subtract already‑booked slots by querying the `Appointment` table.
- **Why**:  
  - Simpler schema – fewer tables to manage.  
  - No need to pre‑fill slots for all future dates.  
  - Easier to handle changes in working hours (just update the doctor’s record; slots are recomputed on the fly).

#### 3.2 Database‑Level Concurrency Control
- **Decision**: We use a **partial unique constraint** on `(doctor, start_time)` for appointments with `status = 'scheduled'`.
- **Why**: This guarantees that even if two requests try to book the same slot simultaneously, only one will succeed; the other will raise a database integrity error, which we catch and translate to a 409 HTTP conflict. This is more reliable than application‑level locks.

#### 3.3 Atomic Reschedule
- **Decision**: The `reschedule` operation is wrapped in a single database transaction (`transaction.atomic()`). It cancels the original appointment and creates a new one (or updates the existing one) in one go.
- **Why**: Ensures that the original slot is freed and the new slot is claimed atomically – no intermediate state where both slots are unavailable or both are free.

#### 3.4 Timezone Handling
- **Decision**: All datetimes are stored in **UTC** in the database. The API accepts and returns ISO‑8601 datetimes with offset information (or assumes UTC). The validation checks (past, 1‑hour buffer) are performed against `timezone.now()` (UTC).
- **Why**: Avoids timezone confusion, especially as the clinic might operate across timezones in the future. The frontend can convert to local time for display.

#### 3.5 Keeping Historical Records
- **Decision**: When an appointment is cancelled or rescheduled, we do **not** delete the record – we change its status to `cancelled` and store a reason (when applicable).
- **Why**: Provides an audit trail for the clinic. The original slot becomes available again because we only consider `scheduled` records when checking availability.

---

### 4. Trade‑offs Considered

| Trade‑off | Chosen approach | Rationale |
|-----------|----------------|-----------|
| **Slot table vs. on‑the‑fly** | On‑the‑fly generation | Saves storage and simplifies maintenance. The slight CPU cost is negligible for 5 doctors and typical query rates. |
| **Application‑level vs. DB‑level locking** | DB‑level partial unique constraint | More robust; we avoid race conditions even under high load. The downside is that we must handle the database error gracefully in code. |
| **Single doctor per reschedule** | Reschedule keeps the same doctor | Simplifies implementation. If changing doctor becomes a requirement, we can extend the endpoint to accept an optional `doctor_id` later. |
| **All working days identical** | Assume same hours for all weekdays | Good for the MVP. If needed, we can replace with a `Schedule` model that defines exceptions, without breaking existing logic. |
| **Cancellation vs. deletion** | Soft cancellation (status change) | Preserves history and allows the slot to be re‑booked. The only “cost” is more rows, but that’s negligible. |
| **Django vs. other frameworks** | Django + DRF | Provides built‑in admin, ORM, migrations, and a mature ecosystem – speeds up development and reduces boilerplate. |

---

### 5. Growth & Extensibility

While starting small, the design accommodates future growth:

- **More doctors**: Simply add records – no code changes.
- **Different slot durations**: The duration is currently hard‑coded as 30 minutes, but it can be moved to a `Doctor` field if needed.
- **Working hour variations**: A `Schedule` model can override default hours for specific days or date ranges.
- **Authentication**: The API currently has no auth; we could add JWT or session‑based auth with minimal changes.
- **Notifications**: An event hook can be added after booking/cancellation to send emails or SMS.

---

## Section 2 – API Implementation

*(To be filled after code is written – will include endpoint descriptions, request/response examples, and setup instructions.)*

---

## Section 3 – Deployment & CI/CD

*(To be filled after deployment – will include public URL, branch strategy, and pipeline description.)*

---

## Local Development Setup

*(To be added – commands to set up virtual environment, install dependencies, run migrations, and start the dev server.)*