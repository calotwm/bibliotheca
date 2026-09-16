import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DataTable } from "./DataTable";

interface Row {
  id: number;
  name: string;
  note: string;
}

const columns = [
  { key: "name", header: "Name", render: (row: Row) => row.name },
  {
    key: "note",
    header: "Note",
    className: "w-64",
    render: (row: Row) => row.note,
  },
];

const rows: Row[] = [
  { id: 1, name: "Alpha", note: "First note" },
  { id: 2, name: "Beta", note: "Second note" },
];

function getTable(): HTMLTableElement {
  return screen.getByRole("table");
}

describe("DataTable", () => {
  it("wraps long cell text by default so no cell can widen the table", () => {
    const { container } = render(<DataTable columns={columns} rows={rows} />);
    const table = getTable();
    // fixedLayout stays opt-in.
    expect(table.className).not.toContain("table-fixed");
    // Wrapping is the default: a long unbreakable value must never dictate the
    // column width and push the rest of the table off-screen.
    const cells = within(table).getAllByRole("cell");
    for (const cell of cells) {
      expect(cell.className).toContain("whitespace-normal");
      expect(cell.className).toContain("[overflow-wrap:anywhere]");
    }
    // The default shrink floor is low enough to keep adapting on a laptop.
    expect(container.querySelector("table")?.className).toBe(
      "w-full min-w-[520px] text-left text-sm"
    );
  });

  it("adds table-fixed when fixedLayout is true and propagates className to th", () => {
    render(<DataTable columns={columns} rows={rows} fixedLayout />);
    const table = getTable();
    expect(table.className).toContain("table-fixed");
    // The 'Note' column has className w-64; both the header <th> and the
    // data <td> for note must carry it now that fixedLayout propagates the
    // className to the header.
    const noteHeader = within(table).getByRole("columnheader", { name: "Note" });
    expect(noteHeader.className).toContain("w-64");
    // Cells still carry className (legacy behaviour). 2 rows x 2 cols = 4
    // cells. The 2nd cell in each row is the 'note' column.
    const cells = within(table).getAllByRole("cell");
    expect(cells.length).toBe(4);
    const noteCellAlpha = cells[1]; // row 0, note col
    expect(noteCellAlpha.className).toContain("w-64");
    const noteCellBeta = cells[3]; // row 1, note col
    expect(noteCellBeta.className).toContain("w-64");
    // The header <th> for 'Name' has no className and must stay empty
    // (no leakage of undefined/null into the DOM).
    const nameHeader = within(table).getByRole("columnheader", { name: "Name" });
    expect(nameHeader.className).not.toContain("undefined");
    expect(nameHeader.className).not.toContain("null");
  });

  it("lets a consumer opt out of wrapping when it truly wants no-wrap cells", () => {
    render(<DataTable columns={columns} rows={rows} wrapText={false} />);
    const cells = within(getTable()).getAllByRole("cell");
    for (const cell of cells) {
      expect(cell.className).not.toContain("whitespace-normal");
      expect(cell.className).not.toContain("[overflow-wrap:anywhere]");
    }
  });

  it("honours minWidthClass so a consumer can override the shrink floor", () => {
    const { container } = render(
      <DataTable columns={columns} rows={rows} minWidthClass="min-w-[700px]" />
    );
    expect(container.querySelector("table")?.className).toBe(
      "w-full min-w-[700px] text-left text-sm"
    );
  });
});