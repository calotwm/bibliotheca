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
  deactivated: 0,
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

async function uploadAndPreview(container: HTMLElement) {
  const user = userEvent.setup();
  const file = new File(["xlsx"], "catalog.xlsx", {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  const input = container.querySelector('input[type="file"]') as HTMLInputElement;
  await user.upload(input, file);
  await user.click(screen.getByRole("button", { name: "Previsualizar" }));
}

describe("ImportarExcel", () => {
  beforeEach(() => {
    vi.mocked(importApi.uploadPreview).mockResolvedValue(PREVIEW);
  });

  it("renders the Observaciones column in the preview table", async () => {
    const { container } = renderPage();
    await uploadAndPreview(container);

    expect(await screen.findByText("Observaciones")).toBeInTheDocument();
    expect(screen.getByText("Juli y Cande")).toBeInTheDocument();
  });

  it("shows Juli for a row with null observaciones", async () => {
    vi.mocked(importApi.uploadPreview).mockResolvedValue({
      ...PREVIEW,
      sheets: [
        {
          ...PREVIEW.sheets[0],
          rows: [{ ...PREVIEW.sheets[0].rows[0], observaciones: null }],
        },
      ],
    });
    const { container } = renderPage();
    await uploadAndPreview(container);

    expect(await screen.findByText("Observaciones")).toBeInTheDocument();
    expect(screen.getByText("Juli")).toBeInTheDocument();
  });

  it("shows the deactivated count in the preview summary", async () => {
    vi.mocked(importApi.uploadPreview).mockResolvedValue({
      ...PREVIEW,
      deactivated: 3,
    });
    const { container } = renderPage();
    await uploadAndPreview(container);

    expect(await screen.findByText("Se desactivarán")).toBeInTheDocument();
    expect(screen.getByText("3 libros se desactivarán", { exact: false })).toBeInTheDocument();
  });
});
