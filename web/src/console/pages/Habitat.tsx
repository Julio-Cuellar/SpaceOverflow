import { useState } from "react";
import type { Mission } from "../data/useMission";
import type { Zone } from "../model";
import { label } from "../model";
import { Badge, Empty, EvidenceBadge, Heading, Panel } from "../ui/Common";
import { IncidentPanel } from "../ui/Incidents";
import { ZoneTrends } from "../ui/Charts";
export function HabitatMap({
  mission,
  selected,
  onSelect,
}: {
  mission: Mission;
  selected: string;
  onSelect: (id: string) => void;
}) {
  const ship = mission.data.ship;
  if (!ship) return <Empty>Habitat layout is not available.</Empty>;
  return (
    <svg
      className="habitat-map"
      viewBox={`0 0 ${ship.canvas.width} ${ship.canvas.height}`}
      role="group"
      aria-label="Selectable habitat zones"
    >
      {ship.zones.map((z) => (
        <g
          key={z.id}
          role="button"
          tabIndex={0}
          aria-pressed={selected === z.id}
          aria-label={`${z.name}, ${label(z.status)}, ${z.openIncidents} open incidents`}
          onClick={() => onSelect(z.id)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              onSelect(z.id);
            }
          }}
          className={`map-zone sev-${z.status} ${selected === z.id ? "selected" : ""}`}
        >
          <rect
            x={z.layout.x}
            y={z.layout.y}
            width={z.layout.w}
            height={z.layout.h}
            rx="3"
          />
          <text
            x={z.layout.x + z.layout.w / 2}
            y={z.layout.y + z.layout.h / 2}
            textAnchor="middle"
            fontSize="11"
          >
            {z.name}
          </text>
          <text
            x={z.layout.x + z.layout.w / 2}
            y={z.layout.y + z.layout.h / 2 + 20}
            textAnchor="middle"
            fontSize="9"
          >
            {z.openIncidents
              ? "▲ " + z.openIncidents + " incidents"
              : "● " + label(z.status)}
          </text>
        </g>
      ))}
    </svg>
  );
}
export function Habitat({ mission }: { mission: Mission }) {
  const [selected, setSelected] = useState("");
  const [scenario, setScenario] = useState("co2_slow");
  const [speed, setSpeed] = useState(1);
  const zones = mission.data.ship?.zones ?? [];
  const zone = zones.find((z) => z.id === selected) ?? zones[0];
  const setZone = (z: Zone) => setSelected(z.id);
  return (
    <>
      <Heading
        eyebrow="HABITAT OPERATIONS"
        title="Ship environment"
        subtitle={
          mission.data.ship?.name ??
          "Zones, sensor history and incident management."
        }
        actions={
          <button className="button" onClick={mission.reload}>
            ↻ Refresh
          </button>
        }
      />
      <div className="habitat-layout">
        <Panel
          title="Habitat zone map"
          subtitle="Layout and zone dimensions are supplied by the backend"
        >
          <HabitatMap
            mission={mission}
            selected={zone?.id ?? ""}
            onSelect={setSelected}
          />
          <p className="muted">
            Select a zone · Status includes an icon and label
          </p>
        </Panel>
        <Panel
          title={zone?.name ?? "Selected zone"}
          subtitle="Zone status and open events"
        >
          {zone ? (
            <>
              <Badge severity={zone.status} />
              <dl>
                <dt>Zone code</dt>
                <dd>{zone.code}</dd>
                <dt>Deck</dt>
                <dd>{zone.deck}</dd>
                <dt>Open incidents</dt>
                <dd>{zone.openIncidents}</dd>
              </dl>
              <label className="field">
                Select workspace
                <select
                  value={zone.id}
                  onChange={(e) =>
                    setZone(zones.find((z) => z.id === e.target.value)!)
                  }
                >
                  {zones.map((z) => (
                    <option key={z.id} value={z.id}>
                      {z.name}
                    </option>
                  ))}
                </select>
              </label>
            </>
          ) : (
            <Empty>No zones available.</Empty>
          )}
        </Panel>
      </div>
      {zone && <ZoneTrends key={zone.id} mission={mission} zoneId={zone.id} />}
      <IncidentPanel
        incidents={mission.data.incidents.filter(
          (i) => !zone || i.zoneId === zone.id,
        )}
        zones={zones}
        types={mission.data.incidentTypes}
        run={mission.run}
        pending={mission.pending}
      />
      <Panel
        title="Incident catalog"
        subtitle="Versioned incident types and evidence from the backend"
      >
        <div className="catalog-grid">
          {mission.data.incidentTypes.map((t) => (
            <details key={t.key}>
              <summary>
                {t.categoryName} · {t.name}
              </summary>
              <div className="badge-row">
                <Badge severity={t.defaultSeverity} />
                <EvidenceBadge state={t.evidenceState} />
                <span className="tag">
                  {t.detection === "AUTO" ? "Automatic" : "Manual"}
                </span>
              </div>
              {t.suggestedActions.map((a, i) => (
                <p key={i}>{a}</p>
              ))}
            </details>
          ))}
          {!mission.data.incidentTypes.length && (
            <Empty>Incident catalog unavailable.</Empty>
          )}
        </div>
      </Panel>
      <Panel
        title="Simulation controls"
        subtitle="Demonstration only · Runs against the selected data adapter"
      >
        <div className="demo-controls">
          <label className="field">
            Scenario
            <select
              value={scenario}
              onChange={(e) => setScenario(e.target.value)}
            >
              {[
                ["co2_slow", "Slow CO₂ rise"],
                ["pressure_leak", "Pressure leak"],
                ["humidity_high", "High humidity"],
                ["o2_failure", "Oxygen failure"],
                ["heat", "Heat"],
              ].map(([v, t]) => (
                <option key={v} value={v}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Speed
            <input
              type="number"
              min="0.1"
              max="20"
              step="0.1"
              value={speed}
              onChange={(e) => setSpeed(Number(e.target.value))}
            />
          </label>
          {(["start", "stop"] as const).map((action) => (
            <button
              className={`button ${action === "start" ? "primary" : ""}`}
              key={action}
              disabled={mission.pending || !zone || !(speed > 0 && speed <= 20)}
              onClick={() =>
                zone &&
                void mission.run({
                  type: "scenario",
                  action,
                  key: scenario,
                  zone: zone.code,
                  speed,
                })
              }
            >
              {action === "start" ? "Start scenario" : "Stop scenario"}
            </button>
          ))}
        </div>
      </Panel>
    </>
  );
}
