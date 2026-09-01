import { describe, it, expect } from "vitest";
import { createRoot } from "react-dom/client";
import { act } from "react";
import { OverlayViewer } from "./OverlayViewer";

describe("OverlayViewer", () => {
  it("shows empty state when engineer DXF is missing", async () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    await act(async () => {
      root.render(<OverlayViewer svg={'<svg><text>awaiting engineer DXF</text></svg>'} />);
    });
    expect(container.textContent).toContain("awaiting engineer DXF");
    expect(container.querySelector('[data-testid="overlay-empty"]')).not.toBeNull();
    root.unmount();
  });

  it("renders layer toggles and a FAIL locate target", async () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    const svg = '<svg><g id="generated"></g><g id="reference"></g><g id="difference"></g></svg>';
    await act(async () => {
      root.render(<OverlayViewer svg={svg} highlightFeature="solder_openings" />);
    });
    expect(container.textContent).toMatch(/generated/i);
    expect(container.textContent).toMatch(/reference/i);
    expect(container.textContent).toMatch(/difference/i);
    const boxes = container.querySelectorAll('input[type="checkbox"]');
    expect(boxes.length).toBe(3);
    root.unmount();
  });
});
