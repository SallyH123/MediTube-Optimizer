# MediTube Optimizer

## Overview

MediTube Optimizer is an intelligent medication-tubing and workflow optimization system for hospital pharmacies. It helps technicians decide **what to tube, when to tube it, and where it should go** by combining medication timing, priority, cutoff, bin, and patient-transfer information.

The project pairs a Python backend rules engine with a React tubing board. All clinical, timing, and transfer decisions are evaluated by the backend; the frontend presents that evaluated board state for the technician.

## Problem Statement

Hospital pharmacies process many medication orders with different due times, routes, priorities, and patient locations. Technicians must decide which orders can travel together, avoid sending routine doses too early, prioritize urgent medications, and account for patients who move after a medication is prepared.

Incorrect tubing decisions can delay administration, send medication to the wrong location, increase manual follow-up, and create unnecessary delivery work. MediTube Optimizer centralizes these checks into a clear, transfer-aware tubing workflow.

## Key Features

MediTube provides:

- grouping pending orders by physical tubing bin;
- identifying medications that are ready to tube now;
- ranking ready bins by medication priority;
- reconciling patient transfers before tubing;
- keeping unknown destinations in a separate handling queue; and
- preserving a backend-confirmed tubing history.

### Transfer-aware tubing

Before tubing, the backend compares the patient's previous and current room, determines the destination bin, and reconciles the medication location. The board displays the backend-generated transfer notification until that transferred order is successfully tubed.

### Priority and timing guidance

The backend identifies medications that are ready to tube now, ranks bins by priority, and keeps non-ready medications visible for later review. Within each bin, the interface places `TUBE NOW` medications first for faster scanning.

### Technician control

Evaluation never tubes medication automatically. A technician must explicitly select **TUBE**, or use a manual override when appropriate.

## Core workflow

1. The backend evaluates all pending medication orders.
2. Bins enter review when their closest dose is due within one hour.
3. Within a reviewed bin, each medication must satisfy its cutoff and unit-specific tubing window.
4. Before tubing, the backend checks for a patient transfer and moves the medication to the correct destination bin.
5. A technician selects **TUBE** or uses the manual override. Only an explicit action changes medication state.

## Rules at a glance

1. **Bin review gate**

   The engine first checks the earliest scheduled medication in each bin. A bin enters review only when that closest dose is due within one hour. This avoids repeatedly evaluating bins whose medications are still far from due.

2. **Cutoff release times**

   - Medications due from **21:00 through 08:59** are part of the night batch and release at **20:30** on the preceding evening.
   - Medications due from **09:00 through 20:59** are part of the day batch and release at **08:30** on their due date.

   Passing the time window alone is not enough: the medication must also have passed its applicable cutoff release time.

3. **Unit-specific tubing windows**

   After the bin is under review and the cutoff is released, each medication is evaluated individually.

   - Standard units, including ICU and floor bins, use a **five-hour** tubing window.
   - ED and PERIOP use a **one-hour** tubing window.
   - Overdue medications remain eligible for review and tubing.

4. **Medication priority score**

   A medication score is the sum of its status score and route score. `STAT` adds **100** points; `Routine` adds **0**. Route scores are: IV **30**, SUBQ/IM **20**, PO/Inhaler **10**, and topical **5**. For example, a STAT IV medication scores **130** (`100 + 30`), while a routine IV medication scores **30**.

5. **Bin priority score**

   Ready bins are ranked by `highest medication score + 50% of the sum of all medication scores in the bin`. This gives urgent medications the strongest influence while still rewarding bins that efficiently group several eligible medications.

6. **Patient transfers and unknown destinations**

   Immediately before tubing, the backend compares the previous and current patient room. If the patient moved, the engine determines the new destination bin and reconciles the medication before tubing. If the room cannot be mapped safely, the order remains in the separate `UNKNOWN` queue.

7. **Explicit tubing and override**

   Evaluation does not tube medication automatically. A technician must select **TUBE** to send currently eligible medications, or use a manual override when operationally appropriate.

## Demo board

The demo contains fixed cases for cutoff, transfer, route, priority, and unknown-destination review.

- `http://localhost:5173/cutoff-demo?time=2000` — 8:00 PM scenario
- `http://localhost:5173/cutoff-demo?time=2030` — 8:30 PM scenario

The transfer notification is generated by the backend. It remains visible after reconciliation so repeated board reads do not hide it, and it is removed once the transferred order is successfully tubed.

## Run locally

### 1. Start the backend

Create and activate a virtual environment, then install the project requirements:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run the API server:

```powershell
.\.venv\Scripts\python.exe -c "from wsgiref.simple_server import make_server; from pharmacy_tube_optimizer.api import create_app; make_server('127.0.0.1', 8000, create_app()).serve_forever()"
```

The API is then available at `http://127.0.0.1:8000`.

### 2. Start the frontend

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite, normally `http://localhost:5173`.

If the frontend is served separately from the backend, set `VITE_API_BASE_URL` to the backend origin before starting Vite.

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/bins` | Return the complete evaluated board. |
| `GET` | `/bins/{bin_id}` | Return one bin and active transfer notifications. |
| `POST` | `/bins/{bin_id}/tube` | Re-check transfers and tube eligible orders in a bin. |
| `POST` | `/bins/{bin_id}/force-tube` | Apply a technician-approved tubing override. |
| `POST` | `/simulation/refresh` | Add a generated medication batch to the live simulation. |
| `GET` | `/demo/bins?time=2000` | Return the fixed 8:00 PM demo board. |
| `GET` | `/demo/bins?time=2030` | Return the fixed 8:30 PM demo board. |

## Project layout

```text
pharmacy_tube_optimizer/
├── api/        # WSGI routes and response composition
├── data/       # Demo data, generated data, and transfer fixtures
├── models/     # Medication, patient-location, and bin domain models
├── rules/      # Pure timing, priority, cutoff, and transfer rules
├── services/   # Evaluation, state, tubing, and override workflows
└── tests/      # Unit and integration coverage

frontend/
└── src/        # React tubing-board interface
```

## Tests

Run the backend test suite from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest pharmacy_tube_optimizer\tests -q
```
