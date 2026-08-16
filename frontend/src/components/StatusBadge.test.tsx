import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "./StatusBadge";

describe("StatusBadge", () => {
  it("renders the Spanish label for In Stock", () => {
    render(<StatusBadge status="In Stock" />);
    expect(screen.getByText("En stock")).toBeInTheDocument();
  });

  it("renders the Spanish label for Low", () => {
    render(<StatusBadge status="Low" />);
    expect(screen.getByText("Stock bajo")).toBeInTheDocument();
  });

  it("renders the Spanish label for Out", () => {
    render(<StatusBadge status="Out" />);
    expect(screen.getByText("Sin stock")).toBeInTheDocument();
  });

  it("falls back to the raw status for unknown values", () => {
    render(<StatusBadge status="Desconocido" />);
    expect(screen.getByText("Desconocido")).toBeInTheDocument();
  });
});