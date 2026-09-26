/**
 * useProgress — persistent learning tracker via localStorage.
 *
 * Stores:
 *  - completedQuests: Set<number>   which roadmap quest indexes are done
 *  - skillProgress:  Record<skill, 0-100>  self-reported learning %
 *  - subTasks:       Record<questIndex, Set<subTaskId>>  checklist per quest
 *
 * Keyed by jobId so each analysis has its own progress.
 */
import { useState, useCallback, useEffect } from 'react';

// ── Sub-task templates per priority ─────────────────────────────────────────
export const SUB_TASKS: Record<string, { id: string; label: string }[]> = {
  high: [
    { id: 'read_docs',    label: '📖 Read the official docs' },
    { id: 'watch_video',  label: '▶️ Watch a tutorial video' },
    { id: 'build_demo',   label: '🔨 Build a small demo project' },
    { id: 'take_quiz',    label: '✅ Take a practice quiz' },
    { id: 'apply_work',   label: '🚀 Apply it in a real project' },
  ],
  medium: [
    { id: 'read_docs',    label: '📖 Read the official docs' },
    { id: 'watch_video',  label: '▶️ Watch a tutorial video' },
    { id: 'build_demo',   label: '🔨 Build a small demo project' },
    { id: 'take_quiz',    label: '✅ Take a practice quiz' },
  ],
  low: [
    { id: 'read_docs',    label: '📖 Read the official docs' },
    { id: 'watch_video',  label: '▶️ Watch a tutorial video' },
    { id: 'build_demo',   label: '🔨 Build a small demo project' },
  ],
};

// ── Types ────────────────────────────────────────────────────────────────────
export interface ProgressState {
  completedQuests: number[];          // serialisable array (Set in memory)
  skillProgress: Record<string, number>; // skill name → 0-100
  subTasks: Record<string, string[]>; // questIdx → completed subTask ids
  notes: Record<string, string>;      // questIdx → free-text note
}

const DEFAULT_STATE: ProgressState = {
  completedQuests: [],
  skillProgress: {},
  subTasks: {},
  notes: {},
};

function storageKey(jobId: string) {
  return `cn_progress_${jobId}`;
}

function load(jobId: string): ProgressState {
  try {
    const raw = localStorage.getItem(storageKey(jobId));
    if (raw) return { ...DEFAULT_STATE, ...JSON.parse(raw) };
  } catch { /* ignore */ }
  return { ...DEFAULT_STATE };
}

function save(jobId: string, state: ProgressState) {
  try {
    localStorage.setItem(storageKey(jobId), JSON.stringify(state));
  } catch { /* ignore */ }
}

// ── Hook ─────────────────────────────────────────────────────────────────────
export function useProgress(jobId: string) {
  const [state, setState] = useState<ProgressState>(() => load(jobId));

  // Persist on every change
  useEffect(() => {
    save(jobId, state);
  }, [jobId, state]);

  // ── Quest completion ───────────────────────────────────────────────────────
  const toggleQuest = useCallback((idx: number) => {
    setState(prev => {
      const set = new Set(prev.completedQuests);
      if (set.has(idx)) set.delete(idx); else set.add(idx);
      return { ...prev, completedQuests: [...set] };
    });
  }, []);

  const isQuestDone = useCallback((idx: number) =>
    state.completedQuests.includes(idx), [state.completedQuests]);

  // ── Skill progress ─────────────────────────────────────────────────────────
  const setSkillProgress = useCallback((skill: string, pct: number) => {
    setState(prev => ({
      ...prev,
      skillProgress: { ...prev.skillProgress, [skill]: Math.min(100, Math.max(0, pct)) },
    }));
  }, []);

  const getSkillProgress = useCallback((skill: string) =>
    state.skillProgress[skill] ?? 0, [state.skillProgress]);

  // ── Sub-tasks ──────────────────────────────────────────────────────────────
  const toggleSubTask = useCallback((questIdx: number, taskId: string) => {
    setState(prev => {
      const key = String(questIdx);
      const set = new Set(prev.subTasks[key] ?? []);
      if (set.has(taskId)) set.delete(taskId); else set.add(taskId);
      return { ...prev, subTasks: { ...prev.subTasks, [key]: [...set] } };
    });
  }, []);

  const getSubTasks = useCallback((questIdx: number): string[] =>
    state.subTasks[String(questIdx)] ?? [], [state.subTasks]);

  // ── Notes ──────────────────────────────────────────────────────────────────
  const setNote = useCallback((questIdx: number, text: string) => {
    setState(prev => ({
      ...prev,
      notes: { ...prev.notes, [String(questIdx)]: text },
    }));
  }, []);

  const getNote = useCallback((questIdx: number) =>
    state.notes[String(questIdx)] ?? '', [state.notes]);

  // ── Derived stats ──────────────────────────────────────────────────────────
  const completedCount = state.completedQuests.length;

  const overallLearningPct = useCallback((skills: string[]) => {
    if (!skills.length) return 0;
    const sum = skills.reduce((acc, s) => acc + (state.skillProgress[s] ?? 0), 0);
    return Math.round(sum / skills.length);
  }, [state.skillProgress]);

  return {
    state,
    // quests
    toggleQuest, isQuestDone, completedCount,
    completedQuests: state.completedQuests,
    // skills
    setSkillProgress, getSkillProgress,
    // sub-tasks
    toggleSubTask, getSubTasks,
    // notes
    setNote, getNote,
    // derived
    overallLearningPct,
  };
}
