import { createClient, fetchExchange } from "urql";
import type {
  Command,
  Gateway,
  Resource,
  Snapshot,
  Series,
  Rule,
  Session,
} from "../model";
import * as op from "./operations";
import { createStream } from "../../data/ws/stream";
import type { WsMessage } from "../../data/ws/types";
export class ServiceError extends Error {
  constructor(
    public code: string,
    message: string,
  ) {
    super(message);
  }
}
const messages: Record<string, string> = {
  NOT_FOUND: "The requested item was not found.",
  ALREADY_RESOLVED: "This item has already been resolved.",
  ACTIVE_ALERTS: "Active zone alerts prevent incident resolution.",
  NOT_EDITABLE: "Only crew-created tasks can be edited.",
  NOT_DELETABLE: "Only crew-created tasks can be deleted.",
  TITLE_REQUIRED: "Enter a title.",
  INVALID_KIND: "Choose a supported task category.",
  NOTHING_TO_PUBLISH: "There are no draft changes to publish.",
  PLAN_IN_FLIGHT: "Wait for the current plan to be confirmed.",
  UNKNOWN_ZONE: "The selected zone is no longer available.",
  UNKNOWN_TYPE: "The selected incident type is no longer available.",
  INVALID_SEVERITY: "Choose a severity other than Nominal.",
  UNAUTHENTICATED: "Sign in to access your personal workspace.",
  FORBIDDEN: "You do not have permission to access this item.",
};
export const errorMessage = (code: string) =>
  messages[code] ??
  "The request could not be completed. Refresh and try again.";
export interface BackendConfig {
  graphqlUrl: string;
  wsUrl: string;
  apiBase: string;
  habitatId: string;
  sessionUrl?: string;
  crewDirectoryUrl?: string;
  fetchImpl?: typeof fetch;
}
export async function restJson<T>(
  url: string,
  options: RequestInit = {},
  fetchImpl: typeof fetch = fetch,
  timeoutMs = 15000,
): Promise<T> {
  const response = await fetchImpl(url, {
    ...options,
    credentials: "same-origin",
    signal: options.signal
      ? AbortSignal.any([options.signal, AbortSignal.timeout(timeoutMs)])
      : AbortSignal.timeout(timeoutMs),
  });
  if (!response.ok)
    throw new ServiceError(
      String(response.status),
      response.status === 401
        ? "Sign in to continue."
        : response.status === 403
          ? "Access denied."
          : `Service unavailable (HTTP ${response.status}).`,
    );
  const content = response.headers.get("content-type");
  if (!content?.includes("application/json"))
    throw new ServiceError(
      "INVALID_RESPONSE",
      "The server did not return JSON. Check the API route.",
    );
  return response.json() as Promise<T>;
}
export function backendGateway(config: BackendConfig): Gateway {
  const fetchImpl = config.fetchImpl ?? fetch;
  const client = createClient({
    url: config.graphqlUrl,
    exchanges: [fetchExchange],
    preferGetMethod: false,
    fetch: fetchImpl,
    requestPolicy: "network-only",
    fetchOptions: { credentials: "same-origin" },
  });
  const query = async <T>(
    document: string,
    variables: Record<string, unknown> = {},
    signal?: AbortSignal,
  ): Promise<T> => {
    const result = await client
      .query<T>(document, variables, {
        fetchOptions: {
          credentials: "same-origin",
          signal: signal
            ? AbortSignal.any([signal, AbortSignal.timeout(15000)])
            : AbortSignal.timeout(15000),
        },
      })
      .toPromise();
    if (result.error || !result.data)
      throw new ServiceError(
        "GRAPHQL",
        "Mission data is unavailable. Verify that Dev A’s GraphQL service is running and the contract matches.",
      );
    return result.data;
  };
  const page = async <T>(
    document: string,
    key: string,
    signal?: AbortSignal,
  ): Promise<T[]> => {
    let after: string | null = null;
    const items: T[] = [];
    const seen = new Set<string>();
    for (let n = 0; n < 200; n++) {
      const result: Record<
        string,
        {
          nodes: T[];
          pageInfo: { hasNextPage: boolean; endCursor: string | null };
        }
      > = await query<
        Record<
          string,
          {
            nodes: T[];
            pageInfo: { hasNextPage: boolean; endCursor: string | null };
          }
        >
      >(document, { first: 100, after }, signal);
      const connection: {
        nodes: T[];
        pageInfo: { hasNextPage: boolean; endCursor: string | null };
      } = result[key];
      if (
        !connection ||
        !Array.isArray(connection.nodes) ||
        !connection.pageInfo
      )
        throw new ServiceError(
          "INVALID_RESPONSE",
          "The server returned an invalid paginated response.",
        );
      items.push(...connection.nodes);
      if (!connection.pageInfo.hasNextPage) return items;
      after = connection.pageInfo.endCursor;
      if (!after || seen.has(after))
        throw new ServiceError(
          "CURSOR",
          "The server returned an invalid pagination cursor.",
        );
      seen.add(after);
    }
    throw new ServiceError(
      "LIMIT",
      "There are too many results. Narrow the server query.",
    );
  };
  const read = async (
    resource: Resource,
    signal?: AbortSignal,
  ): Promise<Partial<Snapshot>> => {
    switch (resource) {
      case "overview": {
        const [dashboard, alerts, directory] = await Promise.all([
          query<Pick<Snapshot, "dashboard">>(
            op.DASHBOARD,
            { habitatId: config.habitatId },
            signal,
          ),
          page<Snapshot["alerts"][number]>(op.ALERTS, "alerts", signal),
          config.crewDirectoryUrl
            ? restJson<{ crew: Snapshot["crew"] }>(
                config.crewDirectoryUrl,
                { signal },
                fetchImpl,
              )
            : Promise.resolve({ crew: [] as Snapshot["crew"] }),
        ]);
        return {
          ...dashboard,
          crew: directory.crew,
          alerts: alerts.filter((a) => a.status !== "RESOLVED"),
        };
      }
      case "ship": {
        const [ship, incidents, types] = await Promise.all([
          query<Pick<Snapshot, "ship">>(
            op.SHIP,
            { habitatId: config.habitatId },
            signal,
          ),
          page<Snapshot["incidents"][number]>(
            op.INCIDENTS,
            "incidents",
            signal,
          ),
          query<Pick<Snapshot, "incidentTypes">>(op.TYPES, {}, signal),
        ]);
        return { ...ship, ...types, incidents };
      }
      case "tasks":
        return query<Pick<Snapshot, "tasks" | "groundPlan" | "streak">>(
          op.TASKS,
          { day: new Date().toISOString().slice(0, 10) },
          signal,
        );
      case "ground": {
        const result = await query<{ groundControl: Snapshot["ground"] }>(
          op.GROUND,
          {},
          signal,
        );
        return { ground: result.groundControl };
      }
      case "session": {
        if (!config.sessionUrl)
          throw new ServiceError(
            "SESSION_PENDING",
            "Personal sessions are not available in this backend yet. No other crew member’s data is displayed.",
          );
        const session = await restJson<Session>(
          config.sessionUrl,
          { signal },
          fetchImpl,
        );
        if (
          !session.crewMember?.id ||
          !Array.isArray(session.tasks) ||
          !Array.isArray(session.incidents)
        )
          throw new ServiceError(
            "SESSION_INVALID",
            "The session response does not match the personal workspace contract.",
          );
        return { session };
      }
      case "rules": {
        const catalog = await restJson<{ rules: Record<string, unknown>[] }>(
          `${config.apiBase}/api/v1/rules/catalog.json`,
          { signal },
          fetchImpl,
        );
        const rules = catalog.rules.map(
          (r) =>
            ({
              key: r.key,
              parameter: r.parameter,
              kind: r.kind,
              operator: r.operator,
              threshold: r.threshold,
              unit: r.unit,
              windowS: r.window_s,
              severity: String(r.severity).toUpperCase(),
              evidenceState: r.evidence_state,
              sourceRequirement: r.source_requirement,
              sourceDocument: r.source_document,
            }) as Rule,
        );
        return { rules };
      }
    }
  };
  const execute = async (command: Command) => {
    const { type, ...variables } = command;
    if (type === "scenario") {
      await restJson(
        `${config.apiBase}/api/v1/sim/scenarios/${encodeURIComponent(command.key)}:${command.action}`,
        {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ zone: command.zone, speed: command.speed }),
        },
        fetchImpl,
      );
      return;
    }
    const result = await client
      .mutation<
        Record<string, { __typename: string; code?: string; message?: string }>
      >(op.mutations[type], variables, {
        fetchOptions: {
          credentials: "same-origin",
          signal: AbortSignal.timeout(15000),
        },
      })
      .toPromise();
    if (result.error || !result.data)
      throw new ServiceError(
        "GRAPHQL",
        "The change was not confirmed. Refresh before retrying.",
      );
    const payload = result.data[type];
    if (!payload?.__typename)
      throw new ServiceError(
        "INVALID_RESPONSE",
        "The server did not confirm the operation.",
      );
    if (payload.code || payload.__typename.endsWith("Error"))
      throw new ServiceError(
        payload.code ?? "UNKNOWN",
        errorMessage(payload.code ?? "UNKNOWN"),
      );
  };
  return {
    read,
    execute,
    series: async (zoneId, from, to, signal) => {
      const result = await query<{ zoneReadings: Series[] }>(
        op.SERIES,
        {
          zoneId,
          metrics: [
            "pressure_kpa",
            "o2_pct",
            "co2_mmhg",
            "temperature_c",
            "humidity_pct",
          ],
          from,
          to,
        },
        signal,
      );
      return result.zoneReadings;
    },
    subscribe: (invalidate, status) =>
      connectRealtime(config.wsUrl, invalidate, status),
    dispose: () => {},
  };
}
/** Event-driven invalidation: measurements are refreshed from GraphQL, never inferred from raw ticks. */
export function connectRealtime(
  url: string,
  invalidate: () => void,
  status: (text: string) => void,
): () => void {
  let socket: WebSocket | undefined;
  let stopped = false;
  let retry = 0;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let flush: ReturnType<typeof setTimeout> | undefined;
  const stream = createStream();
  const connect = () => {
    if (stopped) return;
    status("Connecting");
    socket = new WebSocket(url);
    socket.onopen = () => {
      retry = 0;
      status("Connected");
      socket!.send(
        JSON.stringify({ type: "resume", after_outbox_id: stream.lastSeq() }),
      );
      invalidate();
    };
    socket.onmessage = (event) => {
      let message: WsMessage;
      try {
        message = JSON.parse(String(event.data)) as WsMessage;
      } catch {
        return;
      }
      if (
        !message ||
        typeof message.type !== "string" ||
        typeof message.topic !== "string" ||
        !message.data ||
        typeof message.data !== "object" ||
        (message.seq !== null && !Number.isSafeInteger(message.seq))
      )
        return;
      if (message.topic === "system") return;
      if (!stream.push(message)) return;
      if (!flush)
        flush = setTimeout(() => {
          stream.drain();
          flush = undefined;
          invalidate();
        }, 500);
    };
    socket.onerror = () => socket?.close();
    socket.onclose = () => {
      if (stopped) return;
      status("Reconnecting");
      timer = setTimeout(
        connect,
        Math.min(30000, 1000 * 2 ** Math.min(retry++, 5)),
      );
    };
  };
  connect();
  return () => {
    stopped = true;
    clearTimeout(timer);
    clearTimeout(flush);
    socket?.close();
  };
}
