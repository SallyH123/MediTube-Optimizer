## MediTube Optimizer

**An Intelligent Medication Tubing and Workflow Optimization System for Hospital Pharmacies**

## Overview

MediTube Optimizer is a backend application designed to optimize medication tubing workflows in hospital pharmacies. The goal is to reduce unnecessary pneumatic tube deliveries, minimize medication delivery errors caused by patient transfers, and improve technician efficiency while ensuring that medications arrive on time.

This project was inspired by real-world challenges commonly faced in inpatient pharmacies, where technicians must constantly decide whether medications should be tubed immediately or temporarily held based on due times, patient locations, and medication priority.

MediTube Optimizer automatically evaluates medication orders, groups medications by tubing bins, and recommends the optimal time to send medications throughout the hospital.

The demo performs evaluation only: it prints the priority-sorted ready-to-tube bins and waits for an explicit tubing request. It does not mark or remove medications automatically.

---

## Problem Statement

Hospital pharmacies process hundreds of medication orders every day. Technicians frequently face several challenges:

- Multiple medications are due at different times for patients in the same unit.
- Patients may transfer to another room before a medication is delivered.
- Routine medications scheduled far in advance are often sent too early.
- STAT medications require immediate delivery.
- Emergency departments and perioperative areas have different turnaround expectations.
- Technicians must manually determine which medications should be tubed together.

Incorrect tubing decisions can result in:

- Delayed medication administration
- Medications sent to the wrong location
- Increased technician workload
- Additional phone calls and manual corrections

MediTube Optimizer aims to automate these decisions using configurable business rules.

---

## Key Features

### Medication Prioritization

When multiple bins need to be sent at the same time, PharmaFlow prioritizes medications in the following order:

1. STAT medications
2. IV medications
3. Oral medications

---

### Intelligent Hold Rules

Routine medications are generally held until they fall within the tubing window.

Special cutoff rules apply:

**Night cutoff**

- Medications due at 21:00 or later remain in the bin until 20:30.

**Morning cutoff**

- Medications due at 09:00 or later remain in the bin until 08:30.
All rules:
Standard units: 5-hour tubing window.
ED/ER/PERIOP: 1-hour tubing window.
Overdue medications: ready to tube.
Priority: STAT has the highest status priority, followed by route priority (IV, SUBQ/IM, inhaled, PO, topical).
Bin priority: highest medication priority + 50% of the sum of all medication priorities.
Transfer: check the patient's current location immediately before tubing and re-evaluate the destination bin.
Unknown room: goes to UNKNOWN rather than guessing.
Night cutoff: medications due at 21:00 are held until the 20:30 release threshold.
Day cutoff: same concept applies to the 09:00 day cutoff, with an 08:30 release threshold.
Final tubing: only medications that are currently eligible are tubed; the others remain for later.

---

### Unit-Specific Rules

#### Emergency Department (ED) and Perioperative Units

- Tube medications only if due within one hour.

#### Other Units (ICU, floor units)

- Standard tubing rules apply.

Supported units:

- ED
- PERIOP
- CVICU
- SICU
- MICU
- Unit 3
- Unit 4
- Unit 5
- Unit 6

---

### Patient Transfer Detection

Before tubing medications, PharmaFlow checks whether the patient has transferred to another location.

Example:

- Original room: 8012
- Patient transferred to: 7015

PharmaFlow automatically moves the medication from Bin 8 to Bin 7 before tubing.

---

### Manual Override

Technicians can manually override the system and send any bin immediately.

---

### Real-Time Tubing Dashboard (Future Development)

Future versions will include a visual dashboard showing:

- Current bins waiting to be tubed
- Medication priorities
- Patient room assignments
- Overdue medications
- Tubing recommendations
- One-click "Tube Now" actions.

---

## Project Structure

```text
pharmacy_tube_optimizer/
├── config.py
├── main.py
├── models/
├── rules/
├── services/
├── data/
├── utils/
└── tests/
```

---

## Run the Demo

```bash
python -m pharmacy_tube_optimizer.main
```

## REST API

The dependency-free WSGI application exposes `GET /bins`, `GET /bins/{bin_id}`, and `POST /bins/{bin_id}/tube`. The POST operation performs a fresh engine-owned transfer reconciliation and evaluation before tubing the selected bin.

```python
from wsgiref.simple_server import make_server
from pharmacy_tube_optimizer.api import create_app

make_server("127.0.0.1", 8000, create_app()).serve_forever()
```

& ".\.venv\Scripts\python.exe" -c "from wsgiref.simple_server import make_server; from pharmacy_tube_optimizer.api import create_app; make_server('127.0.0.1', 8000, create_app()).serve_forever()"
cd frontend
npm run dev
Local:   http://localhost:5173/