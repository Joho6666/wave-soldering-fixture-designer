export type JobStatus =
  | "idle"
  | "file_selected"
  | "uploading"
  | "parsing"
  | "layer_confirmation"
  | "generating"
  | "review_required"
  | "completed"
  | "failed";

export interface DiagnosticLog {
  time: string;
  level: "info" | "warning" | "error";
  message: string;
}

export type FixtureErrorCode =
  | "EMPTY_ARCHIVE"
  | "UNSUPPORTED_FILE"
  | "OUTLINE_NOT_FOUND"
  | "INVALID_GERBER"
  | "LAYER_UNCERTAIN"
  | "JOB_FAILED"
  | "NETWORK_ERROR"
  | "UNKNOWN";

export interface FixtureError {
  code: FixtureErrorCode;
  title: string;
  message: string;
  details?: string[];
  recoverable: boolean;
}

export interface Project {
  id: string;
  name: string;
  createdAt: string;
  status: JobStatus;
  progress: number;
  currentStepDescription?: string;
  errorCode?: string;
  errorMessage?: string;
  error?: FixtureError;
  logs: DiagnosticLog[];
}
