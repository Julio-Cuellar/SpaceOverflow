# Project context: health monitoring for astronauts (NASA Space Apps 2026)

> Context document for a Claude Code agent. It summarizes everything decided, researched and proposed up to Nov 14, 2026, 14:22 (Mexico City time). The team's living source is the "spaceApps" page in Notion; this file consolidates it and corrects its inconsistencies (see section 14).

## 0. How to use this document

**Rules for the agent:**

1. Always distinguish between what is **decided**, what is **researched** (with a source), what is **suggested** (ideas from the team or the assistant, not closed) and what is **unverified**. Each section marks this.
2. Do not invent medical thresholds. Every value that has no verified source in section 5 is written as a **demonstration parameter** and labeled as such in the code and in the interface.
3. Do not make decisions from section 12 (open questions) without asking the user. If the user is not available, choose the most conservative option and leave it noted.
4. The system is a **decision-support prototype**, not a medical device or a diagnostic tool. This must be visible in the interface and in the README.
5. The user speaks Spanish. Interface texts and documentation are written in English in this repository unless indicated otherwise. Ask whether a Spanish version is needed.

**Status legend used throughout the document:**

| Mark | Meaning |
| --- | --- |
| `DECIDED` | The user confirmed it. |
| `VERIFIED` | Read directly in a NASA document cited in this file. |
| `TB` | Read in a Technical Brief (OCHMO), a reference document derived from the standard, "for reference only". |
| `SUGGESTED` | Idea discussed but not closed. |
| `DEMO` | Value invented or assumed for the demonstration. It must be labeled as such. |
| `NO VERIFIED` | Said in the conversation or found in searches, without having opened the source. |

---

## 1. The hackathon and the challenge

- **Event:** NASA International Space Apps Challenge 2026, theme "The Next Frontier". Dates: **November 14 and 15, 2026**, 48 hours.
- **Chosen challenge:** *Create Health Monitoring Software for Astronauts on Space Missions*. Topics: Human Exploration, Software, Space Exploration. Difficulty stated by local organizers: intermediate.
- **Official text (summary of the challenge page, quoted by a local event page):**
  - *Problem:* long missions expose astronauts to space radiation, isolation and confinement, altered gravity and a hostile closed environment. This can bring immune changes, bone loss, cardiovascular events and behavioral health problems. Astronauts bear much of the responsibility for detecting those changes in themselves.
  - *Goal:* build software that gathers health indicators and lets astronauts assess and act on the state of their health.
- **The full official challenge page could not be read** (`https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/`): the reading tool blocked it. Its data resources and official evaluation criteria are not known. **Pending: a person should read it and compare it with this document.**
- **Award criteria** (from a third-party repository, `NO VERIFIED`): best use of science, best use of data, best use of technology, among others.
- **Competition:** at least ten public repositories from other teams solve this same challenge. Most are a dashboard with simulated vital signs and threshold alerts. See section 11 for how to stand out.

---

## 2. Product concept

**Core idea (`DECIDED`):** a system that crosses **body sensors** with **cabin sensors** to generate alerts and measures to activate, and that works **autonomously on board**, without depending on the ground link to mission control.

- **Main user:** the astronaut, not mission control. Mission control is a secondary observer when there is a connection.
- **Body sensors:** heart rate, blood pressure, blood oxygenation (SpO₂), body temperature, hours of sleep, mood. The team's handwritten note also mentions blood sugar (see section 5.6 on its availability on board).
- **Cabin sensors:** oxygen, CO₂, internal pressure, and optionally temperature, humidity, noise and radiation.
- **Example alerts mentioned by the user:** high or low oxygen, CO₂ at a certain level, percentage of the mission's total oxygen already consumed, and activation of measures.
- **Value of crossing body and environment:** NASA warns that many symptoms attributed to CO₂ are also caused by fluid shift in microgravity, and that fixed sensors do not see local pockets of CO₂. Crossing data makes it possible to say "the probable origin is the air, not the astronaut" or the reverse. (`TB`, CO₂ Technical Brief.)

**Features wanted by the team (handwritten note, `DECIDED` as a wish list):**

- Gamification to help astronauts complete tasks that support their health.
- Dynamic charts with the evolution of the indicators over time.
- Color coding to interpret health at a glance.
- Simple explanations of measurements, indicators and risks, because astronauts do not know everything about how to assess their health.
- Show the information in different environments: ship, station, rover or lunar or planetary base.
- Reminders that prompt completing health actions as part of the routine.

**Questions the tool must be able to answer (from the handwritten note):**

1. What measurements can be made in space?
2. Why is an exam necessary?
3. How do the hazards of spaceflight affect these indicators?
4. When does a result deserve the attention of the crew or of the flight surgeons on the ground?
5. What actions can prevent a critical condition?

**Scientific framework (`VERIFIED` as a framework, taken from NASA's Human Research Program):** the five hazards of spaceflight: (1) space radiation, (2) isolation and confinement, (3) distance from Earth, (4) gravitational fields, (5) hostile closed environments. It is advisable to label each indicator of the tool with the hazard it responds to.

---

## 3. Architecture

### 3.1 Guiding principle (`DECIDED`)

**Hexagonal architecture (ports and adapters).** The domain core does not know concrete sensors, documents, voice or models. Everything that changes between demo, jury and real flight is an interchangeable adapter.

### 3.2 Domain core (no external dependencies)

- **Deterministic and auditable** rule engine that decides when there is an alert. **The language model never decides the alert.**
- Computation of derived quantities (for example PIO2, section 5.2).
- Body-environment crossing.
- Personal baseline per astronaut and relative comparison.
- Selection of the recommendation and the measure to activate from the catalog.

### 3.3 Ports (interfaces) and adapters

| Port | What it does | Planned adapters |
| --- | --- | --- |
| Sensor input | Delivers timestamped readings | Simulator (with scenarios), replay of real data (RadLab) and, in theory, real sensors |
| Knowledge | Answers "what to do in this situation" with a citation of the source | (a) Demonstration data labeled as fictitious; (b) RAG over public NASA PDFs |
| Voice input | Converts the astronaut's voice into text | Local Whisper; Alexa (demo only) |
| Writing / assistant | Explains the alert in natural language using only what was retrieved | Local Ollama orchestrated by n8n |
| Ground link | Syncs data with mission control when there is a connection | Optional; the system works the same without it |
| Storage | Saves readings, alerts and baseline | To be defined |

### 3.4 Planned flow (`SUGGESTED`, described by the user)

1. Sensors and rules go first through the **backend**.
2. On an event, the backend sends it to the **agent in n8n**.
3. The agent queries the **RAG** with the NASA PDFs.
4. With what was retrieved, **Ollama** summarizes and returns the answer with its source.

Ollama only uses the RAG as a complementary tool. The rules still decide the alert.

### 3.5 Local autonomous mode (`DECIDED` as an idea, details open)

- Everything lives on a local machine on board: data, rules, indexed PDFs, language model and transcription.
- If the link to mission control is cut, the crew keeps receiving alerts and recommendations with their source.
- When the link returns, it syncs. What is uploaded and who decides what to share is **open** (section 12).
- Context for why it matters: the signal delay to Mars was cited as 3 to 22 minutes each way (`NO VERIFIED` with a primary source; it comes from reading another team's repository).

### 3.6 Voice (`DECIDED`)

- **Local Whisper** as the main transcription (it runs without internet).
- **Alexa** as a temporary adapter for the demonstration only, in case Whisper gets stuck. Alexa processes voice in the cloud, so it is **not autonomous**; this must be stated honestly in the presentation. It requires creating a skill and a public endpoint (for example with a tunnel) that reaches the backend or n8n. The skill in development mode runs only on the team's account, which is enough.
- Always show what was transcribed for confirmation before acting (Whisper can fail with medical terms or cabin noise).
- **An emergency must never depend on the astronaut speaking:** the alert comes from the sensors.
- Plan B: written text input, in case the event's wifi or the microphone fails.
- Effort estimate for Whisper (`NO VERIFIED`, general estimate): one to two hours for the first transcription connected to the backend, plus one or two more for tests with noise and medical terms. Consider a fast variant such as faster-whisper and a small model if there is no graphics card.

### 3.7 Runtime profiles (`DECIDED`)

These are **development profiles** (configurations activated at startup), not user profiles. They are chosen with an **environment variable**:

| Value | Voice | What for |
| --- | --- | --- |
| `dev1` | Whisper | Development |
| `dev2` | Alexa | Development, fallback route for the demo |
| `jury` | Whisper | Clean run by the jury |

- That `dev1` and `jury` use the same thing is **on purpose**: it separates development from delivery and shows order. No technical difference between them is intended.
- The name of the variable and the default value are **not defined**. Assistant's recommendation (`SUGGESTED`): the default value should be `jury`, because it works without internet and without Alexa, so it is the safest if someone starts without configuring anything.

### 3.8 Delivery for the jury with Docker (`DECIDED` as an idea, details open)

The jury will review the code and run the program. To avoid "it works on my machine", a **Docker image will be published on Docker Hub**.

- The image should start with the `jury` profile by default and the profile should be changeable with the environment variable when running the container.
- Include what is needed to work **without internet**: backend, rule base, already indexed NASA PDFs, Whisper model.
- Ollama and its model take a lot of space: decide whether they go in the same image or in a separate container with Docker Compose, together with n8n.
- README with the exact command to download and run the image and the link to the repository.
- Check: final image size, absence of a graphics card on the jury's machine and microphone access from the container (it often gives problems depending on the operating system; text input must be a working alternative).
- Test the container on another computer, without internet, before delivering.

---

## 4. Data and inputs that mission control sees

When there is a connection, everything is visible from mission control: vital signs, cabin environment, radiation, sleep and generated alerts. What is actually shared is open (section 12).

Sleep data (`NO VERIFIED` with concrete links; the claims were saved in Notion after a search made in a voice session and the URLs were not kept):

- Actigraphy wristbands (Actiwatch Spectrum): measure movement and ambient light on the wrist; they estimate sleep and wakefulness, not the stages.
- Standard Measures study: questionnaire before and after sleeping (sleep quality, mood, team cohesion, performance).
- Astronauts sleep on average about six hours in space.
- **No** sleeping compartment that measures sleep by itself was found. A sleep module with noise, light, temperature and movement sensors is **only an idea to explore** and must be presented as such.
- Verified in the standard (`VERIFIED`): crew quarters with a noise limit of NC-40 on missions longer than 30 days, and vibration during sleep below 0.01 g RMS per 2-minute interval.

---

## 5. Catalog of data and rules with a source

> The **severity bands** (green, yellow, red) are a **team proposal**. The standard only gives limits. Mark the bands as such in the code.

### 5.1 Documents read and what was obtained from each

| Document | What was read |
| --- | --- |
| NASA-STD-3001 Vol. 2 Rev F (`https://www.nasa.gov/wp-content/uploads/2025/05/nasa-std-3001-vol-2.pdf`) | Section 6 (atmosphere, water, acoustics, vibration, radiation) and section 7.1 up to 7.1.3. It is a PDF of about 937 thousand characters; the rest was not read. |
| NASA-STD-3001 Vol. 1 Rev C (`https://www.nasa.gov/wp-content/uploads/2023/11/nasa-std-3001-vol-1-rev-c-with-signature.pdf`) | Sections 3 and 4, including 4.8 (radiation). It ends in an appendix truncated in the reading. |
| OCHMO-TB-003 Habitable atmosphere | Read in full as text. Table 6.2-1 and figures come as an image and were completed with Vol. 2. |
| OCHMO-TB-044 Medical operations | Read. It has no numerical thresholds for software. |
| Medical kit checklist | Read. |
| OCHMO-TB-002 (ECLSS) and OCHMO-TB-004 (CO₂) | Read in an earlier voice session. Their values were noted in Notion. |

**Important correction:** the ECLSS Technical Brief gave a minimum cabin pressure of 26.2 kPa. The current standard (Vol. 2 Rev F) says **34.5 kPa**. Use the standard's value.

### 5.2 Environment thresholds (level 1, use as is)

| Parameter | Value | Requirement | Source / state | Suggested use |
| --- | --- | --- | --- | --- |
| 1 h average ppCO₂ | ≤ 3 mmHg | V2 6004 | `VERIFIED` | Red. 1 h moving window |
| PIO2 normoxia | 145 to 155 mmHg | V2 6003, Table 6.2-1 | `VERIFIED` | Green |
| PIO2 mild hypoxia, lower limit | 127 mmHg, indefinite with a monitoring plan | Table 6.2-1 | `VERIFIED` | Yellow below 145; red below 127 |
| PIO2 hypoxia, absolute limit | 122 mmHg (1 h average) | Table 6.2-1 | `VERIFIED` | Critical |
| PIO2 indefinite hyperoxia, upper limit | 356 mmHg | Table 6.2-1 | `VERIFIED` | Red above |
| PIO2 short-term hyperoxia | 791 mmHg for 6 to 9 h | Table 6.2-1 | `VERIFIED` | Pure O₂: 9 h if it is the only exposure in 48 h, 6 h if in 24 h, maximum 5 days in a row |
| Total pressure | 34.5 < P ≤ 103 kPa (5.0 to 15.0 psia) | V2 6006 | `VERIFIED` | Green |
| Pressure rate of change | ≤ 13.5 psi/min if the change exceeds 1.0 psi; changes ≤ 1.0 psi exempt | V2 6007 | `VERIFIED` | Rapid depressurization alert |
| Diluent gas | ≥ 30% | V2 6002 | `VERIFIED` | Composition check |
| Temperature and humidity, health limit | 18 °C with 75% RH up to 27 °C with 25% RH | V2 6012 | `VERIFIED` as anchors of the rationale; the exact points of the figure were not in the text | Red outside |
| Temperature and humidity, performance zone | 20 to 25 °C and 30 to 60% RH | V2 6013 | Same as above | Yellow outside |
| Average post-landing humidity | 25–75% indefinite; 75–85% 24 h; 85–95% 12 h; > 95% 8 h | V2 6011, Table 6.2-2 | `VERIFIED` | Only after removing the suit |
| Drinking water | Minimum 2.5 L per crew member per day | V2 6109 | `TB` (not re-verified in Vol. 2) | Budget |
| Sampling frequency | Atmosphere every 5 s, pressure every 1 s, temperature and humidity every 1 min | V2 6001, Table 6.1-1 | `VERIFIED` | Simulator rhythm |
| Noise, 24 h dose | D ≤ 100 (equivalent to 8 h at 75 dBA in orbit) | V2 6115 | `VERIFIED` | Optional |
| Hazardous noise outside launch | < 85 dBA | V2 6077 | `VERIFIED` | Optional |
| Alarms | < 95 dBA at the receiver's position | V2 6081 | `VERIFIED` | Optional |
| Sleeping quarters (> 30 days) | NC-40 | V2 6079 | `VERIFIED` | Optional |
| Vibration during sleep | < 0.01 g RMS per 2 min interval | V2 6092 | `VERIFIED` | Optional |
| Combustion gases (**monitoring** ranges) | CO 5–1000 ppm; HCN, HCl, HF 2–50 ppm | Table 6.2-3 | `VERIFIED` | These are ranges the sensor must cover, **not** health limits |

**Oxygen formula (`VERIFIED`):** `PIO2 = (P_total − 47 mmHg) × O2_fraction`. The 47 mmHg is the vapor pressure of water at 37 °C.

- Oxygen must be evaluated as a **partial pressure**, not as a percentage. A "normal" percentage at low pressure can be hypoxia.
- The same applies to CO₂: 3 mmHg equals 0.39% at sea level (760 mmHg) but 0.71% at 56.5 kPa. Alerting "by CO₂ percentage" without considering pressure is incorrect.
- Conversions: 1 kPa = 7.50062 mmHg; 1 psi = 51.7149 mmHg.

**Test vectors for the rule engine** (computed by the assistant with the formula above):

| Input | Expected result |
| --- | --- |
| 760 mmHg, 21% O₂ | PIO2 ≈ 149.7 mmHg, normoxia, green |
| 760 mmHg, 18% O₂ | PIO2 ≈ 128.3 mmHg, below 145 (yellow) and barely above 127 |
| 56.5 kPa (423.8 mmHg), 34% O₂ | PIO2 ≈ 128.1 mmHg, yellow, near the 127 limit |
| 1 h average ppCO₂ = 3.1 mmHg | Red |
| Pressure 14.7 psia to 12.0 psia in 1 min (Δ 2.7 psi) | Within the 13.5 psi/min limit; no rate alert |
| Pressure drop of 14 psi in 0.5 min (28 psi/min) | Rapid depressurization alert |

### 5.3 Radiation (level 2, there is real data)

| Parameter | Value | Requirement |
| --- | --- | --- |
| Galactic cosmic ray (GCR) dose, free space | < 1.3 mSv/day | V1 4033 |
| GCR on a planetary surface | < 0.9 mSv/day | V1 4033 |
| Career effective dose | < 600 mSv | V1 4030 |
| Dose per solar particle event (reference spectrum) | < 250 mSv | V1 4031 |
| Solar event with more than 50 mSv projected | Requires area or personal monitors | Table 6.8-1 |
| More than 75 mSv accumulated over several missions | Requires additional monitoring | Table 6.8-1 |
| Nuclear technology | < 20 mSv per mission year (≈ 0.05 mSv/day prorated) | V1 4032 |

Limits per organ, Table 4.8-1 (`VERIFIED`):

| Organ | 30 days | 1 year | Career |
| --- | --- | --- | --- |
| Lens | 1,000 mGy-Eq | 2,000 mGy-Eq | 4,000 mGy-Eq |
| Skin | 1,500 mGy-Eq | 3,000 mGy-Eq | 6,000 mGy-Eq |
| Blood-forming organs | 250 mGy-Eq | 500 mGy-Eq | not applicable |
| Circulatory system | 250 mGy-Eq | 500 mGy-Eq | 1,000 mGy-Eq |
| CNS (hippocampus) | 500 mGy | 1,000 mGy | 1,500 mGy |
| CNS, Z ≥ 10 | not applicable | 100 mGy | 250 mGy |

- These limits depend on specific NASA models (Q model and the 2009 solar-minimum GCR spectrum). **The prototype's values will be approximate** and this must be stated.
- What is measured according to the standard: personal GCR monitoring and solar event monitoring outside low Earth orbit.
- **Real data for the simulator:** NASA OSDR RadLab (`https://visualization.osdr.nasa.gov/radlab/`), which according to another team's project provides absorbed doses from the DOSTEL (ISS), CRaTER (lunar orbit) and MSL-RAD (Mars) instruments; and NOAA SWPC for solar protons. **These datasets were not opened.** Verify format, license and dates before using them.

### 5.4 Body criteria relative to the baseline (level 3)

They directly support the personal baseline per astronaut.

| Parameter | Criterion | Requirement |
| --- | --- | --- |
| Aerobic capacity in mission | ≥ 80% of the pre-mission value | V1 4003 |
| Absolute VO₂max | ≥ 32.9 mL/min/kg (EVA in microgravity); ≥ 36.5 (EVA on a surface) | V1 4001, V1 4002 |
| Muscle strength in mission | ≥ 80% of the baseline | V1 4024 |
| Bone density in mission | ≥ 95% of the previous one at hip and spine; ≥ 90% at femoral neck | V1 4027 |
| Daily energy | Average of 3,035 kcal per crew member, or EER formula with activity factor 1.0–1.25; +200 kcal per hour of EVA | V2 7003, V2 7004 |
| Vitamin D | 25 µg per day | Table 7.1-2 |
| Sleep (configurable default value, not a requirement) | Period of 8.5 h, plus 2 h before and 1.5 h after; circadian minimum between 1 and 7 AM | V1 6001 (rationale) |

EER formula (`VERIFIED`, Table 7.1-1): men ≥ 19 years `662 − 9.53 × age + AF × (15.9 × mass_kg + 539.6 × height_m)`; women ≥ 19 years `354 − 6.91 × age + AF × (9.36 × mass_kg + 726 × height_m)`.

Table 4.6-1, pre-mission strength in multiples of body weight (reading of columns **inferred**, ambiguous in the extracted text): minimum deadlift 1.0, EVA in microgravity 1.3, EVA on a surface 1.6; minimum bench press 0.7, 0.8 and 1.0. Do not use without checking the original table.

### 5.5 Qualitative knowledge for the knowledge port (level 4)

- **CO₂, symptoms** (`TB`): headache between 2.8 and 4.5 mmHg; fatigue, poor sleep and nausea above 4.5 mmHg. To keep the headache risk under 1%, the 7-day average must be below 2.5 mmHg. Apollo 13 reached 14.9 mmHg and dropped to 1 mmHg by improvising filters.
- **Hypoxia** (`VERIFIED`, TB-003): mental changes sometimes imperceptible to the astronaut themselves, reduced vision, fatigue, nausea, headache, dizziness, hyperventilation. An argument in favor of the alarm coming from the sensor.
- **Hyperoxia:** reduces ventilation and heart rate; the treatment is lowering the ppO₂.
- **Decompression sickness:** treatment with recompression and 100% O₂.
- **Space motion sickness:** about 3 days on average (TB-044).
- **Role of the Crew Medical Officer (CMO):** two per increment; the medical decision rests with the flight surgeon on the ground, with the international medical group in acute cases. It helps define when an alert escalates to Ground.
- **Measures to activate:** the medical kit is organized in 11 color-coded packages and contains drug categories per condition (nausea and dizziness, sleep, pain and fever, allergies, infections, respiratory, gastrointestinal, altitude sickness with acetazolamide, mental health, cardiac, emergencies). It serves as a catalog of actions, **not** as a protocol of what to give and when.
- **Measurements on board, according to the medical kit checklist:** blood oximeter, blood pressure monitor and cuff, thermometer, stethoscope, otoscope, tonometer, urine strips. Continuous heart rate would come from a wristband or sensor (`NO VERIFIED`).

### 5.6 What is NOT in the public documents read

- **Thresholds for heart rate, blood pressure and SpO₂.** Options: cite an external scale such as NEWS2 (used by other teams; **not verified**) or label them `DEMO`.
- **Glucometer and electrocardiograph:** the checklist read does not list them. It affects the "blood sugar" of the team's note.
- Critical values for hematology and immunology, and limits on work and sleep hours: the standard says they exist but does not publish them in the text read.
- CO₂ limits at 24 h, 7 and 1000 days in the standard: they did not appear in the part of Vol. 2 that was read. The 2.5 mmHg at 7 days comes from a Technical Brief.
- Table 10.3-1 of Vol. 2 (alerts) did not appear in the stretch read.
- Oxygen consumption per crew member for the mission budget: **not confirmed**. The idea of "percentage of the mission's oxygen spent" needs that figure or a `DEMO` value.
- A decision tree for fever or other symptoms: none was found in what is open.

### 5.7 Proposed structure for the rule catalog (`SUGGESTED`)

One record per rule, in versioned JSON or YAML, with these fields: `key`, `kind`, `parameter`, `operator`, `threshold`, `unit`, `window_s` (for example a 1 h average), `severity`, `source_requirement`, `source_document`, `evidence_state` (`VERIFIED`, `TB` or `DEMO`), `hrp_hazard` (one of the five) and `action_key`. The interface and the alerts must show `source_document`, `source_requirement` and `evidence_state` so that each alert is auditable.

```json
{
  "key": "env-co2-1h",
  "kind": "threshold",
  "parameter": "ppco2",
  "operator": ">",
  "threshold": 3,
  "unit": "mmHg",
  "window_s": 3600,
  "severity": "alert",
  "source_requirement": "V2 6004",
  "source_document": "NASA-STD-3001 Vol. 2 Rev F",
  "evidence_state": "VERIFIED",
  "hrp_hazard": "hostile_closed_environments",
  "action_key": "check_ventilation_and_filters"
}
```

---

## 6. Knowledge base (RAG)

### 6.1 Answer policy (`SUGGESTED`, high priority)

- The model answers **only** with retrieved passages and cites them. If there is no passage that supports the answer, it says it does not have that information. It never invents medical protocols.
- If a real manual is missing for a situation, the **demonstration data** adapter comes in, and the answer says so explicitly ("demonstration data, not from NASA").
- Open decision: does the RAG only return passages with their citation (simpler and auditable), or does it also write with Ollama? The team leans toward using Ollama as the writer.

### 6.2 Candidate documents and their status

| Document | URL | Status |
| --- | --- | --- |
| NASA-STD-3001 Vol. 1 Rev C | `https://www.nasa.gov/wp-content/uploads/2023/11/nasa-std-3001-vol-1-rev-c-with-signature.pdf` | Read in sections 3 and 4 |
| NASA-STD-3001 Vol. 2 Rev F | `https://www.nasa.gov/wp-content/uploads/2025/05/nasa-std-3001-vol-2.pdf` | Read in section 6 and part of 7.1 |
| TB-002 ECLSS | `https://www.nasa.gov/wp-content/uploads/2023/07/eclss-technical-brief-ochmo.pdf` | Read |
| TB-003 Habitable atmosphere | `https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-003-habitable-atmosphere.pdf` | Read |
| TB-004 CO₂ | `https://www.nasa.gov/wp-content/uploads/2023/03/co2-technical-brief-ochmo.pdf` | Read |
| TB-044 Medical operations | `https://www.nasa.gov/wp-content/uploads/2025/08/ochmo-tb-044-medical-operations.pdf` | Read |
| Medical kit checklist | `https://www.nasa.gov/wp-content/uploads/2015/03/medical_kit_checklist_-_full_release.pdf` | Read |
| Human Integration Design Handbook | `https://www.nasa.gov/wp-content/uploads/2015/03/human_integration_design_handbook_revision_1.pdf` | **Not opened** |
| OCHMO-STD-100.1A (medical evaluations) | `https://www.nasa.gov/wp-content/uploads/2023/04/ochmo-std-100.1a.pdf` | **Not opened** |
| ISS medical emergency manual (2016) | `https://www.governmentattic.org/19docs/NASA-ISSmedicalEmergManual_2016.pdf` | **Not opened.** It comes from a transparency release, not from an official NASA site. Check the license and currency before redistributing it in the image |

### 6.3 Practical notes for ingestion (`SUGGESTED`)

- Some tables in the standard are images and do not come out in the extracted text (Table 6.2-1 in TB-003, figures 6.2-2 and 6.2-3). If PDFs are indexed, those tables need manual transcription or visual extraction; the rule catalog in section 5 already contains them.
- Keep per fragment: document, requirement number, page and verification state, so it can be cited.
- Before redistributing PDFs inside the Docker image, confirm that they are public domain or that their license allows it. Documents on nasa.gov marked as publicly accessible usually are, but **the license of each one was not verified**.

---

## 7. Data simulation (`SUGGESTED`)

There are no public in-flight vital signs to train or validate with. Therefore:

- Body data will be **synthetic** and must be labeled as such in code, interface and presentation.
- Respect the standard's frequencies: atmosphere every 5 s, pressure every 1 s, temperature and humidity every 1 min.
- Simulate **scenarios** that demonstrate the body-environment crossing: slow CO₂ increase with headache and heart-rate change; pressure drop with a high rate of change; mild hypoxia from low total pressure with an apparently normal O₂ percentage; solar particle event with increasing dose; sleep deterioration over several days against the baseline; a case in which the body changes but the environment is fine.
- Possible real sources: RadLab and NOAA SWPC for radiation; NASA OSDR (for example the OSD-569 blood count dataset) for pre-flight lab values. Another team used OSD-569 this way; **it was not opened**.
- Open decision: which sleep data to simulate.

---

## 8. Conversational assistant

- Local model with **Ollama** over **n8n** (`SUGGESTED`, described by the user). Test a small model on the demo machine (the jury may not have a GPU).
- Ollama only writes and explains; the rules decide.
- Voice input with local Whisper (section 3.6). Output as text or with local voice (not decided).
- Using cloud APIs (OpenAI, Gemini, Anthropic) for the main flow has already been ruled out for now, for the sake of autonomy.

---

## 9. Honesty and safety constraints

- Decision-support prototype; **not a medical device**; it does not diagnose or prescribe.
- Every figure without a verified source is labeled `DEMO`.
- The severity bands are a team proposal.
- Radiation figures depend on NASA models and will be approximate.
- Alexa is not autonomous: say so in the presentation.
- The emergency alert comes from sensors, not from voice.
- If the system shows a recommendation that comes from demonstration data, it must say so.

---

## 10. Decision status

### 10.1 Decided

- Chosen challenge: health monitoring for astronauts.
- Core idea: cross body sensors with cabin sensors, with alerts and measures.
- Hexagonal architecture with interchangeable knowledge (demo / real NASA PDFs).
- Local and autonomous operation on board.
- Voice: local Whisper as the main one, Alexa only as a demonstration fallback.
- Three profiles by environment variable: `dev1` (Whisper), `dev2` (Alexa), `jury` (Whisper).
- Delivery with a Docker image on Docker Hub.
- Sketches go as notes, without labeling them "our proposal".

### 10.2 Discarded or postponed

- The query about in-flight fever was only a question and **was not noted in Notion** at the user's request (see section 13).

---

## 11. Differentiation from other teams

Angles that are already in the design or make it possible:

- Body-environment crossing with attribution of the probable cause.
- Personal baseline per astronaut (backed by relative criteria in the standard).
- Rules with a source: each alert shows document, requirement and verification state.
- Real autonomy: it works offline, with a local model and transcription.
- Architecture that allows switching from demonstration data to real NASA data without touching the core.
- Evaluating oxygen and CO₂ by partial pressure, a detail that almost nobody applies.
- Reproducible delivery with Docker.

To explore: astronaut consent over what is shared with Ground; sleep module with sensors as a concept; gamification and didactic explanations.

---

## 12. Open questions (do not decide without consulting)

1. Name of the profile environment variable and default value (`jury` is suggested).
2. Does the RAG only return passages with a citation, or does it also write with Ollama?
3. What is uploaded to Ground on reconnecting and whether the astronaut chooses what to share.
4. Demo scenario: Mars transit, lunar base, ISS or another.
5. Which measures each alert activates.
6. Source of the thresholds for heart rate, blood pressure and SpO₂.
7. Mission oxygen budget: is it used, and with what consumption per crew member?
8. Ollama in the same image or in a separate container with Docker Compose?
9. Is JSON/YAML used for the rule catalog and who maintains it?
10. **Backend technology stack, language, database and interface: not discussed.** Ask the user.
11. Team size and roles, and real hours available: not known.
12. Which sleep data to simulate.
13. Language of the interface and of the presentation to the jury.

---

## 13. Unverified information outside Notion

Answer to a voice query about in-flight fever. **The assistant writing this document did not see the sources**; the figures are collected here only as a lead for research, not as citable data:

- Definition of fever from the crew health stabilization program: 100.4 °F or more (about 38 °C), coming from the pre-flight check, not from an in-orbit protocol.
- Immune dysregulation during flight and reactivation of latent viruses (it was mentioned that 9 of 17 astronauts studied shed at least one virus).
- ISS medical kit with about 190 medications in two kits.
- Anecdotal reports that certain medications are less effective in flight, which would justify the tool recording whether a measure worked.
- No decision tree for fever was found. The ISS medical emergency manual, still unopened, is the most likely candidate.

---

## 14. Known inconsistencies in the Notion page

Correct or take into account:

1. The "Candidate documents" table in section 5b still marks as "Not opened" several documents that were read afterwards (Vol. 1 sections 3 and 4, Vol. 2 sections 6 and 7.1, TB-003, TB-044, medical kit checklist). The real state is in section 6.2 of this file.
2. Section 4 of Notion has two nearly duplicate blocks called "Second part".
3. In section 5b, the environmental limits appear with the source "Technical Brief ECLSS" except total pressure; the standard's values were verified afterwards in Vol. 2 (section 5.2 of this file).
4. In 5b the "Pending" item about reading sections 3 and 4 of Vol. 1 is already done.
5. In section 5d the sleep notes cite NASA sources without links; see section 4 of this file.
6. In section 7 (pending), the checkbox "Choose which public PDFs to use" is marked done even though documents remain to be opened.

---

## 15. Pending items (copy from Notion, ordered)

**Research**

- [ ] Read the official challenge page and its resources
- [ ] Find a source for body vital-sign thresholds
- [ ] Open RadLab / OSDR and confirm the format and license of the data
- [ ] Open the ISS medical emergency manual, the HIDH and OCHMO-STD-100.1A
- [ ] Decide whether the oxygen budget is used and with what data

**Design and decisions**

- [ ] Define the MVP scope according to the remaining time
- [ ] Assign team roles
- [ ] Decide whether the rule catalog goes in JSON and who maintains it
- [ ] Confirm whether "RAC" was RAG and decide whether there is a language model or only passage search
- [ ] Decide which sleep data to simulate
- [ ] Choose the name of the environment variable and its default value

**Implementation**

- [ ] Test a small model with Ollama on the demo machine
- [ ] Test local Whisper with background noise
- [ ] Build the flow in n8n: backend, agent, RAG and response
- [ ] Create the Alexa skill and the tunnel only if Whisper gets stuck

**Delivery**

- [ ] Create the Dockerfile and publish the image on Docker Hub
- [ ] Decide whether Ollama goes in the same image or in a separate container with Docker Compose
- [ ] Test the container on another computer, without internet, before delivering
- [ ] Write in the README the command to download and run the image

**Done**

- [x] Define the development profiles and how to switch between them
- [x] First selection of public NASA PDFs and download check

---

## 16. Assistant suggestions (not decided)

> This section is the opinion of the assistant that wrote the document. Ignore it if the user decides otherwise.

**Recommended work order given that the hackathon ends on November 15:**

1. Domain core and rule catalog with the values from sections 5.2 and 5.3, with the tests from the vector table. It is the most defensible in front of a jury and does not depend on infrastructure.
2. Sensor simulator with the scenarios from section 7.
3. Interface with colors, trends and the explanation of each alert with its source.
4. Knowledge adapter with demonstration data, and then the RAG one over PDFs. Start with a handful of well-cited fragments before indexing everything.
5. Whisper and Ollama behind their ports.
6. Docker, the `jury` profile and the test without internet.
7. Alexa only if time is left.

**Suggested repository structure (hexagonal):**

```text
/domain          core: rules, calculations, baseline, severities
/ports           interfaces: sensors, knowledge, voice, assistant, link, storage
/adapters
  /sensors       simulator, RadLab replay
  /knowledge     demo, rag_nasa
  /voice         whisper_local, alexa
  /assistant     ollama_n8n
  /uplink        optional sync
/rules           rule catalog with source and state
/data            simulations and downloaded real data, with license
/profiles        per-profile configuration: dev1, dev2, jury
/docker          Dockerfile and compose
/docs            README, verification notes
```

**Main risks:** too many pieces for 48 hours (n8n, Ollama, Whisper, Alexa, Docker); slow local model without a GPU; presenting `DEMO` values as if they were from NASA; redistributing PDFs without confirming the license; microphone in Docker.

---

## 17. Sources

**Challenge and context**

- Challenge summary, Sonoma State: `https://edeon.sonoma.edu/nasaspaceapps-26/`
- NASA, Space Apps 2026 announcement: `https://science.nasa.gov/universe/nasa-welcomes-all-ages-experience-levels-for-space-apps-challenge/`

**NASA documents read**

- NASA-STD-3001 Vol. 1 Rev C: `https://www.nasa.gov/wp-content/uploads/2023/11/nasa-std-3001-vol-1-rev-c-with-signature.pdf`
- NASA-STD-3001 Vol. 2 Rev F: `https://www.nasa.gov/wp-content/uploads/2025/05/nasa-std-3001-vol-2.pdf`
- OCHMO-TB-002 ECLSS: `https://www.nasa.gov/wp-content/uploads/2023/07/eclss-technical-brief-ochmo.pdf`
- OCHMO-TB-003: `https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-003-habitable-atmosphere.pdf`
- OCHMO-TB-004 CO₂: `https://www.nasa.gov/wp-content/uploads/2023/03/co2-technical-brief-ochmo.pdf`
- OCHMO-TB-044: `https://www.nasa.gov/wp-content/uploads/2025/08/ochmo-tb-044-medical-operations.pdf`
- Medical kit checklist: `https://www.nasa.gov/wp-content/uploads/2015/03/medical_kit_checklist_-_full_release.pdf`

**Other teams' projects consulted (reference for approaches)**

- AstroHealth: `https://github.com/Ridwanulkarim/nasa-challenge-Create-Health-Monitoring-Software-for-Astronauts-on-Space-Missions`
- AURORA (offline, RadLab, NOAA): `https://github.com/fabriciojunio/aurora-astronaut-health`
- Crew Health Monitor (space rules versus terrestrial ones, OSD-569): `https://github.com/AdityaK0804/Crew-Health-Monitor`

**Real data mentioned, unopened**

- NASA OSDR: `https://osdr.nasa.gov/`
- RadLab: `https://visualization.osdr.nasa.gov/radlab/`
- NOAA SWPC GOES (solar protons): no verified URL
