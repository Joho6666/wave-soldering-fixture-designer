import { FixtureParameters } from "./fixture";

export type AiCommandKind = "update_parameters" | "regenerate" | "locate_issue" | "explain_issue" | "no_op";

export interface AiCommand {
  kind: AiCommandKind;
  parameters?: Partial<FixtureParameters>;
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
