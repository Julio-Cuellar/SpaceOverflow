import type { Mission } from "../data/useMission";
import {
  Badge,
  CrewCard,
  Empty,
  EvidenceBadge,
  Heading,
  Metric,
  Panel,
} from "../ui/Common";
import { time } from "../model";
export function Overview({ mission }: { mission: Mission }) {
  const { data, run, pending } = mission;
  const alerts = data.alerts
    .slice()
    .sort(
      (a, b) =>
        ["NORMAL", "ATENCION", "ALERTA", "CRITICO"].indexOf(b.severity) -
        ["NORMAL", "ATENCION", "ALERTA", "CRITICO"].indexOf(a.severity),
    );
  return (
    <>
      <Heading
        eyebrow="MISSION CONTROL · LIVE OPERATIONS"
        title="Mission overview"
        subtitle="Crew health and habitat conditions at a glance."
        actions={
          <button className="button" onClick={mission.reload}>
            ↻ Refresh
          </button>
        }
      />
      {data.crew.length > 0 && (
        <section className="crew-section">
          <div className="section-title">
            <div>
              <h2>Astronaut health monitoring</h2>
              <p>Individual readings · source labels per metric</p>
            </div>
          </div>
          <div className="crew-grid">
            {data.crew.map((p) => (
              <CrewCard key={p.id} person={p} />
            ))}
          </div>
        </section>
      )}
      {!data.crew.length && (
        <div className="inline-notice">
          Crew profiles and wearable measurements are awaiting the crew service.
          No personal readings are inferred from habitat sensors.
        </div>
      )}
      <div className="overview-layout">
        <section>
          <div className="section-title">
            <h2>Habitat conditions</h2>
            {data.dashboard && (
              <Badge severity={data.dashboard.globalSeverity} />
            )}
          </div>
          <div className="metric-grid">
            {data.dashboard?.vitals.map((v) => (
              <Metric key={v.key} vital={v} />
            ))}
          </div>
          {data.dashboard?.vitals.length === 0 && (
            <Empty>No sensor readings yet.</Empty>
          )}
        </section>
        <Panel
          title="Active alerts"
          subtitle="Severity and evidence are shown independently"
        >
          {alerts.length ? (
            alerts.map((a) => (
              <article className={`alert-detail sev-${a.severity}`} key={a.id}>
                <div className="section-title">
                  <h3>{a.ruleKey}</h3>
                  <Badge severity={a.severity} />
                </div>
                <p>
                  {data.ship?.zones.find((z) => z.id === a.zoneId)?.name ??
                    "Habitat"}{" "}
                  · {time(a.raisedAt)}
                </p>
                <div className="badge-row">
                  <EvidenceBadge state={a.rule.evidenceState} />
                  <span className="tag">
                    {a.status === "ACKNOWLEDGED" ? "Acknowledged" : "Open"}
                  </span>
                </div>
                {a.recommendation ? (
                  <>
                    <p>{a.recommendation.body}</p>
                    {a.recommendation.citations.map((c, i) => (
                      <details className="citation" key={i}>
                        <summary>
                          {c.documentCode}
                          {c.requirementRef ? " · " + c.requirementRef : ""}
                        </summary>
                        <p>{c.excerpt}</p>
                        <EvidenceBadge state={c.evidenceState} />
                      </details>
                    ))}
                  </>
                ) : (
                  <p className="muted">
                    A cited recommendation is not available yet.
                  </p>
                )}
                <button
                  className="button"
                  disabled={pending || a.status === "ACKNOWLEDGED"}
                  onClick={() =>
                    void run({ type: "acknowledgeAlert", id: a.id })
                  }
                >
                  {a.status === "ACKNOWLEDGED"
                    ? "Acknowledged"
                    : "Acknowledge alert"}
                </button>
              </article>
            ))
          ) : (
            <Empty>No active alerts in the available dataset.</Empty>
          )}
        </Panel>
      </div>
      <Panel title="Recent incidents" subtitle="Shared habitat events">
        {data.incidents.slice(0, 4).map((i) => (
          <article className="ticket-item" key={i.id}>
            <div className="item-copy">
              <span className="ticket-code">{i.code}</span>
              <h3>{i.title}</h3>
              <p>
                {data.ship?.zones.find((z) => z.id === i.zoneId)?.name ??
                  "Zone"}{" "}
                · {time(i.openedAt)}
              </p>
            </div>
            <Badge severity={i.severity} />
          </article>
        ))}
        {!data.incidents.length && <Empty>No incidents reported.</Empty>}
      </Panel>
    </>
  );
}
