import { useEffect, useRef, type ReactNode } from "react";
import {
  evidenceLabels,
  severityLabels,
  type Evidence,
  type Severity,
  type Vital,
  metricLabels,
  type CrewMember,
} from "../model";
export function Badge({ severity }: { severity: Severity | null }) {
  if (severity === null)
    return <span className="status-pill sev-UNKNOWN">○ No wearable data</span>;
  return (
    <span className={`status-pill sev-${severity}`}>
      {{ NORMAL: "●", ATTENTION: "▲", ALERT: "◆", CRITICAL: "■" }[severity]}{" "}
      {severityLabels[severity] ?? "Unknown"}
    </span>
  );
}
export function EvidenceBadge({ state = "DEMO" }: { state?: Evidence }) {
  return (
    <span className="evidence">◇ {evidenceLabels[state] ?? "Unverified"}</span>
  );
}
export function Panel({
  title,
  subtitle,
  actions,
  children,
  className = "",
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`surface ${className}`}>
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}
export function Heading({
  eyebrow,
  title,
  subtitle,
  actions,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
  actions?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <div className="actions">{actions}</div>
    </div>
  );
}
export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty-state">{children}</div>;
}
export function Metric({ vital }: { vital: Vital }) {
  return (
    <article className="metric-tile">
      <span>{metricLabels[vital.key] ?? vital.label}</span>
      <div className="metric-value">
        {new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(
          vital.value,
        )}{" "}
        <small>{vital.unit}</small>
      </div>
      <div className="badge-row">
        <Badge severity={vital.severity} />
        <EvidenceBadge state={vital.evidenceState} />
        <span className="origin-label">
          {vital.origin === "SIMULATED"
            ? "Simulated"
            : vital.origin === "REPLAY"
              ? "Replay"
              : "Sensor"}
        </span>
      </div>
    </article>
  );
}
export function BodyOutline() {
  return (
    <svg
      viewBox="0 0 100 210"
      role="img"
      aria-label="Human body with simulated indicator locations"
    >
      <circle
        cx="50"
        cy="18"
        r="12"
        fill="#172849"
        stroke="#65b5cb"
        strokeWidth="2"
      />
      <path
        d="M39 34Q50 29 61 34L68 78 63 110 70 190 58 190 50 123 42 190 30 190 37 110 32 78Z"
        fill="#65b5cb22"
        stroke="#65b5cb"
        strokeWidth="2"
      />
      <path
        d="M35 43 20 82 25 86 40 62M65 43 80 82 75 86 60 62"
        fill="none"
        stroke="#65b5cb"
        strokeWidth="5"
      />
      <circle cx="54" cy="52" r="4" fill="#ff8a3d" />
      <circle cx="44" cy="72" r="4" fill="#65b5cb" />
      <circle cx="51" cy="94" r="4" fill="#a78dc2" />
    </svg>
  );
}
export function CrewCard({ person }: { person: CrewMember }) {
  const cardEvidence =
    person.vitals[0]?.evidenceState ?? person.bloodPressure?.evidenceState;
  return (
    <article className="crew-card">
      <div className="crew-name">
        <div>
          <h3>{person.name}</h3>
          <p>{person.role}</p>
        </div>
        <Badge severity={person.state} />
      </div>
      <div
        className={`crew-portrait portrait-${person.portrait}`}
        role="img"
        aria-label={`Illustrative portrait of ${person.name}`}
      />
      <div className="crew-secondary">
        {person.bloodPressure && (
          <div>
            <span>Blood pressure</span>
            <b>
              {person.bloodPressure.systolic}/{person.bloodPressure.diastolic}{" "}
              {person.bloodPressure.unit}
            </b>
          </div>
        )}
        {person.vitals
          .filter((v) => v.key === "radiation")
          .map((v) => (
            <div key={v.key}>
              <span>Radiation</span>
              <b>
                {v.value} {v.unit}
              </b>
            </div>
          ))}
      </div>
      <div className="crew-body">
        <BodyOutline />
        <div>
          {person.vitals
            .filter((v) => v.key !== "radiation")
            .map((v) => (
              <div className="crew-reading" key={v.key}>
                <span>{metricLabels[v.key] ?? v.label}</span>
                <b>
                  {v.value} {v.unit}
                </b>
              </div>
            ))}
          {cardEvidence ? (
            <EvidenceBadge state={cardEvidence} />
          ) : (
            <p className="muted">
              No wearable readings are available for this crew member.
            </p>
          )}
        </div>
      </div>
    </article>
  );
}
export function Modal({
  title,
  children,
  onClose,
  className = "",
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  className?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const close = useRef(onClose);
  useEffect(() => {
    close.current = onClose;
  }, [onClose]);
  useEffect(() => {
    const dialog = ref.current!;
    dialog.showModal();
    return () => dialog.close();
  }, []);
  return (
    <dialog
      className={`mission-dialog ${className}`}
      ref={ref}
      onCancel={(e) => {
        e.preventDefault();
        close.current();
      }}
    >
      <div className="dialog-heading">
        <h2>{title}</h2>
        <button
          className="icon-button"
          onClick={onClose}
          aria-label={`Close ${title}`}
        >
          ×
        </button>
      </div>
      {children}
    </dialog>
  );
}
