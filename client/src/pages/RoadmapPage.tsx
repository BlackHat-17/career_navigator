import { useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import PageTransition from '../components/PageTransition';
import { useProgress, SUB_TASKS } from '../lib/useProgress';
import type { AnalysisResult, RoadmapItem } from '../types';

/* ── Tutorial link database ──────────────────────────────────────── */
type TutLink = { label: string; url: string; icon: string; color: string };

const RESOURCE_MAP: { keywords: string[]; links: TutLink[] }[] = [
  {
    keywords: ['docker', 'container', 'kubernetes', 'k8s'],
    links: [
      { label: 'Docker — Get Started', url: 'https://docs.docker.com/get-started/', icon: '📘', color: '#2496ed' },
      { label: 'Docker Tutorial — freeCodeCamp (YouTube)', url: 'https://www.youtube.com/watch?v=fqMOX6JJhGo', icon: '▶️', color: '#ff0000' },
      { label: 'Docker — GeeksforGeeks', url: 'https://www.geeksforgeeks.org/docker-tutorial/', icon: '🟢', color: '#2f8d46' },
    ],
  },
  {
    keywords: ['test', 'jest', 'vitest', 'testing', 'unit test', 'coverage'],
    links: [
      { label: 'Jest — Official Docs', url: 'https://jestjs.io/docs/getting-started', icon: '📘', color: '#c21325' },
      { label: 'JavaScript Testing — freeCodeCamp (YouTube)', url: 'https://www.youtube.com/watch?v=IPiUDhwnZxA', icon: '▶️', color: '#ff0000' },
      { label: 'Testing in JavaScript — GeeksforGeeks', url: 'https://www.geeksforgeeks.org/javascript-testing/', icon: '🟢', color: '#2f8d46' },
    ],
  },
  {
    keywords: ['aws', 'cloud', 'gcp', 'azure', 'ec2', 's3', 'lambda', 'certified'],
    links: [
      { label: 'AWS Free Tier — Get Started', url: 'https://aws.amazon.com/free/', icon: '📘', color: '#ff9900' },
      { label: 'AWS Cloud Practitioner — freeCodeCamp (YouTube)', url: 'https://www.youtube.com/watch?v=SOTamWNgDKc', icon: '▶️', color: '#ff0000' },
      { label: 'AWS Tutorial — GeeksforGeeks', url: 'https://www.geeksforgeeks.org/aws-tutorial/', icon: '🟢', color: '#2f8d46' },
    ],
  },
  {
    keywords: ['system design', 'distributed', 'scalab', 'architecture'],
    links: [
      { label: 'System Design Primer — GitHub', url: 'https://github.com/donnemartin/system-design-primer', icon: '⭐', color: '#6e40c9' },
      { label: 'System Design Interview — YouTube', url: 'https://www.youtube.com/watch?v=i7twT3x5yv8', icon: '▶️', color: '#ff0000' },
      { label: 'System Design — GeeksforGeeks', url: 'https://www.geeksforgeeks.org/system-design-tutorial/', icon: '🟢', color: '#2f8d46' },
    ],
  },
  {
    keywords: ['performance', 'optimis', 'core web vitals', 'lighthouse', 'lazy'],
    links: [
      { label: 'Web.dev — Core Web Vitals', url: 'https://web.dev/explore/learn-core-web-vitals', icon: '📘', color: '#1a73e8' },
      { label: 'Frontend Performance — YouTube', url: 'https://www.youtube.com/watch?v=AQqFZ5t8uNc', icon: '▶️', color: '#ff0000' },
      { label: 'Web Performance — GeeksforGeeks', url: 'https://www.geeksforgeeks.org/web-performance/', icon: '🟢', color: '#2f8d46' },
    ],
  },
  {
    keywords: ['typescript', 'ts'],
    links: [
      { label: 'TypeScript — Official Handbook', url: 'https://www.typescriptlang.org/docs/handbook/intro.html', icon: '📘', color: '#3178c6' },
      { label: 'TypeScript Full Course — YouTube', url: 'https://www.youtube.com/watch?v=30LWjhZzg50', icon: '▶️', color: '#ff0000' },
      { label: 'TypeScript Tutorial — GeeksforGeeks', url: 'https://www.geeksforgeeks.org/typescript/', icon: '🟢', color: '#2f8d46' },
    ],
  },
  {
    keywords: ['react', 'component', 'hook', 'jsx'],
    links: [
      { label: 'React — Official Docs', url: 'https://react.dev/learn', icon: '📘', color: '#61dafb' },
      { label: 'React Full Course — freeCodeCamp (YouTube)', url: 'https://www.youtube.com/watch?v=bMknfKXIFA8', icon: '▶️', color: '#ff0000' },
      { label: 'ReactJS Tutorial — GeeksforGeeks', url: 'https://www.geeksforgeeks.org/react-tutorial/', icon: '🟢', color: '#2f8d46' },
    ],
  },
  {
    keywords: ['node', 'express', 'backend', 'api', 'server'],
    links: [
      { label: 'Node.js — Official Docs', url: 'https://nodejs.org/en/docs', icon: '📘', color: '#68a063' },
      { label: 'Node.js Full Course — YouTube', url: 'https://www.youtube.com/watch?v=Oe421EPjeBE', icon: '▶️', color: '#ff0000' },
      { label: 'Node.js Tutorial — GeeksforGeeks', url: 'https://www.geeksforgeeks.org/nodejs/', icon: '🟢', color: '#2f8d46' },
    ],
  },
  {
    keywords: ['sql', 'database', 'postgres', 'mysql', 'db'],
    links: [
      { label: 'SQL Tutorial — W3Schools', url: 'https://www.w3schools.com/sql/', icon: '📘', color: '#04aa6d' },
      { label: 'SQL Full Course — freeCodeCamp (YouTube)', url: 'https://www.youtube.com/watch?v=HXV3zeQKqGY', icon: '▶️', color: '#ff0000' },
      { label: 'SQL Tutorial — GeeksforGeeks', url: 'https://www.geeksforgeeks.org/sql-tutorial/', icon: '🟢', color: '#2f8d46' },
    ],
  },
  {
    keywords: ['git', 'github', 'version control'],
    links: [
      { label: 'Git — Official Docs', url: 'https://git-scm.com/doc', icon: '📘', color: '#f05032' },
      { label: 'Git & GitHub Crash Course — YouTube', url: 'https://www.youtube.com/watch?v=RGOj5yH7evk', icon: '▶️', color: '#ff0000' },
      { label: 'Git Tutorial — GeeksforGeeks', url: 'https://www.geeksforgeeks.org/git-tutorial/', icon: '🟢', color: '#2f8d46' },
    ],
  },
  {
    keywords: ['graphql'],
    links: [
      { label: 'GraphQL — Official Docs', url: 'https://graphql.org/learn/', icon: '📘', color: '#e535ab' },
      { label: 'GraphQL Full Course — freeCodeCamp (YouTube)', url: 'https://www.youtube.com/watch?v=ed8SzALpx1Q', icon: '▶️', color: '#ff0000' },
      { label: 'GraphQL Tutorial — GeeksforGeeks', url: 'https://www.geeksforgeeks.org/graphql/', icon: '🟢', color: '#2f8d46' },
    ],
  },
  {
    keywords: ['rust'],
    links: [
      { label: 'The Rust Book — Official', url: 'https://doc.rust-lang.org/book/', icon: '📘', color: '#f74c00' },
      { label: 'Rust Crash Course — YouTube', url: 'https://www.youtube.com/watch?v=zF34dRivLOw', icon: '▶️', color: '#ff0000' },
      { label: 'Rust Tutorial — GeeksforGeeks', url: 'https://www.geeksforgeeks.org/introduction-to-rust-programming-language/', icon: '🟢', color: '#2f8d46' },
    ],
  },
];

const FALLBACK_LINKS: TutLink[] = [
  { label: 'Search on freeCodeCamp', url: 'https://www.freecodecamp.org/news/', icon: '🔍', color: '#0a0a23' },
  { label: 'Search on GeeksforGeeks', url: 'https://www.geeksforgeeks.org/', icon: '🟢', color: '#2f8d46' },
  { label: 'Search on YouTube', url: 'https://www.youtube.com/', icon: '▶️', color: '#ff0000' },
];

function getTutorialLinks(title: string, description: string): TutLink[] {
  const text = `${title} ${description}`.toLowerCase();
  for (const entry of RESOURCE_MAP) {
    if (entry.keywords.some(kw => text.includes(kw))) return entry.links;
  }
  return FALLBACK_LINKS;
}

/* ── XP / Level system ───────────────────────────────────────────── */
const XP_PER_QUEST: Record<string, number> = { high: 500, medium: 300, low: 150 };
const TOTAL_XP = 1500;

function calcLevel(xp: number) {
  if (xp < 300)  return { level: 1, title: 'Novice',       color: '#71717a', next: 300  };
  if (xp < 700)  return { level: 2, title: 'Apprentice',   color: '#6079f8', next: 700  };
  if (xp < 1200) return { level: 3, title: 'Practitioner', color: '#a78bfa', next: 1200 };
  if (xp < 1800) return { level: 4, title: 'Expert',       color: '#f59e0b', next: 1800 };
  return               { level: 5, title: 'Master',        color: '#10b981', next: 2500 };
}

/* ── Badges ──────────────────────────────────────────────────────── */
const ALL_BADGES = [
  { id: 'first_quest',   icon: '🎯', label: 'First Quest',   desc: 'Complete your first task'         },
  { id: 'half_way',      icon: '⚡', label: 'Momentum',      desc: 'Complete 3 quests'                },
  { id: 'high_roller',   icon: '🔥', label: 'High Priority', desc: 'Complete a high-priority quest'   },
  { id: 'completionist', icon: '👑', label: 'Completionist', desc: 'Complete all quests'              },
  { id: 'speed_runner',  icon: '💨', label: 'Speed Runner',  desc: 'Complete 2 quests in one session' },
  { id: 'scholar',       icon: '📚', label: 'Scholar',       desc: '500 XP earned'                    },
];

/* ── Priority config ─────────────────────────────────────────────── */
const P: Record<string, { label: string; color: string; border: string; bg: string; glow: string; icon: string }> = {
  high:   { label: 'HIGH',   color: '#fda4af', border: 'rgba(244,63,94,0.35)',  bg: 'rgba(244,63,94,0.08)',  glow: 'rgba(244,63,94,0.3)',  icon: '🔥' },
  medium: { label: 'MEDIUM', color: '#fcd34d', border: 'rgba(245,158,11,0.35)', bg: 'rgba(245,158,11,0.08)', glow: 'rgba(245,158,11,0.3)', icon: '⚡' },
  low:    { label: 'LOW',    color: '#6ee7b7', border: 'rgba(16,185,129,0.35)', bg: 'rgba(16,185,129,0.08)', glow: 'rgba(16,185,129,0.3)', icon: '🌱' },
};

/* ── Sub-task checklist inside each quest card ───────────────────── */
function SubTaskChecklist({
  questIdx,
  priority,
  progress,
}: {
  questIdx: number;
  priority: string;
  progress: ReturnType<typeof useProgress>;
}) {
  const tasks      = SUB_TASKS[priority] ?? SUB_TASKS.low;
  const doneTasks  = progress.getSubTasks(questIdx);
  const donePct    = Math.round((doneTasks.length / tasks.length) * 100);
  const note       = progress.getNote(questIdx);
  const [showNote, setShowNote] = useState(false);

  return (
    <div className="mt-4 space-y-3" onClick={e => e.stopPropagation()}>
      {/* Sub-task progress bar */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] font-bold tracking-widest uppercase" style={{ color: '#3f3f46' }}>
            🗂️ Learning Checklist
          </span>
          <span className="text-[10px] font-bold" style={{ color: donePct === 100 ? '#34d399' : '#52525b' }}>
            {doneTasks.length}/{tasks.length} done
          </span>
        </div>
        <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
          <motion.div
            className="h-full rounded-full"
            animate={{ width: `${donePct}%` }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
            style={{
              background: donePct === 100
                ? 'linear-gradient(90deg,#10b981,#34d399)'
                : 'linear-gradient(90deg,#6079f8,#a78bfa)',
              boxShadow: donePct === 100 ? '0 0 8px rgba(16,185,129,0.5)' : '0 0 8px rgba(96,121,248,0.4)',
            }}
          />
        </div>
      </div>

      {/* Checklist items */}
      <div className="space-y-1.5">
        {tasks.map(task => {
          const done = doneTasks.includes(task.id);
          return (
            <button
              key={task.id}
              onClick={() => progress.toggleSubTask(questIdx, task.id)}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-all duration-150"
              style={{
                background: done ? 'rgba(16,185,129,0.08)' : 'rgba(255,255,255,0.03)',
                border: `1px solid ${done ? 'rgba(16,185,129,0.3)' : 'rgba(255,255,255,0.06)'}`,
              }}
            >
              {/* Checkbox */}
              <div className="w-5 h-5 rounded-md flex items-center justify-center shrink-0 transition-all duration-200"
                style={{
                  background: done ? 'rgba(16,185,129,0.25)' : 'rgba(255,255,255,0.05)',
                  border: `1.5px solid ${done ? '#34d399' : 'rgba(255,255,255,0.1)'}`,
                }}>
                <AnimatePresence>
                  {done && (
                    <motion.span
                      key="check"
                      initial={{ scale: 0, rotate: -20 }}
                      animate={{ scale: 1, rotate: 0 }}
                      exit={{ scale: 0 }}
                      className="text-[10px] font-black"
                      style={{ color: '#34d399' }}
                    >✓</motion.span>
                  )}
                </AnimatePresence>
              </div>
              <span className="text-xs flex-1" style={{ color: done ? '#34d399' : '#94a3b8', textDecoration: done ? 'line-through' : 'none' }}>
                {task.label}
              </span>
            </button>
          );
        })}
      </div>

      {/* Notes toggle */}
      <div>
        <button
          onClick={() => setShowNote(v => !v)}
          className="text-[10px] font-bold flex items-center gap-1 transition-colors"
          style={{ color: showNote ? '#818cf8' : '#3f3f46' }}
        >
          📝 {showNote ? 'Hide notes' : 'Add a note'}
        </button>
        <AnimatePresence>
          {showNote && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden mt-2"
            >
              <textarea
                value={note}
                onChange={e => progress.setNote(questIdx, e.target.value)}
                placeholder="What did you learn? Any blockers?"
                rows={3}
                className="w-full text-xs rounded-xl px-3 py-2.5 resize-none outline-none transition-all"
                style={{
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  color: '#e2e8f0',
                  fontFamily: 'inherit',
                }}
                onFocus={e => (e.target.style.borderColor = 'rgba(99,102,241,0.4)')}
                onBlur={e => (e.target.style.borderColor = 'rgba(255,255,255,0.08)')}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

/* ── Overall Progress Dashboard ──────────────────────────────────── */
function ProgressDashboard({
  items,
  progress,
  earnedXP,
  lvlData,
  unlockedBadges,
}: {
  items: RoadmapItem[];
  progress: ReturnType<typeof useProgress>;
  earnedXP: number;
  lvlData: ReturnType<typeof calcLevel>;
  unlockedBadges: Set<string>;
}) {
  // Per-priority completion stats
  const byPriority = (['high', 'medium', 'low'] as const).map(p => {
    const total = items.filter(it => it.priority === p).length;
    const done  = items.filter((it, i) => it.priority === p && progress.isQuestDone(i)).length;
    return { p, total, done };
  });

  // Sub-task aggregate
  const totalSubTasks = items.reduce((sum, it) => sum + (SUB_TASKS[it.priority]?.length ?? 3), 0);
  const doneSubTasks  = items.reduce((sum, _it, i) => sum + progress.getSubTasks(i).length, 0);
  const subPct = totalSubTasks > 0 ? Math.round((doneSubTasks / totalSubTasks) * 100) : 0;

  const questPct = items.length > 0 ? Math.round((progress.completedCount / items.length) * 100) : 0;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: 0.1 }}
      className="rounded-3xl p-6 relative overflow-hidden"
      style={{
        background: 'rgba(22,27,39,0.85)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(255,255,255,0.07)',
        boxShadow: '0 0 0 1px rgba(96,121,248,0.08), 0 16px 48px rgba(0,0,0,0.4)',
      }}
    >
      <div className="absolute top-0 left-8 right-8 h-px"
        style={{ background: 'linear-gradient(90deg, transparent, rgba(96,121,248,0.6), rgba(167,139,250,0.6), transparent)' }} />

      <div className="flex items-center gap-6 flex-wrap">
        {/* Avatar / level badge */}
        <div className="relative shrink-0">
          <motion.div
            animate={{ boxShadow: [`0 0 20px ${lvlData.color}44`, `0 0 40px ${lvlData.color}88`, `0 0 20px ${lvlData.color}44`] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="w-20 h-20 rounded-2xl flex items-center justify-center text-4xl"
            style={{ background: `${lvlData.color}18`, border: `2px solid ${lvlData.color}44` }}>
            {lvlData.level === 1 ? '🌱' : lvlData.level === 2 ? '⚡' : lvlData.level === 3 ? '🔮' : lvlData.level === 4 ? '🏆' : '👑'}
          </motion.div>
          <div className="absolute -bottom-2 -right-2 w-7 h-7 rounded-full flex items-center justify-center text-xs font-black"
            style={{ background: lvlData.color, color: '#000', boxShadow: `0 0 10px ${lvlData.color}` }}>
            {lvlData.level}
          </div>
        </div>

        <div className="flex-1 min-w-0 space-y-3">
          {/* Level + XP */}
          <div className="flex items-center gap-3 flex-wrap">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-black text-white">Level {lvlData.level}</span>
                <span className="text-xs font-bold px-2 py-0.5 rounded-full"
                  style={{ background: `${lvlData.color}22`, border: `1px solid ${lvlData.color}44`, color: lvlData.color }}>
                  {lvlData.title}
                </span>
              </div>
              <p className="text-xs mt-0.5" style={{ color: '#52525b' }}>
                {earnedXP} XP · {Math.max(0, lvlData.next - earnedXP)} XP to Level {lvlData.level + 1}
              </p>
            </div>
          </div>

          {/* XP bar */}
          <div className="h-3 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.05)' }}>
            <motion.div className="h-full rounded-full relative overflow-hidden"
              initial={{ width: 0 }}
              animate={{ width: `${Math.min((earnedXP / TOTAL_XP) * 100, 100)}%` }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
              style={{ background: `linear-gradient(90deg, ${lvlData.color}, ${lvlData.color}bb)`, boxShadow: `0 0 12px ${lvlData.color}88` }}>
              <motion.div className="absolute inset-0"
                animate={{ x: ['-100%', '200%'] }} transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut', repeatDelay: 0.5 }}
                style={{ background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)', width: '40%' }} />
            </motion.div>
          </div>

          {/* Stats row */}
          <div className="flex gap-6 flex-wrap">
            {[
              { label: 'Quests',    value: `${progress.completedCount}/${items.length}` },
              { label: 'XP earned', value: earnedXP },
              { label: 'Badges',    value: unlockedBadges.size },
              { label: 'Sub-tasks', value: `${doneSubTasks}/${totalSubTasks}` },
            ].map(s => (
              <div key={s.label}>
                <div className="text-base font-black text-white">{s.value}</div>
                <div className="text-[10px] mt-0.5" style={{ color: '#52525b' }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Dual progress bars: quests + sub-tasks */}
      <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Quest completion */}
        <div className="rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-white">⚔️ Quest Progress</span>
            <span className="text-xs font-black" style={{ color: questPct === 100 ? '#34d399' : '#818cf8' }}>{questPct}%</span>
          </div>
          <div className="h-2 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
            <motion.div className="h-full rounded-full"
              animate={{ width: `${questPct}%` }}
              transition={{ duration: 0.6 }}
              style={{ background: questPct === 100 ? 'linear-gradient(90deg,#10b981,#34d399)' : 'linear-gradient(90deg,#6079f8,#818cf8)' }}
            />
          </div>
          {/* Per-priority mini bars */}
          <div className="mt-3 space-y-1.5">
            {byPriority.map(({ p, total, done }) => {
              const pStyle = P[p];
              const pct = total > 0 ? Math.round((done / total) * 100) : 0;
              return (
                <div key={p} className="flex items-center gap-2">
                  <span className="text-[10px] w-14 shrink-0" style={{ color: pStyle.color }}>{pStyle.icon} {pStyle.label}</span>
                  <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
                    <motion.div className="h-full rounded-full"
                      animate={{ width: `${pct}%` }}
                      transition={{ duration: 0.5, delay: 0.1 }}
                      style={{ background: pStyle.color }}
                    />
                  </div>
                  <span className="text-[10px] w-8 text-right shrink-0" style={{ color: '#52525b' }}>{done}/{total}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Sub-task learning progress */}
        <div className="rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-white">🗂️ Learning Steps</span>
            <span className="text-xs font-black" style={{ color: subPct === 100 ? '#34d399' : '#a78bfa' }}>{subPct}%</span>
          </div>
          <div className="h-2 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
            <motion.div className="h-full rounded-full"
              animate={{ width: `${subPct}%` }}
              transition={{ duration: 0.6 }}
              style={{ background: subPct === 100 ? 'linear-gradient(90deg,#10b981,#34d399)' : 'linear-gradient(90deg,#a78bfa,#c4b5fd)' }}
            />
          </div>
          <p className="text-[10px] mt-3" style={{ color: '#52525b' }}>
            {doneSubTasks} of {totalSubTasks} learning steps completed across all quests
          </p>
          {/* Motivational message */}
          <p className="text-xs mt-2 font-semibold" style={{ color: subPct >= 80 ? '#34d399' : subPct >= 40 ? '#fbbf24' : '#818cf8' }}>
            {subPct === 0 ? '🚀 Start your first learning step!' :
             subPct < 40  ? '📖 Keep learning — you\'re building momentum' :
             subPct < 80  ? '⚡ Great progress — halfway through the journey!' :
             subPct < 100 ? '🔥 Almost there — finish strong!' :
                            '👑 All learning steps complete!'}
          </p>
        </div>
      </div>
    </motion.div>
  );
}

/* ── Quest card ──────────────────────────────────────────────────── */
function QuestCard({
  item,
  index,
  progress,
  justUnlocked,
}: {
  item: RoadmapItem;
  index: number;
  progress: ReturnType<typeof useProgress>;
  justUnlocked: boolean;
}) {
  const p    = P[item.priority] ?? P.low;
  const xp   = XP_PER_QUEST[item.priority] ?? 150;
  const [expanded, setExpanded] = useState(false);
  const links = getTutorialLinks(item.title, item.description);
  const completed = progress.isQuestDone(index);

  // Sub-task progress for this quest
  const subTaskDefs = SUB_TASKS[item.priority] ?? SUB_TASKS.low;
  const doneSubs    = progress.getSubTasks(index);
  const subPct      = Math.round((doneSubs.length / subTaskDefs.length) * 100);

  return (
    <motion.div
      initial={{ opacity: 0, y: 32 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06, type: 'spring', stiffness: 120, damping: 18 }}
      className="relative rounded-2xl overflow-hidden"
      style={{
        background: completed ? 'rgba(16,185,129,0.08)' : 'rgba(22,27,39,0.85)',
        border: `1px solid ${completed ? 'rgba(16,185,129,0.35)' : p.border}`,
        backdropFilter: 'blur(16px)',
        boxShadow: completed
          ? '0 0 20px rgba(16,185,129,0.1)'
          : `0 0 0 1px rgba(0,0,0,0.2), 0 8px 32px rgba(0,0,0,0.3)`,
        opacity: completed ? 0.82 : 1,
      }}
    >
      {/* Top glow line */}
      {!completed && (
        <div className="absolute top-0 left-4 right-4 h-px"
          style={{ background: `linear-gradient(90deg, transparent, ${p.color}, transparent)`, opacity: 0.6 }} />
      )}

      {/* Sub-task progress stripe at top when in progress */}
      {!completed && subPct > 0 && subPct < 100 && (
        <div className="absolute top-0 left-0 h-0.5 transition-all duration-500"
          style={{ width: `${subPct}%`, background: 'linear-gradient(90deg,#6079f8,#a78bfa)' }} />
      )}

      {/* XP unlock flash */}
      <AnimatePresence>
        {justUnlocked && (
          <motion.div
            initial={{ opacity: 0, scale: 0.5, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4 }}
            className="absolute top-3 right-14 text-xs font-black px-2 py-1 rounded-full z-10"
            style={{ background: 'rgba(16,185,129,0.9)', color: '#fff' }}>
            +{xp} XP!
          </motion.div>
        )}
      </AnimatePresence>

      <div className="p-5">
        <div className="flex items-start gap-4">
          {/* Quest number / check button */}
          <motion.button
            onClick={e => { e.stopPropagation(); progress.toggleQuest(index); }}
            whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}
            className="w-10 h-10 rounded-xl flex items-center justify-center text-sm font-black shrink-0 transition-all duration-300"
            style={{
              background: completed ? 'rgba(16,185,129,0.2)' : p.bg,
              border: `2px solid ${completed ? 'rgba(16,185,129,0.6)' : p.border}`,
              color: completed ? '#34d399' : p.color,
              boxShadow: completed ? '0 0 14px rgba(16,185,129,0.3)' : `0 0 10px ${p.glow}`,
            }}>
            <AnimatePresence mode="wait">
              {completed ? (
                <motion.span key="check" initial={{ scale: 0, rotate: -90 }} animate={{ scale: 1, rotate: 0 }}
                  transition={{ type: 'spring', stiffness: 300 }}>✓</motion.span>
              ) : (
                <motion.span key="num">{index + 1}</motion.span>
              )}
            </AnimatePresence>
          </motion.button>

          <div className="flex-1 min-w-0" onClick={() => setExpanded(e => !e)}>
            <div className="flex items-center gap-2 flex-wrap mb-1 cursor-pointer">
              <span className={`text-sm font-bold ${completed ? 'line-through opacity-50' : 'text-white'}`}>
                {item.title}
              </span>
              <span className="text-[10px] font-black px-2 py-0.5 rounded-full tracking-wider"
                style={{ background: p.bg, border: `1px solid ${p.border}`, color: p.color }}>
                {p.icon} {p.label}
              </span>
            </div>

            {/* Sub-task mini progress indicator (collapsed state) */}
            {!expanded && subPct > 0 && (
              <div className="flex items-center gap-2 mb-1">
                <div className="flex-1 h-1 rounded-full overflow-hidden max-w-[120px]" style={{ background: 'rgba(255,255,255,0.06)' }}>
                  <div className="h-full rounded-full" style={{
                    width: `${subPct}%`,
                    background: subPct === 100 ? '#34d399' : 'linear-gradient(90deg,#6079f8,#a78bfa)',
                  }} />
                </div>
                <span className="text-[10px]" style={{ color: subPct === 100 ? '#34d399' : '#52525b' }}>
                  {doneSubs.length}/{subTaskDefs.length} steps
                </span>
              </div>
            )}

            {/* Expanded content */}
            <AnimatePresence>
              {expanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.22 }}
                  className="overflow-hidden"
                >
                  <p className="text-xs leading-relaxed mb-4 mt-1" style={{ color: '#71717a' }}>
                    {item.description}
                  </p>

                  {/* Tutorial links */}
                  <div className="space-y-1.5 mb-4" onClick={e => e.stopPropagation()}>
                    <p className="text-[10px] font-bold tracking-widest uppercase mb-2" style={{ color: '#3f3f46' }}>
                      📚 Learn it
                    </p>
                    {links.map(link => (
                      <a key={link.url} href={link.url} target="_blank" rel="noopener noreferrer"
                        className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium transition-all duration-200 group"
                        style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}
                        onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.07)')}
                        onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.03)')}>
                        <span className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] shrink-0"
                          style={{ background: `${link.color}22`, border: `1px solid ${link.color}44` }}>
                          {link.icon}
                        </span>
                        <span className="flex-1 text-zinc-300 group-hover:text-white transition-colors">{link.label}</span>
                        <span className="text-zinc-700 group-hover:text-zinc-400 transition-colors text-[10px]">↗</span>
                      </a>
                    ))}
                  </div>

                  {/* Sub-task checklist */}
                  <SubTaskChecklist questIdx={index} priority={item.priority} progress={progress} />
                </motion.div>
              )}
            </AnimatePresence>

            <div className="flex items-center gap-3 mt-2 cursor-pointer">
              <span className="text-xs font-bold" style={{ color: completed ? '#34d399' : '#52525b' }}>
                {completed ? '✓ ' : ''}{xp} XP
              </span>
              <span className="text-xs" style={{ color: '#3f3f46' }}>
                {expanded ? '▲ less' : '▼ details & checklist'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

/* ── Badge component ─────────────────────────────────────────────── */
function Badge({ badge, unlocked }: { badge: (typeof ALL_BADGES)[0]; unlocked: boolean }) {
  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      whileHover={unlocked ? { scale: 1.08, y: -2 } : {}}
      className="flex flex-col items-center gap-2 p-3 rounded-2xl text-center"
      style={{
        background: unlocked ? 'rgba(96,121,248,0.1)' : 'rgba(255,255,255,0.02)',
        border: `1px solid ${unlocked ? 'rgba(96,121,248,0.35)' : 'rgba(255,255,255,0.05)'}`,
        boxShadow: unlocked ? '0 0 16px rgba(96,121,248,0.2)' : 'none',
        filter: unlocked ? 'none' : 'grayscale(1) opacity(0.3)',
      }}>
      <span className="text-2xl">{badge.icon}</span>
      <div>
        <p className="text-xs font-bold" style={{ color: unlocked ? '#a5b4fc' : '#52525b' }}>{badge.label}</p>
        <p className="text-[10px] mt-0.5" style={{ color: '#3f3f46' }}>{badge.desc}</p>
      </div>
    </motion.div>
  );
}

/* ── Main Page ───────────────────────────────────────────────────── */
export default function RoadmapPage() {
  const location   = useLocation();
  const navigate   = useNavigate();
  const { jobId }  = useParams<{ jobId: string }>();
  const result: AnalysisResult | undefined = location.state?.result;

  // Persistent progress — keyed by jobId so each analysis is independent
  const progress = useProgress(jobId ?? 'default');
  const [justUnlocked, setJustUnlocked] = useState<number | null>(null);

  if (!result) {
    return (
      <PageTransition className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-4xl mb-4">🗺️</p>
          <p className="text-zinc-400 mb-4">No roadmap data. Run an analysis first.</p>
          <button onClick={() => navigate('/')} className="btn-primary">← Start analysis</button>
        </div>
      </PageTransition>
    );
  }

  const items = result.roadmap;

  // XP & level
  const earnedXP = progress.completedQuests.reduce(
    (sum, i) => sum + (XP_PER_QUEST[items[i]?.priority] ?? 0), 0,
  );
  const lvlData = calcLevel(earnedXP);

  // Badge logic
  const unlockedBadges = new Set<string>();
  if (progress.completedCount >= 1) unlockedBadges.add('first_quest');
  if (progress.completedCount >= 3) unlockedBadges.add('half_way');
  if (progress.completedCount === items.length && items.length > 0) unlockedBadges.add('completionist');
  if (earnedXP >= 500) unlockedBadges.add('scholar');
  if (progress.completedQuests.some(i => items[i]?.priority === 'high')) unlockedBadges.add('high_roller');
  if (progress.completedCount >= 2) unlockedBadges.add('speed_runner');

  const handleToggle = (i: number) => {
    const wasCompleted = progress.isQuestDone(i);
    progress.toggleQuest(i);
    if (!wasCompleted) {
      setJustUnlocked(i);
      setTimeout(() => setJustUnlocked(null), 1800);
    }
  };

  const glass = {
    background: 'rgba(22,27,39,0.85)',
    backdropFilter: 'blur(20px)',
    border: '1px solid rgba(255,255,255,0.07)',
    boxShadow: '0 0 0 1px rgba(96,121,248,0.08), 0 16px 48px rgba(0,0,0,0.4)',
  };

  return (
    <PageTransition className="min-h-screen px-4 py-12 overflow-hidden">
      {/* BG orbs */}
      <div className="fixed inset-0 pointer-events-none">
        <motion.div className="orb w-[600px] h-[600px] bg-indigo-600/20 -top-48 -left-32"
          animate={{ scale: [1, 1.2, 1], rotate: [0, 10, 0] }}
          transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut' }} />
        <motion.div className="orb w-[400px] h-[400px] bg-violet-600/15 bottom-0 right-0"
          animate={{ scale: [1, 1.3, 1] }}
          transition={{ duration: 9, repeat: Infinity, ease: 'easeInOut', delay: 3 }} />
        <motion.div className="orb w-[250px] h-[250px] bg-amber-500/08 top-1/2 right-1/4"
          animate={{ scale: [1, 1.4, 1] }}
          transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut', delay: 1 }} />
        <div className="absolute inset-0 opacity-[0.025]"
          style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)', backgroundSize: '60px 60px' }} />
      </div>

      <div className="relative max-w-3xl mx-auto space-y-6 z-10">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }}
          className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-2xl">🗺️</span>
              <h1 className="text-3xl font-black">
                Quest{' '}
                <span style={{ background: 'linear-gradient(135deg, #e0e7ff, #818cf8, #6079f8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                  Roadmap
                </span>
              </h1>
            </div>
            <p className="text-sm" style={{ color: '#52525b' }}>
              Complete quests, tick off learning steps, earn XP — progress saves automatically
            </p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => navigate(-1)} className="btn-ghost">← Results</button>
            <button onClick={() => navigate('/')} className="btn-ghost">New analysis</button>
          </div>
        </motion.div>

        {/* Progress Dashboard (player card + dual progress bars) */}
        <ProgressDashboard
          items={items}
          progress={progress}
          earnedXP={earnedXP}
          lvlData={lvlData}
          unlockedBadges={unlockedBadges}
        />

        {/* Badges */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          className="rounded-2xl p-5" style={glass}>
          <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
            <span>🏅</span> Badges
            <span className="text-xs font-normal ml-1" style={{ color: '#52525b' }}>
              {unlockedBadges.size}/{ALL_BADGES.length} unlocked
            </span>
          </h3>
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
            {ALL_BADGES.map(b => (
              <Badge key={b.id} badge={b} unlocked={unlockedBadges.has(b.id)} />
            ))}
          </div>
        </motion.div>

        {/* Quest list */}
        <div>
          <motion.h3 initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.25 }}
            className="text-sm font-bold text-white mb-4 flex items-center gap-2">
            <span>⚔️</span> Active Quests
            <span className="text-xs font-normal" style={{ color: '#52525b' }}>
              Tap ▼ to expand · check box to complete · progress saves automatically
            </span>
          </motion.h3>
          <div className="space-y-3">
            {items.map((item, i) => (
              <QuestCard
                key={i}
                item={item}
                index={i}
                progress={progress}
                justUnlocked={justUnlocked === i}
              />
            ))}
          </div>
        </div>

        {/* Completion banner */}
        <AnimatePresence>
          {progress.completedCount === items.length && items.length > 0 && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="rounded-3xl p-8 text-center relative overflow-hidden"
              style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.35)', boxShadow: '0 0 40px rgba(16,185,129,0.15)' }}>
              <div className="absolute top-0 left-8 right-8 h-px"
                style={{ background: 'linear-gradient(90deg, transparent, rgba(16,185,129,0.8), transparent)' }} />
              <motion.div
                animate={{ scale: [1, 1.2, 1], rotate: [0, 10, -10, 0] }}
                transition={{ duration: 0.8, delay: 0.2 }}
                className="text-5xl mb-3">👑</motion.div>
              <h3 className="text-xl font-black text-white mb-1">Quest Complete!</h3>
              <p className="text-sm" style={{ color: '#6ee7b7' }}>
                You've conquered all {items.length} quests and earned {earnedXP} XP. You are a Master.
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </PageTransition>
  );
}
