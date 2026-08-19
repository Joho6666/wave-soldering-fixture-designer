import { describe, it, expect, beforeEach } from "vitest";
import { createRoot } from "react-dom/client";
import { act } from "react";
import { LayerConfirmModal } from "./LayerConfirmModal";
import { useProjectStore } from "../../store/useProjectStore";

describe("LayerConfirmModal React Hook Lifecycle", () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    useProjectStore.getState().resetProject();
  });

  it("renders closed -> open -> closed without hook order errors", async () => {
    const root = createRoot(container);

    // 1. Initial render when closed
    await act(async () => {
      useProjectStore.setState({ isLayerConfirmModalOpen: false });
      root.render(<LayerConfirmModal />);
    });
    expect(container.innerHTML).toBe("");

    // 2. Open modal
    await act(async () => {
      useProjectStore.setState({
        isLayerConfirmModalOpen: true,
        analysis: {
          width: 100,
          height: 100,
          fileCount: 2,
          holeCount: 10,
          outlineClosed: true,
          outlineAreaMm2: 10000,
          layers: [
            { id: "layer-1", filename: "board.gbr", type: "board_outline", confidence: 1.0, confirmed: false },
            { id: "layer-2", filename: "drill.drl", type: "drill", confidence: 0.95, confirmed: false },
          ],
        },
      });
    });
    expect(container.innerHTML).toContain("确认 Gerber 图层映射");
    expect(container.innerHTML).toContain("board.gbr");

    // 3. Close modal again
    await act(async () => {
      useProjectStore.setState({ isLayerConfirmModalOpen: false });
    });
    expect(container.innerHTML).toBe("");

    // 4. Open modal again (second cycle)
    await act(async () => {
      useProjectStore.setState({ isLayerConfirmModalOpen: true });
    });
    expect(container.innerHTML).toContain("确认 Gerber 图层映射");

    // 5. Cleanup
    await act(async () => {
      root.unmount();
    });
  });
});
