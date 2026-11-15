# spaceApps

<aside>
🛰️

NASA Space Apps Challenge 2026 · Nov 14–15 · Challenge: **Create Health Monitoring Software for Astronauts on Space Missions**

</aside>

## 1. The challenge

**Problem.** Long missions expose astronauts to radiation, isolation and confinement, altered gravity and a hostile closed environment. This can cause immune changes, bone loss, cardiovascular events and behavioral health problems. The astronauts themselves have to detect a good part of those changes in themselves.

**Goal.** Build software that gathers health indicators and lets astronauts assess their state and act accordingly.

Note: the full official challenge page (resources and evaluation criteria) could not be read. Pending verification at [spaceappschallenge.org/2026/challenges/health-monitoring-software/](http://spaceappschallenge.org/2026/challenges/health-monitoring-software/)

## 2. What it implies (analysis)

- The user is the astronaut, not mission control.
- It must work without Ground: the signal delay to Mars is 3 to 22 minutes each way.
- There are two distinct steps: assess (interpret the data) and act (protocol, recommendation, alert).
- Cover physical and behavioral health.
- There is almost no public in-flight vital-sign data, so there will be simulation. It must be justified and thresholds without a source must be labeled as demonstration parameters.

**Scientific framework:** the five HRP hazards from NASA: space radiation, isolation and confinement, distance from Earth, gravitational fields, hostile or closed environments.

**Possible real data:** NASA OSDR ([osdr.nasa.gov](http://osdr.nasa.gov), e.g. OSD-569), RadLab, NOAA SWPC, NASA-STD-3001, NEWS2 scale.

## 3. Competition and differentiation

There are at least ten public repos from other teams. Most are a dashboard with simulated vital signs and threshold alerts.

Angles that do differentiate:

- Personal baseline per astronaut
- Rules adapted to space versus terrestrial ranges
- Explainability: each alert with its reason and its source
- Consent and privacy over what data is shared with Ground
- Real NASA data integrated, not just cited
- A concrete user and a concrete scenario

## 4. Our proposal

**Core idea (first version, Nov 14, by voice):** a system that combines biometric sensors with the ship's environmental sensors and generates alerts and measures to activate.

- Biometric: heart rate, blood pressure, blood oxygenation.
- Environmental: oxygen level, CO₂ level, internal cabin pressure.
- Possible alerts: high or low oxygen, CO₂ at a certain percentage, percentage of the mission's total oxygen already consumed.
- Each alert can activate measures.

To be defined: concrete user, demo scenario, which measures are activated and how body data is crossed with environment data.

**Second part (Nov 14, by voice): knowledge source and architecture**

- Use public NASA data: the public PDFs and manuals that indicate what to do in each situation.
- Hexagonal architecture (ports and adapters) so the knowledge source is interchangeable.
- If there is no manual at hand for a situation, demonstration data invented by the team can be used.
- That demonstration data is later replaced by real NASA data without touching the core of the system.
- The real documents feed an information retrieval system (in the voice note it sounded like "RAC"; it is understood as RAG, to be confirmed).

Sketch of the idea:

- Core: alert rules, body-environment crossing and recommendation.
- Input port: sensors (simulated or real).
- Knowledge port: "what to do in this situation".
- Adapter 1: demonstration data, labeled as such.
- Adapter 2: public NASA PDFs with passage retrieval and citation of the source.

**Second part (Nov 14, by voice): public data, RAG and hexagonal architecture**

- Use public NASA documents (PDFs, manuals and protocols) on what to do in each situation, as a knowledge base for a RAG.
- Hexagonal architecture (ports and adapters): the knowledge source is an interchangeable adapter.
- If there is no real manual for a situation, an adapter with demonstration data is used, clearly labeled as fictitious.
- Later it can be swapped for real NASA data without touching the core of the system.

To verify: which NASA medical manuals are really public and which situations they cover.

## 5. Ideas discussed

### Handwritten note · Nov 14, 13:11 (PDF Notes_261114_131143)

**Planning — problem statement**

Build health monitoring software for astronauts on space missions. On long missions astronauts cannot depend on ground control, so the astronaut must detect changes in themselves.

**Five hazards of spaceflight**

1. Space radiation
2. Isolation and confinement
3. Distance from Earth
4. Gravity fields
5. Hostile closed environments

**These hazards represent health problems**

- Changes in the immune system
- Loss of bone density
- Cardiovascular events
- Inadequate nutrition
- Behavioral health conditions

Astronauts must be able to perform health assessments on themselves during a mission, to prevent and treat health problems that may arise.

**Useful health indicators**

- Blood pressure
- Heart rate
- Blood sugar
- Body temperature
- Hours of sleep
- Mood

**Use the resources of NASA's Human Research Program**

Questions the tool must be able to answer:

- What measurements can be made in space?
- Why is an exam necessary?
- How do the hazards of spaceflight affect these health indicators?
- When might a result deserve the attention of the crew or of the flight surgeons on the ground?
- What actions can be taken to prevent a critical health condition?

**To consider**

- Provide information on astronauts' health in different environments: spacecraft, space station, rover or a base on another planet or moon.
- Tool to prompt astronauts to take measures or complete specific actions from time to time as part of the mission routine.

**Include the following features**

- Gamification to help astronauts perform tasks that support their health
- Dynamic charts showing changes in astronauts' health indicators over time
- Color coding that helps interpret health at a glance

Astronauts do not know everything about how to assess their health. The tool could provide simple instructions and explanations covering measurements, health indicators and risks.

## 5b. Knowledge sources (public NASA PDFs)

These are the sources that would feed the knowledge port. The limits below were read directly in the OCHMO Technical Briefs, which are reference documents derived from NASA-STD-3001 ("for reference only", they do not replace the standard). To cite in the presentation it is advisable to confirm each value in the full standard.

### Verified environmental limits

| Parameter | Limit | Requirement | Source |
| --- | --- | --- | --- |
| CO₂ (1 hour average) | No more than 3 mmHg partial pressure | [V2 6004] | [CO₂ Technical Brief](https://www.nasa.gov/wp-content/uploads/2023/03/co2-technical-brief-ochmo.pdf) |
| O₂ (inspired partial pressure) | Normoxia range: 145 to 155 mmHg | [V2 6003] | [ECLSS Technical Brief](https://www.nasa.gov/wp-content/uploads/2023/07/eclss-technical-brief-ochmo.pdf) |
| Diluent gas (nitrogen) | At least 30% of the atmosphere | [V2 6002] | ECLSS Technical Brief |
| Total cabin pressure | Between 34.5 and 103 kPa (5.0 to 15.0 psia), indefinite exposure. **Corrected:** the 26.2 kPa in the ECLSS Technical Brief was from an earlier revision; the Vol. 2 Rev F standard has it at 34.5 kPa | [V2 6006] | NASA-STD-3001 Vol. 2 Rev F |
| Pressure rate of change | Maximum 13.5 psi/min if the change exceeds 1.0 psi | [V2 6007] | ECLSS Technical Brief |
| Temperature and humidity (health limit) | 18 °C with 75% humidity up to 27 °C with 25% | [V2 6012] | ECLSS Technical Brief |
| Temperature and humidity (performance zone) | 20 to 25 °C and 30 to 60% humidity | [V2 6013] | ECLSS Technical Brief |
| Drinking water | Minimum 2.5 L per crew member per day | [V2 6109] | ECLSS Technical Brief |
| Food | Average of 3,035 kcal per crew member per day | [V2 7003] | ECLSS Technical Brief |

### Useful data for CO₂ alerts

- Symptoms observed by CO₂ level: headaches between 2.8 and 4.5 mmHg, and fatigue, poor sleep and nausea above 4.5 mmHg.
- To keep the headache risk below 1%, the 7-day average must be below 2.5 mmHg.
- Reference level on Earth: average indoor air has between 0.08% and 0.1% CO₂, that is, 0.608 to 0.76 mmHg.
- Historical case: in Apollo 13 the CO₂ reached 14.9 mmHg and dropped to 1 mmHg after improvising the filters.
- NASA warning: many symptoms attributed to CO₂ are also caused by fluid shift in microgravity, and fixed sensors do not see local pockets of CO₂. This justifies crossing the environment with body data.

### Requirements that support our idea

- [V2 6021] The standard requires displaying pressure, humidity, temperature, ppO₂ and ppCO₂ in real time.
- [V2 6022] The standard requires alerting the crew, locally and remotely, when those parameters leave safe limits.
- [V2 6001] The standard requires monitoring data in a format compatible with trend analysis.
- [V1 3003] Programs must provide in-mission capabilities to monitor physiological and psychosocial well-being.
- [V1 3004] Programs must provide capabilities and resources to diagnose and treat possible medical conditions.

### Candidate documents for the knowledge port

| Document | What it is for | Status |
| --- | --- | --- |
| [NASA-STD-3001 Vol. 1, Rev C](https://www.nasa.gov/wp-content/uploads/2023/11/nasa-std-3001-vol-1-rev-c-with-signature.pdf?emrc=6a7d82570f36c) | Crew health: fitness for duty, exposure limits, medical care. 86 pages. | Only the index and the scope opened. Sections 3 and 4 still to be read. |
| [NASA-STD-3001 Vol. 2, Rev F](https://www.nasa.gov/wp-content/uploads/2025/05/nasa-std-3001-vol-2.pdf) | Environmental and habitat limits. | Not fully opened. The limits came from the Technical Briefs. |
| [ECLSS Technical Brief (OCHMO-TB-002)](https://www.nasa.gov/wp-content/uploads/2023/07/eclss-technical-brief-ochmo.pdf) | Summary of atmosphere, water and life support. | Read. |
| [CO₂ Technical Brief (OCHMO-TB-004)](https://www.nasa.gov/wp-content/uploads/2023/03/co2-technical-brief-ochmo.pdf) | Symptoms, historical levels and CO₂ requirements. | Read. |
| [Habitable Atmosphere Technical Brief (OCHMO-TB-003)](https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-003-habitable-atmosphere.pdf) | Cabin pressure and composition. | Not opened. |
| [Medical Operations Technical Brief (OCHMO-TB-044)](https://www.nasa.gov/wp-content/uploads/2025/08/ochmo-tb-044-medical-operations.pdf) | Structure of ISS medical operations. | Not opened. |
| [Human Integration Design Handbook](https://www.nasa.gov/wp-content/uploads/2015/03/human_integration_design_handbook_revision_1.pdf) | Rationale, history and data behind the standard. | Not opened. |
| [Medical kit checklist](https://www.nasa.gov/wp-content/uploads/2015/03/medical_kit_checklist_-_full_release.pdf) | Medications, side effects and location. | Not opened. |
| [ISS medical emergency manual (2016)](https://www.governmentattic.org/19docs/NASA-ISSmedicalEmergManual_2016.pdf) | Step-by-step procedures. It comes from a transparency release, not from an official NASA site. | Not opened. Check license and currency. |
| [OCHMO-STD-100.1A](https://www.nasa.gov/wp-content/uploads/2023/04/ochmo-std-100.1a.pdf) | Medical evaluations and test schedule. | Not opened. |

### Pending items in this section

- The body vital-sign thresholds (heart rate, blood pressure, blood oxygenation) did not come from these documents. They must be looked up in another source or labeled as demonstration parameters.
- Sections 3 and 4 of Volume 1 still need to be read, which cover in-mission medical care and fitness limits.
- The oxygen budget per mission can be computed with the data from the ECLSS Technical Brief (resting and exercise O₂ consumption per crew member). It remains to be defined whether we use it.

## 5c. Analysis: most useful data for the algorithm

Read on Nov 14 directly in NASA-STD-3001 Vol. 2 Rev F (section 6 and section 7.1 up to 7.1.3; the rest of the document was not read), Vol. 1 Rev C (sections 3 and 4, including 4.8 radiation), OCHMO Technical Briefs TB-003 and TB-044, and the medical kit checklist. The severity bands (green, yellow, red) are a team proposal; the standard only gives limits.

### Findings that change the design

- **Oxygen is measured as a partial pressure, not as a percentage.** The standard defines PIO2 = (Total pressure − 47 mmHg) × O₂ fraction. With 14.7 psia and 21% O₂ it gives about 150 mmHg, within normoxia. With a lower-pressure cabin, a "normal" percentage can be hypoxia. The algorithm must compute PIO2 from two sensors (pressure and O₂ %).
- **The standard asks for exactly what we propose.** [V2 6020] continuous recording, [V2 6021] real-time display, [V2 6022] local and remote alert, [V2 6001] data suitable for trend analysis.
- **The body's health criteria are relative to each astronaut's baseline.** It directly supports the personal baseline.
- **The thresholds for heart rate, blood pressure and SpO₂ are not in these documents.** The medical kit does include a blood oximeter, blood pressure monitor and thermometer, so they are real on-board measurements. The checklist read does not list a glucometer or ECG, which affects the "blood sugar" in our note.

### Level 1: hard environmental thresholds (use as is)

| Parameter | Value | Requirement | Use in the algorithm |
| --- | --- | --- | --- |
| ppCO₂, 1 hour average | ≤ 3 mmHg | [V2 6004] | Red limit. 1 h moving window |
| PIO2 normoxia | 145 to 155 mmHg | [V2 6003], Table 6.2-1 | Green range |
| PIO2 mild hypoxia, lower limit | 127 mmHg, indefinite with a monitoring plan | Table 6.2-1 | Yellow below 145, red below 127 |
| PIO2 hypoxia, absolute limit | 122 mmHg (1 h average) | Table 6.2-1 | Critical |
| PIO2 hyperoxia | 356 mmHg indefinite; 791 mmHg only 6 to 9 h | Table 6.2-1 | Red above 356. Pure O₂: 9 h maximum if it is the only exposure in 48 h, 6 h if in 24 h, no more than 5 days in a row |
| Total pressure | 34.5 to 103 kPa | [V2 6006] | Green range |
| Pressure rate of change | ≤ 13.5 psi/min if the change exceeds 1.0 psi | [V2 6007] | Rapid depressurization alert |
| Diluent gas | ≥ 30% | [V2 6002] | Composition check |
| Temperature and humidity | Health limit 18 °C with 75% RH up to 27 °C with 25% RH; performance zone 20 to 25 °C and 30 to 60% RH | [V2 6012] and [V2 6013] | Yellow outside the performance zone, red outside the health limit. The exact points of the figure are not in the text; they are the anchors of the rationale |
| Sampling frequency | Atmosphere every 5 s, pressure every 1 s, temperature and humidity every 1 min | [V2 6001], Table 6.1-1 | Defines the rhythm of the sensor simulator |
| Noise | 24 h dose D ≤ 100 (8 h at 75 dBA in orbit); hazardous ≥ 85 dBA; alarms < 95 dBA; sleeping quarters NC-40 | [V2 6115] [V2 6077] [V2 6081] [V2 6079] | Optional sensor |
| Vibration during sleep | < 0.01 g RMS per 2 min interval | [V2 6092] | Optional sensor |
| Combustion gases | Monitoring ranges: CO 5 to 1000 ppm, HCN, HCl, HF 2 to 50 ppm | Table 6.2-3 | These are ranges the sensor must cover, not health limits |

### Level 2: radiation (very differentiating, there is real data)

| Parameter | Value | Requirement |
| --- | --- | --- |
| GCR dose in free space | < 1.3 mSv/day | [V1 4033] |
| GCR dose on a planetary surface | < 0.9 mSv/day | [V1 4033] |
| Career effective dose | < 600 mSv | [V1 4030] |
| Dose per solar particle event | < 250 mSv | [V1 4031] |
| More than 50 mSv per solar event | Requires area or personal monitors | Table 6.8-1 |
| More than 75 mSv accumulated over several missions | Requires additional monitoring | Table 6.8-1 |
| Limits per organ at 30 days, 1 year and career | Blood: 250 and 500 mGy-Eq. Circulatory: 250, 500 and 1,000. Lens: 1,000, 2,000 and 4,000. Skin: 1,500, 3,000 and 6,000. CNS: 500, 1,000 and 1,500 mGy | Table 4.8-1 |

Use real RadLab data to feed the simulator and the standard for the limits. The standard's doses depend on specific NASA models (Q model, 2009 solar-minimum GCR spectrum), so our prototype's values will be approximate.

### Level 3: body criteria relative to the baseline

| Parameter | Criterion | Requirement |
| --- | --- | --- |
| Aerobic capacity in mission | ≥ 80% of the pre-mission value | [V1 4003] |
| Absolute VO₂max | ≥ 32.9 mL/min/kg (EVA in microgravity); ≥ 36.5 (EVA on a surface) | [V1 4001] [V1 4002] |
| Muscle strength in mission | ≥ 80% of the baseline | [V1 4024] |
| Bone density in mission | ≥ 95% of the previous one (hip and spine); ≥ 90% (femoral neck) | [V1 4027] |
| Daily energy | 3,035 kcal average per crew member, or EER formula with activity factor of 1.0 to 1.25; +200 kcal per hour of EVA | [V2 7003] [V2 7004] |
| Vitamin D | 25 µg per day | Table 7.1-2 |
| Sleep (configurable default value) | Period of 8.5 h, plus 2 h before and 1.5 h after; circadian minimum between 1 and 7 AM | [V1 6001] (rationale, not a requirement) |

### Level 4: qualitative knowledge for the knowledge port (RAG)

- **CO₂ symptoms:** headache between 2.8 and 4.5 mmHg; fatigue, poor sleep and nausea above 4.5 (TB-004).
- **Hypoxia symptoms:** mental changes sometimes imperceptible to the astronaut, reduced vision, fatigue, nausea, headache, dizziness, hyperventilation (TB-003). It is an argument in favor of the alarm coming from the environmental sensor and not from the astronaut themselves.
- **Hyperoxia:** reduces ventilation and heart rate; the treatment is lowering the ppO₂ (TB-003).
- **Decompression sickness:** treatment with recompression and 100% O₂ (TB-003).
- **Space motion sickness:** lasts about 3 days on average (TB-044).
- **Role of the Crew Medical Officer (CMO):** two per increment; the medical decision rests with the flight surgeon on the ground, with the international medical group in acute cases. It helps define when the alert escalates to Ground (TB-044).
- **Measurements on board (medical kit checklist):** blood oximeter, blood pressure monitor, thermometer, stethoscope, otoscope, tonometer, urine strips.
- **Measures to activate:** the medical kit gives drug categories per condition (nausea, sleep, pain, allergies, altitude sickness with acetazolamide, among others). It serves for the catalog of actions.

### What is not in the public documents

- Thresholds for heart rate, blood pressure and SpO₂. Another citable source will have to be used (for example the NEWS2 scale) or they must be labeled as demonstration parameters.
- Critical values for hematology and immunology, and limits on work and sleep hours: the standard says they exist but does not publish them in this text.
- CO₂ limits at 24 h, 7 and 1000 days in the standard: they did not appear in the part of Vol. 2 that was read. The value of 2.5 mmHg at 7 days comes from the CO₂ Technical Brief.
- Table 10.3-1 (alerts) of Vol. 2: it did not appear in the stretch read.
- Oxygen consumption per crew member for the mission budget: not confirmed in this reading.

### Proposed structure for the rule catalog

Each rule as a record with: parameter, operator, value, unit, time window, severity, source requirement and state (verified in the standard, derived from a Technical Brief or demonstration parameter). This way the knowledge port can show the source of each alert and the demonstration adapter is marked.

## 5d. Sketch of ideas we can implement

Loose notes on what we have been discussing. They are ideas to build, not closed things.

### Local autonomous mode

The whole system lives on a local machine on board, without depending on the link to mission control. The data, the rules and the NASA PDFs stay inside. If the connection is cut, the crew keeps receiving alerts and recommendations with their source. When the link returns, it syncs with Ground.

To decide:

- What is uploaded to mission control on reconnecting and whether the astronaut chooses what to share.
- Whether the document search only returns passages with their citation or also writes with a language model.

### What mission control would see

All the data would be visible from mission control when there is a connection: vital signs, cabin environment, radiation, sleep and the alerts that have been generated.

### Sleep data

What we found in NASA sources:

- Astronauts use actigraphy wristbands (Actiwatch Spectrum), which measure movement and ambient light on the wrist. They serve to estimate hours of sleep, not the stages.
- The Standard Measures study uses a questionnaire before and after sleeping on sleep quality, mood, team cohesion and performance.
- Each astronaut has a crew quarter for sleeping, with a noise limit of NC-40 according to the standard.
- Astronauts sleep on average about six hours in space.

What we did not find: a sleeping compartment that measures sleep by itself. We leave that part as an idea to explore, for example a sleep module with noise, light, temperature and movement sensors.

Data that mission control could see per astronaut: hours of sleep per night, multi-day trend against their baseline, ambient light, questionnaire answers and room noise.

### Assistant with a local language model

Use a local model with Ollama instead of an external API such as OpenAI, Gemini or Anthropic, so it works without internet.

Planned flow, built on n8n:

1. Sensors and rules go first through the backend.
2. When there is an event, the backend sends it to the agent in n8n.
3. The agent queries the RAG with the NASA PDFs.
4. With what it finds, it summarizes and returns the answer with its source.

The idea is that Ollama only uses the RAG as a complementary tool. The rules remain what decides when there is an alert, and the model takes care of explaining it.

Cautions to keep in mind:

- The model should answer only with what was retrieved from the RAG and say it does not have the information if there is no passage that supports it, so it does not invent medical protocols.
- Test a small model that runs well on the demo machine.

### Voice input

So the crew does not have to type, an astronaut can speak and the system transcribes what they say to text. That text goes through Ollama and the RAG.

Planned flow: voice, local transcription (for example Whisper, which runs without internet), text, agent with RAG, answer as text or with a local voice.

Cautions to keep in mind:

- The transcription can fail with medical terms or with cabin noise, so it is advisable to show what was transcribed for confirmation before acting.
- In an emergency, the alert must not depend on the astronaut speaking. It must come from the sensors.

### Voice: Whisper first, Alexa as a fallback

The idea is to use Whisper as the main transcription. If we see we get stuck with the transcription, we use Alexa as a fallback for the demo. Since the project is in hexagonal architecture, voice is an interchangeable adapter and the core, the rules and Ollama do not change.

Two development profiles (configurations activated when starting the project, not user profiles):

- **Presentation profile:** activates the Alexa adapter for voice, in case Whisper does not work well for us. It requires creating the Alexa skill and a public endpoint (for example with a tunnel) so Alexa reaches the backend or n8n.
- **Jury profile:** activates the local Whisper adapter and works entirely without the Alexa connection. It is the one that shows the autonomous system, without internet.

Notes to keep at hand:

- The profiles are switched with a profile environment variable. There are three values: dev1 starts with Whisper, dev2 starts with Alexa and jury starts with Whisper. The dev profiles are for development and the jury profile is so that the competition's jury can run everything correctly. That dev1 and jury use the same thing is on purpose: it separates what is development from what is delivery and shows that there is order in the profiles. The exact name of the variable and the default value are yet to be defined.
- Alexa processes voice in the cloud, so it is not autonomous. It is a temporary adapter for the demo, and it is advisable to say so in the presentation.
- A skill in development mode runs only on our account, which is enough for the demo.
- Have a plan B with written text in case the event's wifi fails.
- Time estimate for Whisper: one or two hours to have the first transcription connected to the backend, and another hour or two of tests with background noise and medical terms. It is a general estimate, not verified with our team.

### Delivery for the jury with Docker

The jury is going to review the code and also run the program. To avoid the problem of it working on our computer and not on theirs, we are going to create a Docker image and publish it on Docker Hub, so they can run it in a container without installing anything by hand.

Ideas to keep at hand:

- The image should start by default with the jury profile, which uses local Whisper and does not need Alexa.
- The profile should be changeable with the environment variable when running the container, for example to use dev1 or dev2 ourselves.
- Include in the image everything it needs without internet: the backend, the rule base, the already indexed NASA PDFs and the Whisper model. This way the jury does not wait for downloads or depend on the event's network.
- Ollama and its model take a lot of space. We have to decide whether they go inside the same image or in a second container, for example with Docker Compose together with n8n.
- Leave in the README the exact command to download and run the image, and the link to the repository with the code.

To check:

- The final size of the image, so that downloading it from Docker Hub does not take too long.
- Whether the jury's machine has a graphics card. Without one, Ollama and Whisper will run slower and we have to test with a small model.
- The microphone inside the container: accessing the machine's audio from Docker can give problems depending on the operating system, and it is advisable to have text input as an alternative.

### Additional gases: nitrogen, methane and water vapor

Idea to extend the cabin indices with three more gases. Notes on where we are with each one:

- **Nitrogen:** today we only have it indirectly, as a diluent gas. The standard requires at least 30% diluent gas in the atmosphere ([V2 6002]) and nitrogen is the most common diluent. The idea is to measure it as its own gas and compute its partial pressure, just like oxygen.
- **Methane:** it does not appear in anything we have read. The standard refers to a list of maximum allowable limits for air contaminants (SMAC, document JSC-20584), which we have not opened yet. Until it is reviewed, any methane threshold would be demonstration data and must be labeled as such.
- **Water vapor:** we already have relative humidity with its limits (18 °C with 75% up to 27 °C with 25%, and the performance zone of 20 to 25 °C with 30 to 60%). The idea is to also show it as a gas of the mixture. A useful fact: the water vapor pressure in the lungs is 47 mmHg, and it is the one subtracted when computing inspired oxygen.

To decide:

- Whether nitrogen and water vapor are read from their own sensors or computed from the other data.
- Open the contaminants list (SMAC) to see whether it includes methane and with what limits.

## 6. Decisions

| Decision | Date | Reason |
| --- | --- | --- |
|  |  |  |

## 7. Pending items

- [ ]  Read the official challenge page and its resources
- [ ]  Define the MVP scope according to the remaining time
- [ ]  Assign team roles
- [x]  Choose which public NASA PDFs to use and check that they can be downloaded (see section 5b; several documents remain to be opened)
- [ ]  Find a source for body vital-sign thresholds (see 5c; they are not in Vol. 1, Vol. 2 or the Technical Briefs read)
- [ ]  Decide whether the rule catalog is written in JSON and who maintains it
- [ ]  Test a small model with Ollama on the demo machine
- [ ]  Test local Whisper with background noise
- [x]  Define the development profiles and how to switch between them: it was decided with an environment variable with three values (dev1 with Whisper, dev2 with Alexa, jury with Whisper)
- [ ]  Choose the name of the environment variable and its default value
- [ ]  Open the air contaminants list (SMAC, JSC-20584) and look for methane
- [ ]  Decide whether nitrogen and water vapor are measured or computed
- [ ]  Create the Dockerfile and publish the image on Docker Hub
- [ ]  Decide whether Ollama goes in the same image or in a separate container with Docker Compose
- [ ]  Test the container on another computer, without internet, before delivering
- [ ]  Write in the README the command to download and run the image
- [ ]  Create the Alexa skill and the tunnel only if Whisper gets stuck
- [ ]  Build the flow in n8n: backend, agent, RAG and response
- [ ]  Decide which sleep data we are going to simulate
- [ ]  Confirm whether "RAC" was RAG and decide whether the system uses a language model or only passage search

## 8. Sources

- [Challenge summary (Sonoma State)](https://edeon.sonoma.edu/nasaspaceapps-26/)
- [NASA: Space Apps 2026](https://science.nasa.gov/universe/nasa-welcomes-all-ages-experience-levels-for-space-apps-challenge/)
- [AstroHealth](https://github.com/Ridwanulkarim/nasa-challenge-Create-Health-Monitoring-Software-for-Astronauts-on-Space-Missions)
- [AURORA](https://github.com/fabriciojunio/aurora-astronaut-health)
- [Crew Health Monitor](https://github.com/AdityaK0804/Crew-Health-Monitor)
