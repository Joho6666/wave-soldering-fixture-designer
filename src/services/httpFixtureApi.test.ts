import { describe, expect, it, vi, beforeEach } from "vitest";

vi.mock("./mockFixtureApi", () => ({ mockFixtureApi: {} }));
vi.mock("./httpFixtureApi", async () => {
  const actual = await vi.importActual<typeof import("./httpFixtureApi")>("./httpFixtureApi");
  return actual;
});

describe("HTTP Fixture API request contract", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("uploads the source file using multipart FormData", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ id: "JOB-1" }), { status: 200 }));
    const { httpFixtureApi } = await import("./httpFixtureApi");
    await httpFixtureApi.createJob(new File(["zip"], "board.zip", { type: "application/zip" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs", expect.objectContaining({ method: "POST" }));
    const [, options] = fetchMock.mock.calls[0];
    expect(options?.body).toBeInstanceOf(FormData);
  });

  it("wraps real regeneration parameters in the expected request envelope", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ id: "JOB-1", status: "completed" }), { status: 200 }));
    const { httpFixtureApi } = await import("./httpFixtureApi");
    await httpFixtureApi.regenerate("JOB-1", {
      sinkClearanceMm: 0.2,
      keepoutClearanceMm: 1,
      solderClearanceMm: 3,
      filletRadiusMm: 1.85,
      clampHoleDiameterMm: 3.4,
      clampOffsetMm: 10,
      handholdWidthMm: 20,
      handholdHeightMm: 40,
      handholdOverlapMm: 1,
      handholdCornerRadiusMm: 2,
      fixtureMarginXmm: 20,
      fixtureMarginYmm: 30,
      fixtureCornerRadiusMm: 5,
      railWidthMm: 5,
      solderBarrierWidthMm: 10,
    });

    const [, options] = fetchMock.mock.calls[0];
    expect(options?.body).toContain('"parameters"');
    expect(options?.body).toContain('"keepoutClearanceMm":1');
  });

  it("fetches AI settings via GET /api/settings/ai", async () => {
    const mockData = {
      aiEnabled: true,
      aiProvider: "openai_compatible",
      aiBaseUrl: "https://api.openai.com/v1",
      aiModel: "gpt-4o-mini",
      aiApiKeyMasked: "sk-****cdef",
      aiTimeoutMs: 10000,
    };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(mockData), { status: 200 }));
    const { httpFixtureApi } = await import("./httpFixtureApi");
    const result = await httpFixtureApi.getAiSettings();

    expect(fetchMock).toHaveBeenCalledWith("/api/settings/ai", expect.objectContaining({ headers: expect.anything() }));
    expect(result.aiModel).toBe("gpt-4o-mini");
    expect(result.aiApiKeyMasked).toBe("sk-****cdef");
  });

  it("updates AI settings via PUT /api/settings/ai", async () => {
    const updatePayload = {
      aiEnabled: true,
      aiProvider: "openai_compatible",
      aiBaseUrl: "https://api.openai.com/v1",
      aiModel: "gpt-4o",
      aiApiKey: "sk-newkey123456",
      aiTimeoutMs: 8000,
    };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ ...updatePayload, aiApiKeyMasked: "sk-****3456" }), { status: 200 }));
    const { httpFixtureApi } = await import("./httpFixtureApi");
    const result = await httpFixtureApi.updateAiSettings(updatePayload);

    expect(fetchMock).toHaveBeenCalledWith("/api/settings/ai", expect.objectContaining({ method: "PUT" }));
    const [, options] = fetchMock.mock.calls[0];
    expect(options?.body).toContain('"aiModel":"gpt-4o"');
    expect(result.aiApiKeyMasked).toBe("sk-****3456");
  });

  it("tests AI connection via POST /api/settings/ai/test", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ ok: true, message: "OK" }), { status: 200 }));
    const { httpFixtureApi } = await import("./httpFixtureApi");
    const result = await httpFixtureApi.testAiConnection();

    expect(fetchMock).toHaveBeenCalledWith("/api/settings/ai/test", expect.objectContaining({ method: "POST" }));
    expect(result.ok).toBe(true);
  });
});

