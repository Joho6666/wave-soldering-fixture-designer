import { describe, it, expect, vi } from "vitest";
import { createRoot } from "react-dom/client";
import { act } from "react";
import { ValidationPage } from "./ValidationPage";

describe("ValidationPage", () => {
  it("renders golden cases and CAD QA chrome", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/api/validation/cases")) {
        return new Response(JSON.stringify({
          cases: [{
            caseId: "CASE-001",
            description: "placeholder",
            status: "awaiting_reference",
            lifecycle: "IMPORTED",
            kind: "synthetic_demo",
            hasInput: true,
            hasReferenceDxf: false,
            hasGeneratedDxf: false,
            hasReport: false,
            notes: "no reference",
            manufacturing: {
              cnc: { tested: false, result: null },
              assembly: { tested: false, pcbFit: null },
              waveSolder: { tested: false, result: null },
            },
            report: null,
          }],
        }), { status: 200 });
      }
      return new Response("<svg><text>awaiting engineer DXF</text></svg>", { status: 200, headers: { "Content-Type": "image/svg+xml" } });
    });
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    await act(async () => {
      root.render(<ValidationPage />);
    });
    await act(async () => {
      await Promise.resolve();
    });
    expect(container.textContent).toContain("CASE-001");
    expect(container.textContent).toContain("Golden Cases");
    expect(container.textContent).toMatch(/Physical Validation/i);
    expect(container.textContent).toMatch(/awaiting engineer DXF/i);
    root.unmount();
  });
});
