import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as importApi from "../api/import";
import type { ImportPreview } from "../lib/types";
import { ImportarExcel } from "./ImportarExcel";

vi.mock("../api/import", () => ({
  uploadPreview: vi.fn(),
  applyImport: vi.fn(),
}));

const PREVIEW: ImportPreview = {
  token: "abc",
  filename: "catalog.xlsx",
  sheets: [
    {
      sheet: "NOVELAS",
      category: "Novela",
      rows: [
        {
          row_number: 2,
          title: "Rayuela",
          author: "Cortázar, Julio",
          editorial: "Sudamericana",
          genre: null,
          price: "29500.00",
          stock: 3,
          observaciones: "Juli y Cande",
          is_new: true,
        },
      ],
    },
  ],
  summaries: [
    {
      sheet: "NOVELAS",
      category: "Novela",
      parsed: 1,
      inserts: 1,
      updates: 0,
      skips: 0,
      errors: 0,
    },
  ],
  errors: [],
  totals: { parsed: 1, inserts: 1, updates: 0, skips: 0, errors: 0 },
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ImportarExcel />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("ImportarExcel", () => {
  beforeEach(() => {
    vi.mocked(importApi.uploadPreview).mockResolvedValue(PREVIEW);
  });

  it("renders the Observaciones column in the preview table", async () => {
    const user = userEvent.setup();
    const { container } = renderPage();

    const file = new File(["xlsx"], "catalog.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, file);
    await user.click(screen.getByRole("button", { name: "Previsualizar" }));

    expect(await screen.findByText("Observaciones")).toBeInTheDocument();
    expect(screen.getByText("Juli y Cande")).toBeInTheDocument();
  });
});
