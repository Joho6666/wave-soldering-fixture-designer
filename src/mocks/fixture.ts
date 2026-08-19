import { FixtureResult } from "../types/fixture";
import { MOCK_DESIGN_ISSUES } from "./inspection";

export const MOCK_FIXTURE_RESULT: FixtureResult = {
  id: "320-WSJ-2024",
  pcb: {
    width: 180.0,
    height: 120.0
  },
  fixture: {
    width: 240.0,
    height: 180.0,
    thickness: 6.2,
    material: "合成石 (Durostone / FR4)"
  },
  locatingPins: 4,
  clamps: 4,
  keepoutRegions: 18,
  solderWindows: 12,
  issues: MOCK_DESIGN_ISSUES,
  status: "completed"
};
