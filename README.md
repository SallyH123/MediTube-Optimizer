## MediTube Optimizer

**An Intelligent Medication Tubing and Workflow Optimization System for Hospital Pharmacies**

## Overview

MediTube Optimizer is a backend application designed to optimize medication tubing workflows in hospital pharmacies. The goal is to reduce unnecessary pneumatic tube deliveries, minimize medication delivery errors caused by patient transfers, and improve technician efficiency while ensuring that medications arrive on time.

This project was inspired by real-world challenges commonly faced in inpatient pharmacies, where technicians must constantly decide whether medications should be tubed immediately or temporarily held based on due times, patient locations, and medication priority.

MediTube Optimizer automatically evaluates medication orders, groups medications by tubing bins, and recommends the optimal time to send medications throughout the hospital.

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
