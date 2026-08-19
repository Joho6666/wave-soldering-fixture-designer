export type IssueSeverity = "info" | "warning" | "error" | "blocking";

export interface IssueTarget {
  layerId: string;
  objectId?: string;
  x: number; // CAD mm X
  y: number; // CAD mm Y
  width?: number; // target box width
  height?: number; // target box height
}

export interface DesignIssue {
  id: string;
  type: string;
  title: string;
  description: string;
  severity: IssueSeverity;
  currentValue?: number;
  requiredValue?: number;
  unit?: string;
  confirmed?: boolean;
  target?: IssueTarget;
}
