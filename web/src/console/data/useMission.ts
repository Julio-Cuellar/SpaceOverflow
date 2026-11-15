import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { backendGateway } from "./backend";
import { demoGateway } from "./demo";
import {
  emptySnapshot,
  type Command,
  type Gateway,
  type Mode,
  type Resource,
  type ResourceState,
  type Snapshot,
} from "../model";
interface Cache {
  owner: Gateway;
  scope: string;
  data: Snapshot;
  states: Partial<Record<Resource, ResourceState>>;
  errors: Partial<Record<Resource, string>>;
}
export function useMission(mode: Mode, personal: boolean, view: string) {
  const gateway = useMemo(
    () =>
      mode === "demo"
        ? demoGateway()
        : backendGateway({
            graphqlUrl: import.meta.env.VITE_GRAPHQL_URL || "/graphql",
            wsUrl:
              import.meta.env.VITE_WS_URL ||
              `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`,
            apiBase: import.meta.env.VITE_API_BASE || "",
            habitatId: import.meta.env.VITE_HABITAT_ID || "transit-ship",
            sessionUrl: import.meta.env.VITE_SESSION_URL,
            crewDirectoryUrl: import.meta.env.VITE_CREW_DIRECTORY_URL,
          }),
    [mode],
  );
  const resources = useMemo<Resource[]>(
    () =>
      personal
        ? ["session", "ship", "rules"]
        : view === "ground"
          ? ["ground", "ship"]
          : view === "tasks"
            ? ["tasks", "ship"]
            : view === "habitat"
              ? ["ship", "rules", "overview"]
              : ["overview", "ship"],
    [personal, view],
  );
  const scope = resources.join(",");
  const [cache, setCache] = useState<Cache>({
    owner: gateway,
    scope,
    data: emptySnapshot,
    states: Object.fromEntries(
      resources.map((r) => [r, "loading" as ResourceState]),
    ),
    errors: {},
  });
  // A source or role change never renders the previous source's data, even for one frame.
  const current =
    cache.owner === gateway && cache.scope === scope ? cache : null;
  const [stream, setStream] = useState({
    owner: gateway,
    state: mode === "demo" ? "Demo stream" : "Connecting",
  });
  const [pending, setPending] = useState(false);
  const [notice, setNotice] = useState("");
  const epoch = useRef(0);
  const refresh = useRef<() => void>(() => {});
  const mutation = useRef(false);
  useEffect(() => {
    let stopped = false;
    let active = false;
    let queued = false;
    const controller = new AbortController();
    const generation = ++epoch.current;
    const load = async () => {
      await Promise.resolve();
      if (stopped) return;
      if (active) {
        queued = true;
        return;
      }
      active = true;
      const results = await Promise.allSettled(
        resources.map((r) => gateway.read(r, controller.signal)),
      );
      if (stopped || generation !== epoch.current) return;
      setCache((previous) => {
        const next: Cache =
          previous.owner === gateway && previous.scope === scope
            ? {
                ...previous,
                data: { ...previous.data },
                states: { ...previous.states },
                errors: { ...previous.errors },
              }
            : {
                owner: gateway,
                scope,
                data: { ...emptySnapshot },
                states: {},
                errors: {},
              };
        results.forEach((result, i) => {
          const r = resources[i];
          if (result.status === "fulfilled") {
            next.data = { ...next.data, ...result.value };
            next.states[r] = "ready";
            delete next.errors[r];
          } else {
            next.states[r] = "error";
            next.errors[r] =
              result.reason instanceof Error
                ? result.reason.message
                : "The data could not be loaded.";
          }
        });
        return next;
      });
      active = false;
      if (queued) {
        queued = false;
        void load();
      }
    };
    refresh.current = () => void load();
    void load();
    const unsubscribe = gateway.subscribe(
      () => void load(),
      (state) => setStream({ owner: gateway, state }),
    );
    const interval = setInterval(() => void load(), 10000);
    return () => {
      stopped = true;
      controller.abort();
      unsubscribe();
      clearInterval(interval);
    };
  }, [gateway, resources, scope]);
  useEffect(() => () => gateway.dispose(), [gateway]);
  const run = useCallback(
    async (command: Command): Promise<boolean> => {
      if (mutation.current) return false;
      mutation.current = true;
      const generation = epoch.current;
      setPending(true);
      setNotice("");
      try {
        await gateway.execute(command);
        if (generation === epoch.current) {
          refresh.current();
          setNotice(
            mode === "demo"
              ? "Demo change saved for this session."
              : "Change confirmed by the backend.",
          );
        }
        return true;
      } catch (error) {
        if (generation === epoch.current)
          setNotice(
            error instanceof Error
              ? error.message
              : "The change could not be saved.",
          );
        return false;
      } finally {
        mutation.current = false;
        setPending(false);
      }
    },
    [gateway, mode],
  );
  return {
    data: current?.data ?? emptySnapshot,
    states:
      current?.states ??
      Object.fromEntries(resources.map((r) => [r, "loading" as ResourceState])),
    errors: current?.errors ?? {},
    connection: stream.owner === gateway ? stream.state : "Connecting",
    pending,
    notice,
    run,
    reload: () => refresh.current(),
    gateway,
  };
}
export type Mission = ReturnType<typeof useMission>;
