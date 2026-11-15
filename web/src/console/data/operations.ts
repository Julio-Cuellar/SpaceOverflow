// Validated against Dev A's exported schema (`contracts/schema.generated.graphql`) by contracts.test.ts.
// `pendingMutations` are not in Dev A's schema yet: they are validated against the integration target.
export const DASHBOARD =
  "query MissionDashboard($habitatId: ID!) { dashboard(habitatId: $habitatId) { habitatId globalSeverity vitals { key label value unit severity evidenceState origin zoneId } } }";
export const ALERTS =
  "query ActiveAlerts($first: Int!, $after: String) { alerts(first: $first, after: $after) { nodes { id ruleKey zoneId severity status causeHint raisedAt rule { sourceRequirement sourceDocument evidenceState parameter } recommendation { body sourceKind actions { key title description } citations { documentCode requirementRef excerpt evidenceState } } } pageInfo { hasNextPage endCursor } } }";
export const SHIP =
  "query Habitat($habitatId: ID!) { ship(habitatId: $habitatId) { habitatId code name kind canvas zones { id code name kind deck layout { x y w h } status openIncidents } } }";
export const INCIDENTS =
  "query Incidents($first: Int!, $after: String) { incidents(first: $first, after: $after) { nodes { id code title description severity status source zoneId openedAt valuesNormal sourceAlertId updates { kind note at } } pageInfo { hasNextPage endCursor } } }";
export const TYPES =
  "query IncidentCatalog { incidentTypes { key name category categoryName detection defaultSeverity evidenceState typicalZones suggestedActions } }";
export const TASKS =
  "query DailyTasks($day: Date!) { tasks(day: $day) { id kind origin title zoneId status dueAt blockedReason effective sourceAlertId incidentId templateId } streak(day: $day) groundPlan { version appliedAt rejected { title reason } } }";
export const GROUND =
  "query GroundControl { groundControl { appliedVersion templates { id title kind status blockedReason cancelled } draft { version templates { id title kind status blockedReason cancelled } } published { version stage reason publishedAt ackedAt } link { online delaySeconds changedAt } } }";
export const SERIES =
  "query ZoneHistory($zoneId: ID!, $metrics: [String!]!, $from: DateTime!, $to: DateTime!) { zoneReadings(zoneId: $zoneId, metrics: $metrics, from: $from, to: $to, resolution: MINUTE) { metric unit points { ts avg min max } } }";
export const mutations = {
  acknowledgeAlert:
    "mutation AcknowledgeAlert($id: ID!) { acknowledgeAlert(id:$id) { __typename ... on AlertError { code message } } }",
  reportIncident:
    "mutation ReportIncident($zoneId: ID!, $typeKey: String!, $description: String!, $severity: Severity) { reportIncident(zoneId:$zoneId,typeKey:$typeKey,description:$description,severity:$severity) { __typename ... on IncidentError { code message } } }",
  acknowledgeIncident:
    "mutation AcknowledgeIncident($id: ID!) { acknowledgeIncident(id:$id) { __typename ... on IncidentError { code message } } }",
  resolveIncident:
    "mutation ResolveIncident($id: ID!, $note: String!) { resolveIncident(id:$id,note:$note) { __typename ... on IncidentError { code message } } }",
  completeTask:
    "mutation CompleteTask($id: ID!, $effective: Boolean) { completeTask(id:$id,effective:$effective) { __typename ... on TaskError { code message } } }",
  snoozeTask:
    "mutation SnoozeTask($id: ID!, $minutes: Int!) { snoozeTask(id:$id,minutes:$minutes) { __typename ... on TaskError { code message } } }",
  blockTask:
    "mutation BlockTask($id: ID!, $reason: String!) { blockTask(id:$id,reason:$reason) { __typename ... on TaskError { code message } } }",
  createTask:
    "mutation CreateTask($kind: TaskKind!, $title: String!, $zoneId: ID, $dueAt: DateTime) { createTask(kind:$kind,title:$title,zoneId:$zoneId,dueAt:$dueAt) { __typename ... on TaskError { code message } } }",
  updateTask:
    "mutation UpdateTask($id: ID!, $title: String!, $zoneId: ID, $dueAt: DateTime) { updateTask(id:$id,title:$title,zoneId:$zoneId,dueAt:$dueAt) { __typename ... on TaskError { code message } } }",
  deleteTask:
    "mutation DeleteTask($id: ID!) { deleteTask(id:$id) { __typename ... on TaskError { code message } } }",
  saveGroundTemplate:
    "mutation SaveGroundTemplate($title: String!, $kind: TaskKind!, $zoneCode: String, $recurrence: String!, $templateId: ID) { saveGroundTemplate(title:$title,kind:$kind,zoneCode:$zoneCode,recurrence:$recurrence,templateId:$templateId) { __typename ... on GroundError { code message } } }",
  cancelGroundTemplate:
    "mutation CancelGroundTemplate($templateId: ID!) { cancelGroundTemplate(templateId:$templateId) { __typename ... on GroundError { code message } } }",
  publishGroundPlan:
    "mutation PublishGroundPlan { publishGroundPlan { __typename ... on GroundError { code message } } }",
  setGroundLink:
    "mutation SetGroundLink($online: Boolean!, $delaySeconds: Float!) { setGroundLink(online:$online,delaySeconds:$delaySeconds) { __typename } }",
} as const;
// Not in Dev A's backend yet (crew session and Ground link sync). The demo gateway simulates them;
// the real backend refuses them with an explicit message instead of calling a missing field.
export const pendingMutations = {
  setConsent:
    "mutation SetConsent($category: String!, $shared: Boolean!) { setConsent(category:$category,shared:$shared) { __typename ... on CrewError { code message } } }",
  recordBaseline:
    "mutation RecordBaseline($metric: String!, $value: Float!) { recordBaseline(metric:$metric,value:$value) { __typename ... on CrewError { code message } } }",
  syncGroundLinkNow:
    "mutation SyncGroundLinkNow { syncGroundLinkNow { __typename } }",
} as const;
export const queryDocuments = [
  DASHBOARD,
  ALERTS,
  SHIP,
  INCIDENTS,
  TYPES,
  TASKS,
  GROUND,
  SERIES,
];
