import { useState } from "react";
import type { Command, Incident, IncidentType, Zone } from "../model";
import { label, time } from "../model";
import { Badge, Empty, EvidenceBadge, Modal, Panel } from "./Common";
interface Props {
  incidents: Incident[];
  zones: Zone[];
  types: IncidentType[];
  run: (command: Command) => Promise<boolean>;
  pending: boolean;
  personal?: boolean;
  title?: string;
}
export function IncidentPanel({
  incidents,
  zones,
  types,
  run,
  pending,
  personal = false,
  title,
}: Props) {
  const [filter, setFilter] = useState("open");
  const [selected, setSelected] = useState<Incident | null>(null);
  const [report, setReport] = useState(false);
  const [note, setNote] = useState("");
  const [typeKey, setTypeKey] = useState(types[0]?.key ?? "");
  const incident = incidents.find((i) => i.id === selected?.id) ?? selected;
  const chosen = types.find((t) => t.key === typeKey) ?? types[0];
  const visible = incidents
    .filter(
      (i) =>
        filter === "all" ||
        (filter === "resolved"
          ? i.status === "RESOLVED"
          : i.status !== "RESOLVED"),
    )
    .slice()
    .sort((a, b) => b.openedAt.localeCompare(a.openedAt));
  return (
    <Panel
      title={title ?? (personal ? "My tickets" : "Incidents")}
      subtitle={
        personal
          ? "Reported by or assigned to you"
          : "Shared habitat incidents · newest first"
      }
      actions={
        <button
          className="button primary"
          disabled={!types.length || !zones.length}
          onClick={() => setReport(true)}
        >
          ＋ Report incident
        </button>
      }
    >
      <div className="segments" aria-label="Incident status">
        {["open", "resolved", "all"].map((v) => (
          <button
            key={v}
            aria-pressed={filter === v}
            onClick={() => setFilter(v)}
          >
            {v[0].toUpperCase() + v.slice(1)}
          </button>
        ))}
      </div>
      <div>
        {visible.length ? (
          visible.map((i) => (
            <article className="ticket-item" key={i.id}>
              <span className={`incident-mark sev-${i.severity}`}>▲</span>
              <div className="item-copy">
                <span className="ticket-code">
                  {i.code} · {label(i.status)}
                </span>
                <button
                  className="item-title"
                  onClick={() => {
                    setSelected(i);
                    setNote("");
                  }}
                >
                  {i.title}
                </button>
                <p>
                  {zones.find((z) => z.id === i.zoneId)?.name ?? "Zone"} ·{" "}
                  {time(i.openedAt)} · {label(i.source)}
                </p>
                {i.valuesNormal && i.status !== "RESOLVED" && (
                  <span className="tag">
                    Readings normalized · review before resolving
                  </span>
                )}
              </div>
              <Badge severity={i.severity} />
            </article>
          ))
        ) : (
          <Empty>
            {filter === "resolved"
              ? "No resolved tickets."
              : "No open incidents in this scope."}
          </Empty>
        )}
      </div>
      {incident && (
        <Modal
          title={`${incident.code} · ${incident.title}`}
          onClose={() => setSelected(null)}
        >
          <div className="badge-row">
            <Badge severity={incident.severity} />
            <span className="tag">{label(incident.status)}</span>
            <span className="tag">
              {personal ? "Personal ticket" : "Zone incident"}
            </span>
          </div>
          <p>{incident.description || "No description provided."}</p>
          <dl>
            <dt>Location</dt>
            <dd>
              {zones.find((z) => z.id === incident.zoneId)?.name ?? "Zone"}
            </dd>
            <dt>Source</dt>
            <dd>{label(incident.source)}</dd>
            <dt>Opened</dt>
            <dd>{time(incident.openedAt)}</dd>
          </dl>
          <h3>Activity history</h3>
          {incident.updates.length ? (
            <ol className="history-list">
              {incident.updates.map((u, i) => (
                <li key={i}>
                  <time>{time(u.at)}</time>
                  <p>{u.note}</p>
                </li>
              ))}
            </ol>
          ) : (
            <p className="muted">No updates recorded.</p>
          )}
          {incident.status !== "RESOLVED" && (
            <>
              <label className="field">
                Resolution note
                <textarea
                  maxLength={1500}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                />
              </label>
              <div className="actions">
                <button
                  className="button"
                  disabled={pending || incident.status === "ACKNOWLEDGED"}
                  onClick={() =>
                    void run({ type: "acknowledgeIncident", id: incident.id })
                  }
                >
                  Acknowledge
                </button>
                <button
                  className="button primary"
                  disabled={pending || !note.trim()}
                  onClick={() =>
                    void run({
                      type: "resolveIncident",
                      id: incident.id,
                      note: note.trim(),
                    }).then((ok) => {
                      if (ok) setSelected(null);
                    })
                  }
                >
                  Resolve incident
                </button>
              </div>
              <p className="muted">
                Automatic incidents cannot close while zone alerts remain
                active.
              </p>
            </>
          )}
        </Modal>
      )}
      {report && (
        <Modal title="Report an incident" onClose={() => setReport(false)}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              void run({
                type: "reportIncident",
                zoneId: String(f.get("zoneId")),
                typeKey: chosen!.key,
                description: String(f.get("description")).trim(),
              }).then((ok) => {
                if (ok) setReport(false);
              });
            }}
          >
            <label className="field">
              Location
              <select name="zoneId" required>
                {zones.map((z) => (
                  <option key={z.id} value={z.id}>
                    {z.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Incident type
              <select
                value={chosen?.key ?? ""}
                required
                onChange={(e) => setTypeKey(e.target.value)}
              >
                {types.map((t) => (
                  <option key={t.key} value={t.key}>
                    {t.categoryName} · {t.name}
                  </option>
                ))}
              </select>
            </label>
            {chosen && (
              <div className="badge-row">
                <Badge severity={chosen.defaultSeverity} />
                <EvidenceBadge state={chosen.evidenceState} />
                <span className="muted">Catalog default severity</span>
              </div>
            )}
            <label className="field">
              Observation
              <textarea
                name="description"
                maxLength={3000}
                placeholder="Describe what you observed"
              />
            </label>
            <button className="button primary" disabled={pending || !chosen}>
              Submit report
            </button>
          </form>
        </Modal>
      )}
    </Panel>
  );
}
