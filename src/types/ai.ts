import { FixtureParameters } from "./fixture";

export type AiCommandKind =
  | "update_parameters"
  | "apply_recipe_preset"
  | "set_locating_pins"
  | "add_custom_region"
  | "auto_fix_drc"
  | "regenerate"
  | "locate_issue"
  | "explain_issue"
  | "no_op";

export interface AiCommand {
  kind: AiCommandKind;
  presetId?: "automotive_high_reliability" | "dense_consumer" | "thick_copper_heavy" | "standard";
  presetName?: string;
  parameters?: Partial<FixtureParameters>;
  suggestedParameters?: Partial<FixtureParameters>;
  pinDrillIds?: string[];
  regionType?: "keepout" | "solder";
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  label?: string;
  targetIssueIds?: string[];
  issueId?: string;
  reason: string;
  requiresConfirmation: boolean;
}

export interface AiCommandRequest {
  userMessage: string;
  conversationId?: string;
  command?: AiCommand;
  apply?: boolean;
  requestId?: string;
}

export interface AiCommandResponse {
  conversationId?: string;
  message: string;
  status: "complete" | "needs_confirmation" | "error";
  command: AiCommand;
  applied: boolean;
  job?: { id: string; status: string; progress: number } | null;
  errors: string[];
}

export interface AiMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  createdAt: string;
  command?: AiCommand;
  commandStatus?: "pending" | "applied" | "rejected" | "failed";
}
