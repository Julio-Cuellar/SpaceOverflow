export type Severity = "NORMAL" | "ATTENTION" | "ALERT" | "CRITICAL";
export type Evidence = "VERIFIED" | "TB" | "DEMO" | "UNVERIFIED";
export type Origin = "REAL" | "SIMULATED" | "REPLAY";
export interface Vital {
  key: string;
  label: string;
  value: number;
  unit: string;
  severity: Severity;
  evidenceState: Evidence;
  origin: Origin;
  zoneId: string | null;
}
export interface Dashboard {
  habitatId: string;
  globalSeverity: Severity;
  vitals: Vital[];
}
export interface Zone {
  id: string;
  code: string;
  name: string;
  kind: string;
  deck: string;
  layout: { x: number; y: number; w: number; h: number };
  status: Severity;
  openIncidents: number;
}
export interface Ship {
  id: string;
  name: string;
  canvas: { width: number; height: number };
  zones: Zone[];
}
export interface Citation {
  documentCode: string;
  requirementRef: string | null;
  page?: number | null;
  excerpt: string;
  evidenceState: Evidence;
}
export interface Recommendation {
  body: string;
  composedBy?: string;
  sourceKind: string;
  actions: { key: string; title: string; description: string }[];
  citations: Citation[];
}
export interface Alert {
  id: string;
  ruleKey: string;
  zoneId: string | null;
  severity: Severity;
  status: "RAISED" | "ACKNOWLEDGED" | "RESOLVED";
  causeHint: string;
  raisedAt: string;
  rule: {
    sourceRequirement: string;
    sourceDocument: string;
    evidenceState: Evidence;
    parameter: string;
  };
  recommendation: Recommendation | null;
}
export interface Incident {
  id: string;
  code: string;
  title: string;
  description: string;
  severity: Severity;
  status: "OPEN" | "ACKNOWLEDGED" | "RESOLVED";
  source: "MANUAL" | "ALERT";
  zoneId: string;
  openedAt: string;
  valuesNormal: boolean;
  sourceAlertId: string | null;
  updates: { kind: string; note: string; at: string }[];
}
export interface IncidentType {
  key: string;
  name: string;
  category: string;
  categoryName: string;
  detection: "AUTO" | "MANUAL";
  defaultSeverity: Severity;
  evidenceState: Evidence;
  typicalZones: string[];
  suggestedActions: string[];
}
export type TaskKind = "HEALTH" | "SHIP" | "INCIDENT";
export interface Task {
  id: string;
  kind: TaskKind;
  origin: "GROUND" | "SYSTEM" | "CREW";
  title: string;
  zoneId: string | null;
  status: "PENDING" | "COMPLETED" | "BLOCKED";
  dueAt: string | null;
  blockedReason: string | null;
  effective: boolean | null;
  sourceAlertId: string | null;
  incidentId: string | null;
  templateId: string | null;
}
export interface Template {
  zoneCode?: string | null;
  recurrence?: "DAILY" | "ONCE";
  id: string;
  title: string;
  kind: "HEALTH" | "SHIP";
  status: "PENDING" | "APPLIED" | "COMPLETED" | "BLOCKED";
  blockedReason: string | null;
  cancelled: boolean;
}
export type PlanStage =
  | "DRAFT"
  | "QUEUED"
  | "IN_TRANSIT"
  | "RECEIVED"
  | "APPLIED"
  | "CONFIRMED"
  | "REJECTED";
export interface Ground {
  appliedVersion: number;
  templates: Template[];
  draft: { version: number; templates: Template[] } | null;
  published: {
    version: number;
    stage: PlanStage;
    reason: string | null;
    publishedAt: string;
    ackedAt: string | null;
  } | null;
  link: { online: boolean; delaySeconds: number; changedAt: string };
}
export interface GroundPlan {
  version: number;
  appliedAt: string | null;
  rejected: { title: string; reason: string }[];
}
export interface Rule {
  key: string;
  parameter: string;
  kind: string;
  operator: string;
  threshold: number;
  unit: string;
  windowS: number;
  severity: Severity;
  evidenceState: Evidence;
  sourceRequirement: string;
  sourceDocument: string;
}
export interface Series {
  metric: string;
  unit: string;
  points: { ts: string; avg: number; min: number; max: number }[];
}
export interface CrewMember {
  id: string;
  name: string;
  role: string;
  portrait: number;
  bloodPressure?: {
    systolic: number;
    diastolic: number;
    unit: string;
    origin: Origin;
    evidenceState: Evidence;
  };
  /** `null` when no wearable data exists: the state is unknown, not normal. */
  state: Severity | null;
  vitals: Vital[];
}
/** Session is supplied by a trusted backend, not a user picker or URL parameter. */
export interface Session {
  crewMember: CrewMember;
  zoneId: string;
  tasks: Task[];
  incidents: Incident[];
  sharedTasks: boolean;
  baselines?: { metric: string; value: number; recordedAt: string }[];
}
export interface Snapshot {
  dashboard: Dashboard | null;
  ship: Ship | null;
  alerts: Alert[];
  incidents: Incident[];
  incidentTypes: IncidentType[];
  tasks: Task[];
  ground: Ground | null;
  groundPlan: GroundPlan | null;
  rules: Rule[];
  crew: CrewMember[];
  session: Session | null;
  streak: number | null;
}
export type Resource =
  "overview" | "ship" | "tasks" | "ground" | "session" | "rules";
export type ResourceState = "idle" | "loading" | "ready" | "error";
export type Mode = "demo" | "backend";
export type Command =
  | { type: "acknowledgeAlert"; id: string }
  | {
      type: "reportIncident";
      zoneId: string;
      typeKey: string;
      description: string;
      severity?: Severity;
    }
  | { type: "acknowledgeIncident"; id: string }
  | { type: "resolveIncident"; id: string; note: string }
  | { type: "completeTask"; id: string; effective: boolean | null }
  | { type: "snoozeTask"; id: string; minutes: number }
  | { type: "blockTask"; id: string; reason: string }
  | {
      type: "createTask";
      kind: "HEALTH" | "SHIP";
      title: string;
      zoneId: string | null;
      dueAt: string | null;
    }
  | {
      type: "updateTask";
      id: string;
      title: string;
      zoneId: string | null;
      dueAt: string | null;
    }
  | { type: "deleteTask"; id: string }
  | {
      type: "saveGroundTemplate";
      title: string;
      kind: "HEALTH" | "SHIP";
      zoneCode: string | null;
      recurrence: "DAILY" | "ONCE";
      templateId?: string;
    }
  | { type: "cancelGroundTemplate"; templateId: string }
  | { type: "publishGroundPlan" }
  | { type: "setGroundLink"; online: boolean; delaySeconds: number }
  | { type: "setConsent"; category: "tasks"; shared: boolean }
  | { type: "recordBaseline"; metric: string; value: number }
  | { type: "syncGroundLinkNow" }
  | {
      type: "scenario";
      key: string;
      action: "start" | "stop";
      zone: string;
      speed: number;
    };
export interface Gateway {
  read: (
    resource: Resource,
    signal?: AbortSignal,
  ) => Promise<Partial<Snapshot>>;
  execute: (command: Command) => Promise<void>;
  series: (
    zoneId: string,
    from: string,
    to: string,
    signal?: AbortSignal,
  ) => Promise<Series[]>;
  subscribe: (
    invalidate: () => void,
    status: (state: string) => void,
  ) => () => void;
  dispose: () => void;
}
export const emptySnapshot: Snapshot = {
  dashboard: null,
  ship: null,
  alerts: [],
  incidents: [],
  incidentTypes: [],
  tasks: [],
  ground: null,
  groundPlan: null,
  rules: [],
  crew: [],
  session: null,
  streak: null,
};
export const severityLabels: Record<Severity, string> = {
  NORMAL: "Nominal",
  ATTENTION: "Attention",
  ALERT: "High",
  CRITICAL: "Critical",
};
export const evidenceLabels: Record<Evidence, string> = {
  VERIFIED: "Verified",
  TB: "Technical brief",
  DEMO: "Demo",
  UNVERIFIED: "Unverified",
};
export const statusLabels: Record<string, string> = {
  RAISED: "Open",
  ACKNOWLEDGED: "Acknowledged",
  RESOLVED: "Resolved",
  OPEN: "Open",
  PENDING: "Pending",
  COMPLETED: "Completed",
  BLOCKED: "Blocked",
  APPLIED: "Applied",
  HEALTH: "Health",
  SHIP: "Habitat",
  INCIDENT: "Incident",
  GROUND: "Ground",
  SYSTEM: "System",
  CREW: "Crew",
  MANUAL: "Manual",
  ALERT: "Alert",
  DRAFT: "Draft",
  QUEUED: "Queued",
  IN_TRANSIT: "In transit",
  RECEIVED: "Received",
  CONFIRMED: "Confirmed",
  REJECTED: "Rejected",
};
export const label = (value: string) => statusLabels[value] ?? value;
export const time = (value: string | null) =>
  value
    ? new Intl.DateTimeFormat("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "UTC",
      }).format(new Date(value)) + " UTC"
    : "Not scheduled";
export const metricLabels: Record<string, string> = {
  pressure_kpa: "Pressure",
  o2_pct: "Oxygen",
  co2_mmhg: "Carbon dioxide",
  temperature_c: "Temperature",
  humidity_pct: "Humidity",
  pio2: "Inspired oxygen",
  heart_rate: "Heart rate",
  spo2: "Oxygen saturation",
  body_temperature: "Body temperature",
  radiation: "Radiation exposure",
  blood_pressure: "Blood pressure",
};
