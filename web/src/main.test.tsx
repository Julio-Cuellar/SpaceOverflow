import { screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

describe("main", () => {
  beforeEach(() => {
    vi.resetModules();
    document.body.innerHTML = '<div id="root"></div>';
  });

  it("mounts the app into #root, so the page is not blank", async () => {
    await import("./main");

    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "Mission overview" }),
      ).toBeVisible(),
    );
    expect(
      screen.getByText("Decision support prototype · Not a medical device"),
    ).toBeVisible();
  });
});
