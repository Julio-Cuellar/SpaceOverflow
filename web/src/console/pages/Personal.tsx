import { useEffect, useState } from "react";
import type { Mission } from "../data/useMission";
import type { Series } from "../model";
import { time, metricLabels } from "../model";
import {
  Badge,
  BodyOutline,
  Empty,
  EvidenceBadge,
  Heading,
  Panel,
} from "../ui/Common";
import { TaskPanel } from "../ui/Tasks";
import { IncidentPanel } from "../ui/Incidents";
import { ZoneTrends } from "../ui/Charts";
export function Personal({
  mission,
  section,
}: {
  mission: Mission;
  section: string;
}) {
  const session = mission.data.session;
  const [series, setSeries] = useState<Series[]>([]);
  const [sensorError, setSensorError] = useState("");
  const zoneId = session?.zoneId;
  useEffect(() => {
    if (!zoneId) return;
    let active = true;
    const controller = new AbortController();
    const load = async () => {
      try {
        const data = await mission.gateway.series(
          zoneId,
          new Date(Date.now() - 60000).toISOString(),
          new Date().toISOString(),
          controller.signal,
        );
        if (active) {
          setSeries(data);
          setSensorError("");
        }
      } catch {
        if (active) setSensorError("Current zone readings are unavailable.");
      }
    };
    void load();
    const timer = setInterval(() => void load(), 10000);
    return () => {
      active = false;
      controller.abort();
      clearInterval(timer);
    };
  }, [mission.gateway, zoneId]);
  if (!session)
    return (
      <>
        <Heading
          eyebrow="PERSONAL WORKSPACE"
          title="My crew dashboard"
          subtitle="Your health, your activities, your space."
        />
        <Empty>
          {mission.states.session === "loading"
            ? "Loading your session…"
            : (mission.errors.session ??
              "An authenticated crew session is required.")}
        </Empty>
        <button className="button" onClick={mission.reload}>
          Retry session
        </button>
      </>
    );
  const person = session.crewMember;
  const zone = mission.data.ship?.zones.find((z) => z.id === session.zoneId);
  const zones = mission.data.ship?.zones ?? [];
  const next = session.tasks
    .filter((t) => t.status === "PENDING")
    .sort((a, b) => (a.dueAt ?? "").localeCompare(b.dueAt ?? ""))[0];
  const habitat = (
    <>
      <Heading
        eyebrow="YOUR CURRENT WORKSPACE"
        title="My habitat"
        subtitle={zone?.name ?? "Assigned zone"}
      />
      <div className="habitat-layout">
        <Panel
          title={mission.data.ship?.name ?? "Current habitat"}
          subtitle="Current assigned zone · shared environmental context"
        >
          <div className="dome-illustration">
            <svg
              viewBox="0 0 520 240"
              role="img"
              aria-label="Illustrative habitat dome"
            >
              <path
                d="M66 194A194 170 0 0 1 454 194Z"
                fill="#65b5cb16"
                stroke="#65b5cb"
                strokeWidth="2"
              />
              <path
                d="M146 194Q146 26 260 24Q374 26 374 194M260 24V194M94 111H426M70 160H450"
                stroke="#65b5cb66"
                fill="none"
              />
              <path d="M60 197H460" stroke="#a2d4d5" strokeWidth="4" />
              <text
                x="260"
                y="225"
                textAnchor="middle"
                fill="#b9c6d9"
                fontSize="12"
              >
                HABITAT CONCEPT · NOT TO SCALE
              </text>
            </svg>
          </div>
          <h3>{zone?.name ?? "Zone unavailable"}</h3>
          {zone && <Badge severity={zone.status} />}
        </Panel>
        <Panel
          title="Environmental readings"
          subtitle="Your zone sensors · distinct from personal measurements"
        >
          {sensorError ? (
            <Empty>{sensorError}</Empty>
          ) : (
            <div className="environment-grid">
              {series.map((s) => (
                <article className="environment-reading" key={s.metric}>
                  <span>{metricLabels[s.metric] ?? s.metric}</span>
                  <b>
                    {s.points.at(-1)?.avg.toFixed(2) ?? "—"}{" "}
                    <small>{s.unit}</small>
                  </b>
                  <span className="muted">
                    {s.points.at(-1) ? time(s.points.at(-1)!.ts) : "No samples"}
                  </span>
                </article>
              ))}
            </div>
          )}
        </Panel>
      </div>
      <IncidentPanel
        incidents={mission.data.incidents.filter(
          (i) => i.zoneId === session.zoneId,
        )}
        title="My zone incidents"
        zones={zones}
        types={mission.data.incidentTypes}
        run={mission.run}
        pending={mission.pending}
      />
      {zone && <ZoneTrends key={zone.id} mission={mission} zoneId={zone.id} />}
    </>
  );
  if (section === "habitat") return habitat;
  if (section === "routine")
    return (
      <>
        <Heading
          eyebrow="YOUR DAILY RHYTHM"
          title="My routine"
          subtitle="Personal schedule · today · all times in UTC"
        />
        <TaskPanel
          tasks={session.tasks.filter(
            (t) => t.kind !== "INCIDENT" && !t.sourceAlertId,
          )}
          zones={zones}
          run={mission.run}
          pending={mission.pending}
          routine
        />
      </>
    );
  return (
    <>
      <Heading
        eyebrow="CREW WORKSPACE · PERSONAL SESSION"
        title={`Hello, ${person.name}.`}
        subtitle="Your health, your activities, your space."
      />
      <div className="personal-overview">
        <Panel
          title="My health"
          subtitle="Latest personal wearable measurements"
          actions={<Badge severity={person.state} />}
        >
          <div className="personal-health">
            <div
              className={`personal-portrait portrait-${person.portrait}`}
              role="img"
              aria-label={`Illustrative portrait of ${person.name}`}
            >
              <span>
                {person.name}
                <small>{person.role}</small>
              </span>
            </div>
            <div className="personal-vitals">
              {person.bloodPressure && (
                <div>
                  <span>Blood pressure</span>
                  <b>
                    {person.bloodPressure.systolic}/
                    {person.bloodPressure.diastolic}{" "}
                    <small>{person.bloodPressure.unit}</small>
                  </b>
                  <EvidenceBadge state={person.bloodPressure.evidenceState} />
                  <span className="origin-label">
                    {person.bloodPressure.origin === "SIMULATED"
                      ? "Simulated"
                      : person.bloodPressure.origin === "REPLAY"
                        ? "Replay"
                        : "Sensor"}
                  </span>
                </div>
              )}
              {person.vitals.map((v) => (
                <div key={v.key}>
                  <span>{metricLabels[v.key] ?? v.label}</span>
                  <b>
                    {v.value} <small>{v.unit}</small>
                  </b>
                  <EvidenceBadge state={v.evidenceState} />
                  <span className="origin-label">
                    {v.origin === "SIMULATED"
                      ? "Simulated"
                      : v.origin === "REPLAY"
                        ? "Replay"
                        : "Sensor"}
                  </span>
                </div>
              ))}
            </div>
            <div className="personal-body">
              <BodyOutline />
            </div>
          </div>
        </Panel>
        <Panel
          title="Your next activity"
          subtitle="Personal daily schedule"
          className="next-activity"
        >
          {next ? (
            <>
              <span className="eyebrow">{time(next.dueAt)}</span>
              <h3>{next.title}</h3>
              <p>
                {zones.find((z) => z.id === next.zoneId)?.name ??
                  "Personal workspace"}
              </p>
              <div className="schedule-track">
                <span />
              </div>
              <p className="muted">
                Review the activity in My tasks, or open My routine for the full
                schedule.
              </p>
            </>
          ) : (
            <Empty>All activities complete.</Empty>
          )}
        </Panel>
      </div>
      <div className="two-columns">
        <TaskPanel
          tasks={session.tasks}
          zones={zones}
          run={mission.run}
          pending={mission.pending}
        />
        <IncidentPanel
          personal
          incidents={session.incidents}
          zones={zones}
          types={mission.data.incidentTypes}
          run={mission.run}
          pending={mission.pending}
        />
      </div>
      <Panel
        title="Your workspace at a glance"
        subtitle="Environmental status for your assigned zone"
      >
        <div className="section-title">
          <h3>{zone?.name ?? "Assigned zone"}</h3>
          {zone && <Badge severity={zone.status} />}
        </div>
        <p>
          {zone?.openIncidents ?? 0} shared zone incidents · See My habitat for
          sensor values and details.
        </p>
        <div className="environment-grid">
          {series.slice(0, 5).map((s) => (
            <div className="environment-reading" key={s.metric}>
              <span>{metricLabels[s.metric] ?? s.metric}</span>
              <b>
                {s.points.at(-1)?.avg.toFixed(2) ?? "—"} <small>{s.unit}</small>
              </b>
            </div>
          ))}
        </div>
        {sensorError && <p>{sensorError}</p>}
      </Panel>
    </>
  );
}
