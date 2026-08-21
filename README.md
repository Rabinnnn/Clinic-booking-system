# Clinic Booking System

A full‑stack web application for managing appointments in a small clinic with 5 doctors. A patient can view available slots for each doctor, make a booking, reschedule or cancel the booking. A doctor can also view the appointments that they have.


**Live demo:** [https://clinic-booking-system-mhi3.onrender.com](https://clinic-booking-system-mhi3.onrender.com)

**Github repo** [https://github.com/Rabinnnn/Clinic-booking-system.git](https://github.com/Rabinnnn/Clinic-booking-system.git)

Note: The free tier postgres database on Render will expire on 19th September, 2026

---

## Table of Contents

- [Features](#features)
- [Technology Stack](#technology-stack)
- [System Design](#system-design)
- [API Endpoints](#api-endpoints)
- [Frontend Usage](#frontend-usage)
- [Local Development Setup](#local-development-setup)
- [Deployment & CI/CD](#deployment--cicd)
- [Testing](#testing)
- [License](#license)

---

## Features

### Patient View
- **Book appointments** – select a doctor, enter your name, pick a date, and click any free 30‑minute slot to book instantly.  
- **My upcoming appointments** – see all your future appointments sorted by date (closest first).  
- **Cancel** – provide a reason and cancel any appointment (soft delete – slot becomes bookable again).  
- **Reschedule** – choose a new date, see available slots, and pick a new time – all in one modal.

### Doctor View (secured)
- **Authentication** – access requires a registration number (`doc15/2026`) entered via a clean modal.  
- **View upcoming appointments** – see all future appointments for any doctor, with patient names and times.

### Core Logic
- **Working hours cap** – all slots are automatically restricted to **8:00 AM – 5:00 PM** (working hours).  
- **1‑hour advance buffer** – slots within 60 minutes of the current time are hidden and cannot be booked.  
- **Concurrency‑safe** – database‑level unique constraints prevent double‑booking, even under simultaneous requests.  
- **Atomic rescheduling** – rescheduling frees the original slot and claims the new one in a single transaction.


## Technology Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Django 4.2 + Django REST Framework |
| **Database** | PostgreSQL (Render managed) |
| **Frontend** | Django Templates, Bootstrap 5, Vanilla JavaScript |
| **Authentication** | Simple modal‑based token check (no password storage) |
| **CI/CD** | GitHub Actions (tests on PR, deploy on merge) |
| **Hosting** | Render.com (Web Service + PostgreSQL) |
| **Static Serving** | WhiteNoise |




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
- **Decision**: No separate table for time slots. Instead, for a given doctor and date, generate all possible 30‑minute slots programmatically from `working_hours_start` to `working_hours_end`, then subtract already‑booked slots by querying the `Appointment` table.
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
- **Why**: Avoids timezone confusion, especially as the clinic might operate across timezones in the future. 

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
| **Django vs. other frameworks** | Django + DRF | Although Go is faster since it's a compiled language, Django provides a convenient framework architecture that makes development simple and quick. It also has a rich ecosystem. |




## Section 2 – API Endpoints

All endpoints return JSON and use standard HTTP status codes.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/appointments` | Book a slot. Body: `{"doctor_id": int, "patient_id": int, "start_time": "ISO datetime"}` |
| `GET` | `/api/doctors/{id}/availability?date=YYYY-MM-DD` | List free slots for a doctor on a date. |
| `PATCH` | `/api/appointments/{id}/cancel` | Cancel an appointment. Body: `{"reason": "string"}` |
| `PATCH` | `/api/appointments/{id}/reschedule` | Reschedule to a new slot. Body: `{"new_start_time": "ISO datetime"}` |
| `GET` | `/api/patients/{id}/appointments` | Upcoming appointments for a patient (sorted by date). |
| `GET` | `/api/doctors/{id}/appointments` | Upcoming appointments for a doctor (used in Doctor View). |
| `GET` | `/api/doctors` | List all doctors (for dropdowns). |
| `GET` | `/api/patients` | List all patients (for dropdowns). |

**Error responses** include a meaningful `error` field and appropriate status codes (400, 404, 409).

---

## Frontend Usage

### Patient View
1. **Select a doctor** from the dropdown.  
2. **Enter your name** (if new, a patient record is created automatically).  
3. **Pick a date** (future dates only).  
4. **Click "Check Availability"** – free slots appear as clickable tiles.  
5. **Click a slot** to book instantly – you’ll see a success message and the list of your upcoming appointments updates.

### Doctor View
1. **Click the "Doctor View" tab**.  
2. **Enter the registration number** (`doc15/2026` – this is a demo credential).  
3. **Select a doctor** from the dropdown and click **"Load Appointments"**.  
4. All upcoming appointments for that doctor are displayed, with patient names and actions to cancel/reschedule.

Both views support **cancellation** (with a reason prompt) and **rescheduling** (via a modal with slot picking).

---

## Local Development Setup

### Prerequisites
- Python 3.11+
- PostgreSQL
- `git`

### Steps
1. **Clone the repository:**
```bash
git clone https://github.com/Rabinnnn/Clinic-booking-system.git
cd clinic-booking-system
```

2. **Create and activate virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate 
# On Windows use source .venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set environment variables** - create a .env file with the following contents
```bash
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=postgres://postgres:your-password@localhost:5432/clinic_db
```
make sure you have created the 'clinic_db' database.

5. **Run migrations and seed data**
```bash
python manage.py migrate
# create sample data for doctors, patients, and appointments
python manage.py populate_data   
```

6. **Start the development server**
```bash
python manage.py runserver
```
Visit http://127.0.0.1:8000/ – the frontend will be served at the root.


## Section 3 – Deployment & CI/CD

### Public URL
The application is deployed on Render at:
https://clinic-booking-system-mhi3.onrender.com

### Branch Strategy
- main – production branch. All code is merged here via Pull Requests.

- Feature branches – new features or fixes are developed in a separate branch.

## CI/CD Pipeline (GitHub Actions)
The pipeline is defined in .github/workflows/ci-cd.yml and does the following:

1. On every Pull Request targeting main:

- Runs the test suite (30+ tests) against a PostgreSQL test container.

- Ensures all migrations and checks pass.

2. On a successful merge to main:

- Runs the test suite again (for safety).

- Triggers a deployment hook on Render, which pulls the latest main branch, runs migrations, collects static files, and restarts the service.

## Environment Variables (on Render)
- DATABASE_URL – connection string for the managed PostgreSQL instance.

- SECRET_KEY – a long random string.

- DEBUG – set to False in production.

- ALLOWED_HOSTS – includes clinic-booking-system-mhi3.onrender.com.

## Testing
The project uses Django’s built‑in test framework. All core logic, models, and API endpoints are covered by 30+ tests.

### Run tests locally
```bash
python manage.py test
```

## Project Structure
```bash
.
├── clinic_booking/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── doctors/
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── frontend/
│   ├── migrations/
│   ├── static/
│   ├── templates/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── patients/
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── appointments/
│   ├── migrations/
│   ├── management/commands/populate_data.py
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── services.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── manage.py
├── .gitignore
├── README.md
├── AI_REFLECTION.md
├── runtime.txt
└── requirements.txt
```

## Section 4 – AI REFLECTION 
(check the AI REFLECTION.md file)