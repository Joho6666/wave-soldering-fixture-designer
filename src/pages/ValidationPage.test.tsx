import { describe, it, expect, vi } from "vitest";
import { createRoot } from "react-dom/client";
import { act } from "react";
import { ValidationPage } from "./ValidationPage";

describe("ValidationPage", () => {
  it("renders golden cases from the validation API", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/api/validation/cases")) {
        return new Response(JSON.stringify({
          cases: [{
            caseId: "CASE-001",
            description: "placeholder",
            status: "awaiting_input",
            hasInput: false,
            hasReferenceDxf: false,
            hasGeneratedDxf: false,
            hasReport: false,
            notes: "no reference",
            report: null,
          }],
        }), { status: 200 });
      }
      return new Response("<svg></svg>", { status: 200, headers: { "Content-Type": "image/svg+xml" } });
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
    root.unmount();
  });
});
