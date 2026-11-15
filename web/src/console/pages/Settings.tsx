import { useEffect, useState } from "react";
import type { Mission } from "../data/useMission";
import type { Mode } from "../model";
import { restJson } from "../data/backend";
import { EvidenceBadge, Heading, Panel } from "../ui/Common";
export function Settings({ mission, mode }: { mission: Mission; mode: Mode }) {
  const [health, setHealth] = useState("Checking backend…");
  const [baseline, setBaseline] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    void restJson<{ status: string; profile?: string }>(
      `${import.meta.env.VITE_API_BASE || ""}/health`,
      { signal: controller.signal },
    )
      .then((h) =>
        setHealth(
          `Backend: ${h.status}${h.profile ? " · profile " + h.profile : ""}`,
        ),
      )
      .catch(() => {
        if (!controller.signal.aborted)
          setHealth(
            "Backend unavailable. Demo data is independent of backend availability.",
          );
      });
    return () => controller.abort();
  }, []);
  return (
    <>
      <Heading
        eyebrow="WORKSPACE PREFERENCES"
        title="Settings & system"
        subtitle="Data provenance, connectivity and personal privacy."
      />
      <div className="two-columns">
        <Panel title="System connection" subtitle="Service availability">
          <p>{health}</p>
          <p>
            Mission data:{" "}
            <b>
              {mode === "demo"
                ? "Explicit demonstration adapter"
                : "Backend GraphQL and WebSocket"}
            </b>
          </p>
          <p>Realtime: {mission.connection}</p>
          <p className="muted">
            No automatic switch to demonstration data occurs when a backend
            request fails.
          </p>
          <button className="button" onClick={mission.reload}>
            Retry mission data
          </button>
        </Panel>
        <Panel
          title="Evidence & sources"
          subtitle="Interpret severity and evidence separately"
        >
          <div className="badge-row">
            {(["VERIFICADO", "TB", "DEMO", "NO_VERIFICADO"] as const).map(
              (state) => (
                <EvidenceBadge key={state} state={state} />
              ),
            )}
          </div>
          <p>
            Verified evidence describes its source, not a confidence score.
            Simulated sensor values remain labeled even when the rule uses a
            verified source.
          </p>
          <a
            className="button"
            href={`${import.meta.env.VITE_API_BASE || ""}/api/v1/rules/catalog.json`}
            target="_blank"
            rel="noreferrer"
          >
            Open backend rule catalog ↗
          </a>
        </Panel>
        <Panel title="Personal privacy" subtitle="Current-session consent">
          <p>Sharing settings apply only to the signed-in crew member.</p>
          <label className="checkbox-label">
            <input
              type="checkbox"
              disabled={!mission.data.session || mission.pending}
              checked={mission.data.session?.sharedTasks ?? false}
              onChange={(e) =>
                void mission.run({
                  type: "setConsent",
                  category: "tasks",
                  shared: e.target.checked,
                })
              }
            />{" "}
            Share my task status with Ground
          </label>
          {mode === "backend" && (
            <p className="muted">
              Consent changes require the authenticated crew service.
            </p>
          )}
        </Panel>
        <Panel
          title="Personal baseline"
          subtitle="Profile integration boundary"
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void mission.run({
                type: "recordBaseline",
                metric: "heart_rate",
                value: Number(baseline),
              });
            }}
          >
            <label className="field">
              Resting heart rate (bpm)
              <input
                type="number"
                required
                min="1"
                step="0.1"
                value={baseline}
                onChange={(e) => setBaseline(e.target.value)}
              />
            </label>
            <button
              className="button"
              disabled={mission.pending || !mission.data.session}
            >
              Record baseline
            </button>
            {mission.data.session?.baselines?.map((b) => (
              <p key={b.metric}>Recorded baseline: {b.value} bpm</p>
            ))}
            <p className="muted">
              No clinical interpretation is calculated by the interface.
              Baseline persistence requires the crew service.
            </p>
          </form>
        </Panel>
      </div>
    </>
  );
}
