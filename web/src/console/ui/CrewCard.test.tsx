import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CrewCard } from "./Common";
import { crew } from "../data/fixtures";
import type { CrewMember } from "../model";

describe("CrewCard", () => {
  it("shows the state and readings of a member that has wearable data", () => {
    render(<CrewCard person={crew[0]} />);

    expect(screen.getByText("A. Garcia")).toBeInTheDocument();
    expect(screen.getByText(/Nominal/)).toBeInTheDocument();
    expect(screen.queryByText(/No wearable/)).not.toBeInTheDocument();
  });

  it("does not invent a state or evidence for a member without wearable data", () => {
    const person: CrewMember = {
      id: "m1",
      name: "L. Chen",
      role: "Pilot",
      portrait: 2,
      state: null,
      vitals: [],
    };

    render(<CrewCard person={person} />);

    expect(screen.getByText("○ No wearable data")).toBeInTheDocument();
    expect(
      screen.getByText(
        "No wearable readings are available for this crew member.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Nominal/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Unverified/)).not.toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: /portrait of L. Chen/ }),
    ).toHaveClass("portrait-2");
  });
});
