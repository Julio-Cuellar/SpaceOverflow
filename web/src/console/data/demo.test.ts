import { describe, it, expect, vi, afterEach } from "vitest";
import { demoGateway } from "./demo";
afterEach(() => vi.useRealTimers());
describe("Demo adapter behavioral contracts", () => {
  it("enforces task ownership and records completion and effectiveness", async () => {
    const g = demoGateway();
    await expect(
      g.execute({ type: "deleteTask", id: "demo-task-2" }),
    ).rejects.toThrow("Only crew-created");
    await g.execute({
      type: "completeTask",
      id: "demo-task-1",
      effective: true,
    });
    const s = await g.read("session");
    expect(
      s.session?.tasks.find((t) => t.id === "demo-task-1")?.effective,
    ).toBe(true);
    expect(s.streak).toBe(2);
    g.dispose();
  });
  it("keeps a published plan queued offline, then applies it once without erasing completed work", async () => {
    vi.useFakeTimers();
    const g = demoGateway();
    await g.execute({ type: "setGroundLink", online: false, delaySeconds: 1 });
    await g.execute({
      type: "saveGroundTemplate",
      title: "New health routine",
      kind: "HEALTH",
      zoneCode: null,
      recurrence: "DAILY",
    });
    await g.execute({ type: "publishGroundPlan" });
    await expect(g.execute({ type: "publishGroundPlan" })).rejects.toThrow(
      "already in flight",
    );
    await vi.advanceTimersByTimeAsync(10000);
    expect((await g.read("ground")).ground?.published?.stage).toBe("QUEUED");
    await g.execute({ type: "setGroundLink", online: true, delaySeconds: 1 });
    await vi.advanceTimersByTimeAsync(5000);
    const s = await g.read("ground");
    expect(s.ground?.published?.stage).toBe("CONFIRMED");
    expect(s.tasks?.find((t) => t.id === "demo-task-4")?.status).toBe(
      "COMPLETED",
    );
    expect(
      s.tasks?.filter((t) => t.title === "New health routine"),
    ).toHaveLength(1);
    g.dispose();
  });
  it("does not allow automatic incidents to close until alerts normalize", async () => {
    const g = demoGateway();
    await expect(
      g.execute({
        type: "resolveIncident",
        id: "demo-incident-1",
        note: "Reviewed",
      }),
    ).rejects.toThrow("Active alerts");
    await g.execute({
      type: "scenario",
      key: "co2_slow",
      action: "stop",
      zone: "lab",
      speed: 1,
    });
    await g.execute({
      type: "resolveIncident",
      id: "demo-incident-1",
      note: "Reviewed after normalization",
    });
    expect((await g.read("ship")).incidents?.[0].status).toBe("RESOLVED");
    g.dispose();
  });
  it("validates blocker reasons and snooze ranges", async () => {
    const g = demoGateway();
    await expect(
      g.execute({ type: "blockTask", id: "demo-task-1", reason: " " }),
    ).rejects.toThrow("required");
    await expect(
      g.execute({ type: "snoozeTask", id: "demo-task-1", minutes: 0 }),
    ).rejects.toThrow("between");
    g.dispose();
  });
});
