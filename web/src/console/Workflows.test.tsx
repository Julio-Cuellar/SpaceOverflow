import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeAll, describe, it, expect, vi } from "vitest";
import { ConsoleApp } from "./ConsoleApp";
import { GroundPage } from "./pages/Ground";
import { ZoneTrends, Trend } from "./ui/Charts";
import { seed } from "./data/fixtures";
import { demoGateway } from "./data/demo";
import type { Mission } from "./data/useMission";
import type { Snapshot } from "./model";
beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
  window.scrollTo = vi.fn();
});
afterEach(() => vi.unstubAllGlobals());
const mockMission = (
  data: Snapshot,
  overrides: Partial<Mission> = {},
): Mission => ({
  data,
  states: {},
  errors: {},
  connection: "Demo stream",
  pending: false,
  notice: "",
  run: vi.fn().mockResolvedValue(true),
  reload: vi.fn(),
  gateway: demoGateway(),
  ...overrides,
});
describe("Mission workflow acceptance", () => {
  it("creates, edits and deletes a crew-owned task with a scheduled time and zone", async () => {
    const user = userEvent.setup();
    render(<ConsoleApp initialPath="/tasks" />);
    await screen.findByRole("button", { name: "Mobility and stretching" });
    await user.click(screen.getByRole("button", { name: "＋ Create task" }));
    await user.type(screen.getByLabelText("Title"), "Inspect desk");
    await user.selectOptions(
      screen.getByLabelText("Category", { selector: "select[name=kind]" }),
      "SHIP",
    );
    await user.selectOptions(screen.getByLabelText("Zone"), "demo-lab");
    await user.type(
      screen.getByLabelText("Scheduled time (UTC)"),
      "2026-11-15T18:00",
    );
    await user.click(screen.getByRole("button", { name: "Save task" }));
    await user.click(
      await screen.findByRole("button", { name: "Inspect desk" }),
    );
    await user.click(screen.getByRole("button", { name: "Edit own task" }));
    await user.clear(screen.getByLabelText("Title"));
    await user.type(screen.getByLabelText("Title"), "Inspect new desk");
    await user.click(screen.getByRole("button", { name: "Save task" }));
    await user.click(
      await screen.findByRole("button", { name: "Inspect new desk" }),
    );
    await user.click(screen.getByRole("button", { name: "Delete own task" }));
    await user.click(screen.getByRole("button", { name: "Keep task" }));
    await user.click(screen.getByRole("button", { name: "Delete own task" }));
    await user.click(screen.getByRole("button", { name: "Confirm delete" }));
    await waitFor(() =>
      expect(
        screen.queryByRole("button", { name: "Inspect new desk" }),
      ).not.toBeInTheDocument(),
    );
  });
  it("snoozes and blocks a ground task without allowing edits", async () => {
    const user = userEvent.setup();
    render(<ConsoleApp initialPath="/tasks" />);
    await user.click(
      await screen.findByRole("button", {
        name: "Inspect habitat air filters",
      }),
    );
    await user.click(screen.getByRole("button", { name: "Snooze 15 min" }));
    await user.type(
      screen.getByLabelText("Unable to complete? Give a reason"),
      "Awaiting replacement filter",
    );
    await user.click(screen.getByRole("button", { name: "Report blocker" }));
    expect(
      await screen.findByText("Blocked: Awaiting replacement filter"),
    ).toBeVisible();
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Category" }),
      "INCIDENT",
    );
    expect(screen.getByText("No activities in this filter.")).toBeVisible();
  });
  it("selects zones, acknowledges an incident and respects the active-alert resolution guard", async () => {
    const user = userEvent.setup();
    render(<ConsoleApp initialPath="/habitat" />);
    await user.click(
      await screen.findByRole("button", { name: /^Laboratory,/ }),
    );
    await user.click(
      await screen.findByRole("button", { name: "Elevated CO₂ trend" }),
    );
    await user.click(screen.getByRole("button", { name: "Acknowledge" }));
    await user.type(screen.getByLabelText("Resolution note"), "Reviewed");
    await user.click(screen.getByRole("button", { name: "Resolve incident" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Active alerts prevent resolution",
    );
    await user.click(screen.getByRole("button", { name: /Close INC-0008/ }));
    await user.click(screen.getByRole("button", { name: "Stop scenario" }));
    await user.click(
      await screen.findByRole("button", { name: "Elevated CO₂ trend" }),
    );
    await user.type(
      screen.getByLabelText("Resolution note"),
      "Normalized and reviewed",
    );
    await user.click(screen.getByRole("button", { name: "Resolve incident" }));
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: "Resolved" }));
    expect(
      await screen.findByRole("button", { name: "Elevated CO₂ trend" }),
    ).toBeVisible();
  });
  it("reports a manual incident and starts a different simulator scenario without losing it", async () => {
    const user = userEvent.setup();
    render(<ConsoleApp initialPath="/habitat" />);
    await user.click(
      await screen.findByRole("button", { name: "＋ Report incident" }),
    );
    await user.type(screen.getByLabelText("Observation"), "Latch damaged");
    await user.click(screen.getByRole("button", { name: "Submit report" }));
    expect(
      await screen.findByRole("button", { name: "Equipment malfunction" }),
    ).toBeVisible();
    await user.selectOptions(screen.getByLabelText("Scenario"), "heat");
    await user.clear(screen.getByLabelText("Speed"));
    await user.type(screen.getByLabelText("Speed"), "2");
    await user.click(screen.getByRole("button", { name: "Start scenario" }));
    expect(
      await screen.findByRole("button", { name: "Simulated high temperature" }),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Equipment malfunction" }),
    ).toBeVisible();
    await user.selectOptions(screen.getByLabelText("Window"), "6");
  });
  it("edits and cancels ground drafts, publishes a queued plan and restores the link", async () => {
    const user = userEvent.setup();
    render(<ConsoleApp initialPath="/ground" />);
    await user.click(
      await screen.findByRole("button", { name: "＋ Add template" }),
    );
    await user.type(screen.getByLabelText("Title"), "Personal mobility");
    await user.selectOptions(screen.getByLabelText("Category"), "HEALTH");
    await user.selectOptions(screen.getByLabelText("Zone"), "lab");
    await user.selectOptions(screen.getByLabelText("Recurrence"), "ONCE");
    await user.click(
      screen.getByRole("button", { name: "Save draft template" }),
    );
    const item = (
      await screen.findByRole("heading", { name: "Personal mobility" })
    ).closest("article")!;
    await user.click(within(item).getByRole("button", { name: "Edit" }));
    await user.clear(screen.getByLabelText("Title"));
    await user.type(screen.getByLabelText("Title"), "Updated mobility");
    await user.click(
      screen.getByRole("button", { name: "Save draft template" }),
    );
    await user.click(screen.getByRole("button", { name: "Cut link" }));
    await user.click(screen.getByRole("button", { name: "Publish plan v4" }));
    expect(
      await screen.findByText("Queued", { selector: "li" }),
    ).toHaveAttribute("aria-current", "step");
    await user.click(screen.getByRole("button", { name: "Restore link" }));
    await user.clear(screen.getByLabelText("Delivery delay (seconds)"));
    await user.type(screen.getByLabelText("Delivery delay (seconds)"), "1");
    await user.click(screen.getByRole("button", { name: "Apply delay" }));
    await user.click(screen.getByRole("button", { name: "Sync now" }));
  });
  it("opens settings, saves a local baseline and changes demo task consent", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ status: "ok", profile: "jury" }), {
          headers: { "content-type": "application/json" },
        }),
      ),
    );
    const user = userEvent.setup();
    render(<ConsoleApp initialPath="/settings" />);
    expect(
      await screen.findByText("Backend: ok · profile jury"),
    ).toBeVisible();
    await user.type(screen.getByLabelText("Resting heart rate (bpm)"), "65");
    await user.click(screen.getByRole("button", { name: "Record baseline" }));
    expect(await screen.findByText("Recorded baseline: 65 bpm")).toBeVisible();
    await user.click(
      screen.getByRole("checkbox", {
        name: "Share my task status with Ground",
      }),
    );
    await waitFor(() =>
      expect(
        screen.getByRole("checkbox", {
          name: "Share my task status with Ground",
        }),
      ).not.toBeChecked(),
    );
  });
  it("shows cited assistant replies, degraded mode and playback, and keeps errors visible", async () => {
    const user = userEvent.setup();
    const ask = vi
      .fn()
      .mockResolvedValueOnce({
        outcome: "ANSWERED",
        text: "A sourced response.",
        degraded: true,
        citations: [
          {
            documentCode: "DEMO-DOC",
            requirementRef: "Example",
            excerpt: "Demo source passage.",
            evidenceState: "DEMO",
          },
        ],
      })
      .mockRejectedValueOnce(Error("Assistant is unavailable"));
    const speak = vi.fn().mockResolvedValue(undefined);
    render(
      <ConsoleApp initialPath="/assistant" askAssistant={ask} speak={speak} />,
    );
    await user.click(
      screen.getByRole("button", { name: "What does high CO₂ mean?" }),
    );
    await user.click(screen.getByRole("button", { name: "Send ↑" }));
    expect(await screen.findByText("A sourced response.")).toBeVisible();
    expect(screen.getByText(/Source passages shown/)).toBeVisible();
    await user.click(screen.getByText("DEMO-DOC · Example"));
    expect(screen.getByText("Demo source passage.")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Listen to answer" }));
    expect(speak).toHaveBeenCalledWith("A sourced response.");
    await user.type(screen.getByLabelText("Question"), "Another question");
    await user.click(screen.getByRole("button", { name: "Send ↑" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Assistant is unavailable",
    );
  });
  it("navigates crew profiles and handles an unknown route", async () => {
    const user = userEvent.setup();
    const app = render(<ConsoleApp initialPath="/crew" />);
    await user.click(await screen.findByRole("button", { name: "M. Rossi" }));
    expect(
      screen.getByRole("heading", { name: "M. Rossi · Personal readings" }),
    ).toBeVisible();
    await user.click(screen.getByRole("link", { name: "Mission overview" }));
    expect(
      await screen.findByRole("heading", { name: "Mission overview" }),
    ).toBeVisible();
    app.unmount();
    render(<ConsoleApp initialPath="/unknown" />);
    expect(
      screen.getByRole("heading", { name: "Page not found" }),
    ).toBeVisible();
  });
  it("renders empty Ground history and handles missing or failed chart data", async () => {
    const data = seed();
    data.ground!.templates = [];
    data.ground!.published = null;
    const mission = mockMission(data);
    const app = render(<GroundPage mission={mission} />);
    expect(screen.getByText("No plan templates.")).toBeVisible();
    expect(screen.getByText("No plan has been published.")).toBeVisible();
    app.unmount();
    const empty = { metric: "co2_mmhg", unit: "mmHg", points: [] };
    const chart = render(<Trend series={empty} rules={[]} />);
    expect(
      screen.getByText("No measurements in this time window."),
    ).toBeVisible();
    chart.rerender(
      <Trend
        series={{
          ...empty,
          points: [{ ts: new Date().toISOString(), avg: 3, min: 2, max: 4 }],
        }}
        rules={[
          {
            key: "co2",
            parameter: "ppco2",
            kind: "umbral",
            operator: ">",
            threshold: 3,
            unit: "mmHg",
            windowS: 60,
            severity: "ALERT",
            evidenceState: "DEMO",
            sourceRequirement: "Demo",
            sourceDocument: "DEMO",
          },
        ]}
      />,
    );
    expect(screen.getByText(/Threshold/)).toBeVisible();
    chart.unmount();
    mission.gateway.series = vi.fn().mockRejectedValue(Error("offline"));
    render(<ZoneTrends mission={mission} zoneId="missing" />);
    expect(await screen.findByText(/History is unavailable/)).toBeVisible();
    mission.gateway.dispose();
  });
});
