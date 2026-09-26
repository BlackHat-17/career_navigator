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

export type SkillClassification = 'missing' | 'partial';
export type SkillState =
  | 'locked'
  | 'unlocked'
  | 'learning'
  | 'learning_completed'
  | 'mini_project_available'
  | 'project_in_progress'
  | 'project_submitted'
  | 'assessment_available'
  | 'assessment_started'
  | 'verified'
  | 'targeted_review'
  | 'retake_available';

export interface LearningResource {
  title: string;
  resource_type: string;
  url?: string | null;
  provider?: string | null;
  duration?: string | null;
}

export interface LearningLevel {
  level_number: number;
  title: string;
  objective: string;
  resources: LearningResource[];
  practice?: string | null;
  completion_status: string;
}

export interface MiniProject {
  title: string;
  description: string;
  requirements: string[];
  deliverables: string[];
  evaluation_criteria: string[];
}

export interface AssessmentResult {
  skill: string;
  score?: number | null;
  passed?: boolean | null;
  strong_topics: string[];
  weak_topics: string[];
  feedback?: string | null;
  recommended_action?: string | null;
}

export interface RoadmapSkill {
  name: string;
  classification: SkillClassification;
  state: SkillState;
  learning_track?: LearningLevel[] | null;
  mini_project?: MiniProject | null;
  assessment?: AssessmentResult | null;
}

export interface RoadmapResponse {
  roadmap_id?: string;
  skills: RoadmapSkill[];
  raw?: Record<string, unknown> | null;
}

export interface AnalysisResult {
  claimed: SkillEntry[];
  evidenced: SkillEntry[];
  missing: MissingSkill[];
  roadmap: RoadmapItem[];
  summary: string;
  skills?: RoadmapSkill[];
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
