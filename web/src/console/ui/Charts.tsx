import { useEffect, useState } from "react";
import type { Mission } from "../data/useMission";
import type { Rule, Series } from "../model";
import { metricLabels, time } from "../model";
import { Empty, EvidenceBadge, Panel } from "./Common";
const parameters: Record<string, string> = { co2_mmhg: "ppco2" };
export function Trend({ series, rules }: { series: Series; rules: Rule[] }) {
  const fixed = rules.filter(
    (r) =>
      r.kind === "umbral" &&
      r.parameter === (parameters[series.metric] ?? series.metric),
  );
  if (!series.points.length)
    return <Empty>No measurements in this time window.</Empty>;
  const values = series.points.map((p) => p.avg);
  const min = Math.min(...values, ...fixed.map((r) => r.threshold));
  const max = Math.max(...values, ...fixed.map((r) => r.threshold));
  const padding = (max - min || 1) * 0.15;
  const low = min - padding;
  const span = max - min + 2 * padding;
  const y = (v: number) => 110 - ((v - low) / span) * 95;
  const from = new Date(series.points[0].ts).getTime();
  const to = new Date(series.points.at(-1)!.ts).getTime();
  const points = series.points
    .map(
      (p) =>
        `${35 + ((new Date(p.ts).getTime() - from) / (to - from || 1)) * 520},${y(p.avg)}`,
    )
    .join(" ");
  return (
    <figure className="trend">
      <figcaption>
        <b>{metricLabels[series.metric] ?? series.metric}</b>
        <span>
          {series.points.at(-1)!.avg.toFixed(2)} {series.unit}
        </span>
      </figcaption>
      <svg
        viewBox="0 0 580 145"
        role="img"
        aria-label={`${metricLabels[series.metric] ?? series.metric} history in ${series.unit}`}
      >
        <path
          d="M35 25H555M35 65H555M35 105H555"
          fill="none"
          stroke="#65b5cb25"
        />
        <text x="0" y="25" fill="#b9c6d9" fontSize="9">
          {max.toFixed(1)}
        </text>
        <text x="0" y="108" fill="#b9c6d9" fontSize="9">
          {min.toFixed(1)}
        </text>
        {fixed.map((r) => (
          <g key={r.key}>
            <line
              x1="35"
              x2="555"
              y1={y(r.threshold)}
              y2={y(r.threshold)}
              stroke="#ffad42"
              strokeDasharray="4 4"
            />
          </g>
        ))}
        <polyline
          points={points}
          fill="none"
          stroke="#65d7eb"
          strokeWidth="2"
        />
        <text x="35" y="138" fill="#b9c6d9" fontSize="9">
          {time(series.points[0].ts)}
        </text>
        <text x="490" y="138" fill="#b9c6d9" fontSize="9">
          {time(series.points.at(-1)!.ts)}
        </text>
      </svg>
      {fixed.map((r) => (
        <div key={r.key} className="chart-rule">
          Threshold {r.operator} {r.threshold} {r.unit} · {r.windowS}s{" "}
          <EvidenceBadge state={r.evidenceState} />
        </div>
      ))}
    </figure>
  );
}
export function ZoneTrends({
  mission,
  zoneId,
}: {
  mission: Mission;
  zoneId: string;
}) {
  const [hours, setHours] = useState(1);
  const [series, setSeries] = useState<Series[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    const load = async () => {
      try {
        const result = await mission.gateway.series(
          zoneId,
          new Date(Date.now() - hours * 3600000).toISOString(),
          new Date().toISOString(),
          controller.signal,
        );
        if (active) {
          setSeries(result);
          setError("");
        }
      } catch {
        if (active)
          setError(
            "History is unavailable. Current measurements are shown separately.",
          );
      } finally {
        if (active) setLoading(false);
      }
    };
    void load();
    const timer = setInterval(() => void load(), 10000);
    return () => {
      active = false;
      controller.abort();
      clearInterval(timer);
    };
  }, [mission.gateway, zoneId, hours]);
  return (
    <Panel
      title="Zone trends"
      subtitle="Historical readings · UTC"
      actions={
        <label className="compact-label">
          Window
          <select
            value={hours}
            onChange={(e) => {
              setLoading(true);
              setError("");
              setSeries([]);
              setHours(Number(e.target.value));
            }}
          >
            {[1, 6, 12, 24].map((h) => (
              <option key={h} value={h}>
                {h}h
              </option>
            ))}
          </select>
        </label>
      }
    >
      {error ? (
        <Empty>{error}</Empty>
      ) : loading ? (
        <Empty>Loading zone history…</Empty>
      ) : series.length ? (
        <div className="chart-grid">
          {series.map((s) => (
            <Trend key={s.metric} series={s} rules={mission.data.rules} />
          ))}
        </div>
      ) : (
        <Empty>No history available.</Empty>
      )}
    </Panel>
  );
}
