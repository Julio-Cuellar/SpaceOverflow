import { describe, it, expect, vi, afterEach } from "vitest";
import { backendGateway, connectRealtime, restJson } from "./backend";
const config = {
  graphqlUrl: "http://localhost/graphql",
  wsUrl: "ws://localhost/ws",
  apiBase: "",
  habitatId: "nave-transito",
};
const json = (body: unknown) =>
  new Response(JSON.stringify(body), {
    headers: { "content-type": "application/json" },
  });
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});
describe("Backend integration", () => {
  it("never requests personal data without a configured trusted session route", async () => {
    const fetchImpl = vi.fn();
    const g = backendGateway({ ...config, fetchImpl });
    await expect(g.read("session")).rejects.toThrow(
      "Personal sessions are not available",
    );
    expect(fetchImpl).not.toHaveBeenCalled();
  });
  it("loads all incident pages using server cursors", async () => {
    const fetchImpl = vi.fn(async (_url: unknown, init?: RequestInit) => {
      const body = JSON.parse(String(init?.body));
      if (body.query.includes("IncidentCatalog"))
        return json({ data: { incidentTypes: [] } });
      if (body.query.includes("query Habitat"))
        return json({ data: { ship: { id: "real-uuid", zones: [] } } });
      return json({
        data: {
          incidents: {
            nodes: [{ id: body.variables.after ? "second" : "first" }],
            pageInfo: {
              hasNextPage: !body.variables.after,
              endCursor: body.variables.after ? "end" : "next-page",
            },
          },
        },
      });
    });
    const g = backendGateway({
      ...config,
      fetchImpl: fetchImpl as typeof fetch,
    });
    const data = await g.read("ship");
    expect(data.incidents?.map((i) => i.id)).toEqual(["first", "second"]);
    expect(fetchImpl).toHaveBeenCalledTimes(4);
  });
  it("surfaces typed errors in English and never assumes mutation success", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      json({
        data: {
          resolveIncident: {
            __typename: "IncidentError",
            code: "ACTIVE_ALERTS",
            message: "Hay alertas activas",
          },
        },
      }),
    );
    const g = backendGateway({ ...config, fetchImpl });
    await expect(
      g.execute({ type: "resolveIncident", id: "uuid", note: "Done" }),
    ).rejects.toThrow("Active zone alerts");
  });
  it("sends the backend zone code, not the mock zone id, to the simulator", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(json({ state: "started" }));
    const g = backendGateway({ ...config, fetchImpl });
    await g.execute({
      type: "scenario",
      key: "co2_slow",
      zone: "lab",
      speed: 2,
      action: "start",
    });
    const [, init] = fetchImpl.mock.calls[0];
    expect(JSON.parse(init.body)).toEqual({ zone: "lab", speed: 2 });
  });
  it("rejects HTML responses from an incorrect API proxy", async () => {
    await expect(
      restJson(
        "/api",
        {},
        vi.fn().mockResolvedValue(
          new Response("<html/>", {
            headers: { "content-type": "text/html" },
          }),
        ),
      ),
    ).rejects.toThrow("did not return JSON");
  });
  it("deduplicates event sequences and resumes after reconnect", async () => {
    vi.useFakeTimers();
    const sockets: FakeSocket[] = [];
    class FakeSocket {
      onopen: (() => void) | null = null;
      onclose: (() => void) | null = null;
      onerror: (() => void) | null = null;
      onmessage: ((event: { data: string }) => void) | null = null;
      send = vi.fn();
      close = vi.fn();
      constructor() {
        sockets.push(this);
      }
    }
    vi.stubGlobal("WebSocket", FakeSocket);
    const invalidate = vi.fn();
    const stop = connectRealtime(config.wsUrl, invalidate, vi.fn());
    sockets[0].onopen!();
    const message = JSON.stringify({
      seq: 7,
      type: "incident.updated",
      topic: "habitat",
      at: "now",
      data: {},
    });
    sockets[0].onmessage!({ data: message });
    sockets[0].onmessage!({ data: message });
    await vi.advanceTimersByTimeAsync(500);
    expect(invalidate).toHaveBeenCalledTimes(2);
    sockets[0].onclose!();
    await vi.advanceTimersByTimeAsync(1000);
    sockets[1].onopen!();
    expect(sockets[1].send).toHaveBeenCalledWith(
      JSON.stringify({ type: "resume", after_outbox_id: 7 }),
    );
    stop();
  });
});
