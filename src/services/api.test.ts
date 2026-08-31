import { describe, expect, it } from "vitest";
import { isClientDemoMode } from "./api";

describe("API dispatcher", () => {
  it("does not enable mock unless VITE_USE_MOCK_API is true", () => {
    expect(isClientDemoMode).toBe(false);
  });
});
