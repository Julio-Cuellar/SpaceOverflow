import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeAll } from "vitest";
import { ConsoleApp } from "./ConsoleApp";
beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
  window.scrollTo = vi.fn();
});
describe("React mission console", () => {
  it("opens the English control center with four illustrative crew cards", async () => {
    render(<ConsoleApp initialPath="/" />);
    expect(
      await screen.findByRole("heading", {
        name: "Mission overview",
      }),
    ).toBeVisible();
    expect(
      await screen.findByRole("heading", {
        name: "Astronaut health monitoring",
      }),
    ).toBeVisible();
    expect(
      screen
        .getAllByRole("article")
        .filter((el) => el.className === "crew-card"),
    ).toHaveLength(4);
    expect(
      screen.getByRole("link", { name: /Astronaut portal/ }),
    ).toHaveAttribute("href", "/dashboard-tripulation");
  });
  it("brands the console as SYRA and spells out the name", async () => {
    render(<ConsoleApp initialPath="/" />);
    const sidebar = await screen.findByRole("complementary");
    expect(within(sidebar).getByText("SYRA")).toBeVisible();
    expect(
      within(sidebar).getByText("Spaceflight sYstem for Remote Assessment"),
    ).toBeVisible();
    expect(screen.queryByText(/odyssey/i)).not.toBeInTheDocument();
    await waitFor(() =>
      expect(document.title).toBe("SYRA · Mission overview"),
    );
  });
  it("brands the crew workspace as SYRA too", async () => {
    render(<ConsoleApp initialPath="/dashboard-tripulation" />);
    await screen.findByRole("heading", { name: "Hello, A. Garcia." });
    expect(screen.getByText("SYRA")).toBeVisible();
    expect(screen.queryByText(/odyssey/i)).not.toBeInTheDocument();
    expect(document.title).toBe("SYRA · My crew workspace");
  });
  it("moves from mission control to the astronaut portal and back", async () => {
    const user = userEvent.setup();
    render(<ConsoleApp initialPath="/" />);
    await user.click(
      await screen.findByRole("link", { name: /Astronaut portal/ }),
    );
    expect(
      await screen.findByRole("heading", { name: "Hello, A. Garcia." }),
    ).toBeVisible();
    // The workspace stays standalone: no mission navigation, only a way back.
    expect(
      screen.queryByRole("navigation", { name: "Mission navigation" }),
    ).not.toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: /Mission control/ }));
    expect(
      await screen.findByRole("heading", { name: "Mission overview" }),
    ).toBeVisible();
    expect(
      screen.getByRole("navigation", { name: "Mission navigation" }),
    ).toBeVisible();
  });
  it("shows only the current astronaut in the standalone workspace", async () => {
    render(<ConsoleApp initialPath="/dashboard-tripulation" />);
    expect(
      await screen.findByRole("heading", { name: "Hello, A. Garcia." }),
    ).toBeVisible();
    expect(screen.queryByText("L. Chen")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("navigation", { name: "Mission navigation" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Open mission assistant" }),
    ).toBeVisible();
  });
  it("completes a task and reflects it in the personal routine", async () => {
    const user = userEvent.setup();
    render(<ConsoleApp initialPath="/dashboard-tripulation" />);
    await user.click(
      await screen.findByRole("button", {
        name: "Mobility and stretching",
      }),
    );
    await user.click(screen.getByRole("button", { name: "Complete task" }));
    await waitFor(() =>
      expect(screen.getByText("2 of 4 complete · 2 pending")).toBeVisible(),
    );
    await user.click(screen.getByRole("button", { name: "My routine" }));
    await user.click(screen.getByRole("button", { name: "Completed" }));
    expect(
      await screen.findByRole("button", {
        name: "Mobility and stretching",
      }),
    ).toBeVisible();
  });
  it("keeps the assistant conversation after closing and reopening it", async () => {
    const askAssistant = vi.fn().mockResolvedValue({
      outcome: "NO_INFO",
      text: "No source was found for this question.",
      citations: [],
    });
    const user = userEvent.setup();
    render(
      <ConsoleApp
        initialPath="/dashboard-tripulation"
        askAssistant={askAssistant}
      />,
    );
    await screen.findByRole("heading", { name: "My health" });
    await user.click(
      screen.getByRole("button", { name: "Open mission assistant" }),
    );
    await user.type(screen.getByLabelText("Question"), "test question");
    await user.click(screen.getByRole("button", { name: "Send ↑" }));
    expect(
      await screen.findByText("No source was found for this question."),
    ).toBeVisible();
    await user.click(
      screen.getByRole("button", { name: "Close Mission assistant" }),
    );
    await user.click(
      screen.getByRole("button", { name: "Open mission assistant" }),
    );
    expect(
      screen.getByText("No source was found for this question."),
    ).toBeVisible();
    expect(askAssistant).toHaveBeenCalledWith("test question");
  });
  it("does not let ground tasks expose edit or delete controls", async () => {
    const user = userEvent.setup();
    render(<ConsoleApp initialPath="/tasks" />);
    await user.click(
      await screen.findByRole("button", {
        name: "Inspect habitat air filters",
      }),
    );
    const dialog = screen.getByRole("dialog");
    expect(
      within(dialog).queryByRole("button", { name: "Edit own task" }),
    ).not.toBeInTheDocument();
    expect(
      within(dialog).getByRole("button", { name: "Report blocker" }),
    ).toBeDisabled();
  });
  it("immediately removes demo personal data when the backend adapter is selected", async () => {
    const user = userEvent.setup();
    render(<ConsoleApp initialPath="/dashboard-tripulation" />);
    await screen.findByRole("heading", { name: "Hello, A. Garcia." });
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Data source" }),
      "backend",
    );
    expect(
      screen.queryByRole("heading", { name: "Hello, A. Garcia." }),
    ).not.toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "My crew dashboard" }),
    ).toBeVisible();
  });
});
