export interface SkillEntry {
  skill: string;
  evidence: string;
}

export interface MissingSkill {
  skill: string;
  why: string;
}

export interface RoadmapItem {
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
}

export interface AnalysisResult {
  claimed: SkillEntry[];
  evidenced: SkillEntry[];
  missing: MissingSkill[];
  roadmap: RoadmapItem[];
  summary: string;
}

export interface ProgressEvent {
  type: 'step' | 'done' | 'error';
  step?: number;
  message?: string;
  result?: AnalysisResult;
}

export interface UploadFormData {
  file: File;
  githubUsername: string;
  role: string;
}
