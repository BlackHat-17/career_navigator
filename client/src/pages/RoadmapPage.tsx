import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import PageTransition from '../components/PageTransition';
import type { AnalysisResult, RoadmapItem, RoadmapSkill } from '../types';

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
  if (xp < 300)  return { level: 1, title: 'Novice',      color: '#71717a', next: 300  };
  if (xp < 700)  return { level: 2, title: 'Apprentice',  color: '#6079f8', next: 700  };
  if (xp < 1200) return { level: 3, title: 'Practitioner',color: '#a78bfa', next: 1200 };
  if (xp < 1800) return { level: 4, title: 'Expert',      color: '#f59e0b', next: 1800 };
  return               { level: 5, title: 'Master',       color: '#10b981', next: 2500 };
}

/* ── Badges ──────────────────────────────────────────────────────── */
const ALL_BADGES = [
  { id: 'first_quest',   icon: '🎯', label: 'First Quest',    desc: 'Complete your first task',         unlockAt: 1  },
  { id: 'half_way',      icon: '⚡', label: 'Momentum',       desc: 'Complete 3 quests',                unlockAt: 3  },
  { id: 'high_roller',   icon: '🔥', label: 'High Priority',  desc: 'Complete a high-priority quest',   unlockAt: -1 },
  { id: 'completionist', icon: '👑', label: 'Completionist',  desc: 'Complete all quests',              unlockAt: 99 },
  { id: 'speed_runner',  icon: '💨', label: 'Speed Runner',   desc: 'Complete 2 quests in one session', unlockAt: -2 },
  { id: 'scholar',       icon: '📚', label: 'Scholar',        desc: '500 XP earned',                    unlockAt: -3 },
];

/* ── Priority config ─────────────────────────────────────────────── */
const P: Record<string, { label: string; color: string; border: string; bg: string; glow: string; icon: string }> = {
  high:   { label: 'HIGH',   color: '#fda4af', border: 'rgba(244,63,94,0.35)',   bg: 'rgba(244,63,94,0.08)',   glow: 'rgba(244,63,94,0.3)',   icon: '🔥' },
  medium: { label: 'MEDIUM', color: '#fcd34d', border: 'rgba(245,158,11,0.35)',  bg: 'rgba(245,158,11,0.08)',  glow: 'rgba(245,158,11,0.3)',  icon: '⚡' },
  low:    { label: 'LOW',    color: '#6ee7b7', border: 'rgba(16,185,129,0.35)',  bg: 'rgba(16,185,129,0.08)',  glow: 'rgba(16,185,129,0.3)',  icon: '🌱' },
};

/* ── Quest card ──────────────────────────────────────────────────── */
function QuestCard({
  item, index, completed, onToggle, justUnlocked,
}: {
  item: RoadmapItem; index: number; completed: boolean; onToggle: () => void; justUnlocked: boolean;
}) {
  const p  = P[item.priority] ?? P.low;
  const xp = XP_PER_QUEST[item.priority] ?? 150;
  const [expanded, setExpanded] = useState(false);
  const links = getTutorialLinks(item.title, item.description);

  return (
    <motion.div
      initial={{ opacity: 0, y: 32 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, type: 'spring', stiffness: 120, damping: 18 }}
      className="relative rounded-2xl overflow-hidden cursor-pointer"
      style={{
        background: completed ? 'rgba(16,185,129,0.08)' : 'rgba(22,27,39,0.85)',
        border: `1px solid ${completed ? 'rgba(16,185,129,0.35)' : p.border}`,
        backdropFilter: 'blur(16px)',
        boxShadow: completed ? '0 0 20px rgba(16,185,129,0.1)' : `0 0 0 1px rgba(0,0,0,0.2), 0 8px 32px rgba(0,0,0,0.3)`,
        opacity: completed ? 0.75 : 1,
      }}
      onClick={() => setExpanded(e => !e)}
    >
      {/* Top glow line */}
      {!completed && (
        <div className="absolute top-0 left-4 right-4 h-px"
          style={{ background: `linear-gradient(90deg, transparent, ${p.color}, transparent)`, opacity: 0.6 }} />
      )}

      {/* XP unlock flash */}
      <AnimatePresence>
        {justUnlocked && (
          <motion.div initial={{ opacity: 0, scale: 0.5, y: 10 }} animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }} transition={{ duration: 0.4 }}
            className="absolute top-3 right-14 text-xs font-black px-2 py-1 rounded-full z-10"
            style={{ background: 'rgba(16,185,129,0.9)', color: '#fff' }}>
            +{xp} XP!
          </motion.div>
        )}
      </AnimatePresence>

      <div className="p-5">
        <div className="flex items-start gap-4">
          {/* Quest number / check */}
          <motion.button
            onClick={e => { e.stopPropagation(); onToggle(); }}
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

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <span className={`text-sm font-bold ${completed ? 'line-through opacity-50' : 'text-white'}`}>
                {item.title}
              </span>
              <span className="text-[10px] font-black px-2 py-0.5 rounded-full tracking-wider"
                style={{ background: p.bg, border: `1px solid ${p.border}`, color: p.color }}>
                {p.icon} {p.label}
              </span>
            </div>

            <AnimatePresence>
              {expanded && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }}
                  className="overflow-hidden">
                  <p className="text-xs leading-relaxed mb-3" style={{ color: '#71717a' }}>
                    {item.description}
                  </p>
                  {/* Tutorial links */}
                  <div className="space-y-1.5" onClick={e => e.stopPropagation()}>
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
                </motion.div>
              )}
            </AnimatePresence>

            <div className="flex items-center gap-3 mt-1">
              <span className="text-xs font-bold" style={{ color: completed ? '#34d399' : '#52525b' }}>
                {completed ? '✓ ' : ''}{xp} XP
              </span>
              <span className="text-xs" style={{ color: '#3f3f46' }}>
                {expanded ? '▲ less' : '▼ details'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

/* ── Badge component ─────────────────────────────────────────────── */
function Badge({ badge, unlocked }: { badge: typeof ALL_BADGES[0]; unlocked: boolean }) {
  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      whileHover={unlocked ? { scale: 1.08, y: -2 } : {}}
      className="flex flex-col items-center gap-2 p-3 rounded-2xl text-center transition-all duration-200"
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

function SkillRoadmapCard({ skill }: { skill: RoadmapSkill }) {
  const classificationLabel = skill.classification === 'missing' ? 'Missing skill' : 'Partial skill';
  const stateLabel = skill.state.replace(/_/g, ' ');

  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-white/10 bg-slate-900/80 p-5"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-indigo-300">{classificationLabel}</p>
          <h3 className="mt-2 text-xl font-bold text-white">{skill.name}</h3>
        </div>
        <span className="rounded-full border border-indigo-400/30 bg-indigo-500/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-200">
          {stateLabel}
        </span>
      </div>

      {skill.learning_track && skill.learning_track.length > 0 && (
        <div className="mt-4 space-y-3">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-400">Learning track</p>
          {skill.learning_track.map((level) => (
            <div key={`${skill.name}-${level.level_number}`} className="rounded-xl border border-white/5 bg-slate-950/40 p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="font-semibold text-white">Level {level.level_number}: {level.title}</p>
                <span className="text-[10px] uppercase text-zinc-400">{level.completion_status}</span>
              </div>
              <p className="mt-2 text-sm text-zinc-300">{level.objective}</p>
              {level.resources && level.resources.length > 0 && (
                <ul className="mt-2 space-y-1 text-xs text-zinc-400">
                  {level.resources.slice(0, 3).map((resource, idx) => (
                    <li key={`${resource.title}-${idx}`}>• {resource.title}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}

      {skill.mini_project && (
        <div className="mt-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300">Mini project</p>
          <h4 className="mt-2 font-semibold text-white">{skill.mini_project.title}</h4>
          <p className="mt-2 text-sm text-zinc-300">{skill.mini_project.description}</p>
        </div>
      )}

      {skill.assessment && (
        <div className="mt-4 rounded-xl border border-amber-500/20 bg-amber-500/5 p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-amber-300">Assessment</p>
          <div className="mt-2 flex items-center gap-3">
            <span className="text-lg font-bold text-white">{skill.assessment.score ?? 0}%</span>
            <span className="rounded-full border border-amber-400/30 bg-amber-500/10 px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-amber-200">
              {skill.assessment.passed === true ? 'Passed' : skill.assessment.passed === false ? 'Needs review' : 'Pending'}
            </span>
          </div>
          {skill.assessment.feedback && (
            <p className="mt-2 text-sm text-zinc-300">{skill.assessment.feedback}</p>
          )}
        </div>
      )}
    </motion.div>
  );
}

/* ── Main ────────────────────────────────────────────────────────── */
export default function RoadmapPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const result: AnalysisResult | undefined = location.state?.result;

  const [completed, setCompleted] = useState<Set<number>>(new Set());
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

  const skillRoadmap = result.skills && result.skills.length > 0 ? result.skills : null;

  if (skillRoadmap) {
    return (
      <PageTransition className="min-h-screen px-4 py-12 overflow-hidden">
        <div className="fixed inset-0 pointer-events-none">
          <motion.div className="orb w-[600px] h-[600px] bg-indigo-600/20 -top-48 -left-32"
            animate={{ scale: [1,1.2,1], rotate: [0,10,0] }} transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut' }} />
          <motion.div className="orb w-[400px] h-[400px] bg-violet-600/15 bottom-0 right-0"
            animate={{ scale: [1,1.3,1] }} transition={{ duration: 9, repeat: Infinity, ease: 'easeInOut', delay: 3 }} />
          <div className="absolute inset-0 opacity-[0.025]"
            style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)', backgroundSize: '60px 60px' }} />
        </div>

        <div className="relative mx-auto max-w-4xl space-y-6 z-10">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-indigo-300">Roadmap</p>
              <h1 className="mt-2 text-3xl font-black text-white">Skill learning path</h1>
            </div>
            <button onClick={() => navigate(-1)} className="btn-ghost">← Results</button>
          </div>

          <div className="rounded-3xl border border-white/10 bg-slate-900/80 p-6">
            <p className="text-sm text-zinc-300">
              This roadmap begins after upstream skill classification. Missing skills follow a learning track, while partial skills begin with a focused mini-project and assessment.
            </p>
          </div>

          <div className="space-y-4">
            {skillRoadmap.map((skill) => (
              <SkillRoadmapCard key={skill.name} skill={skill} />
            ))}
          </div>
        </div>
      </PageTransition>
    );
  }

  const items = result.roadmap;
  const earnedXP = [...completed].reduce((sum, i) => sum + (XP_PER_QUEST[items[i]?.priority] ?? 0), 0);
  const lvlData  = calcLevel(earnedXP);
  const completedCount = completed.size;

  // Badge unlock logic
  const unlockedBadges = new Set<string>();
  if (completedCount >= 1) unlockedBadges.add('first_quest');
  if (completedCount >= 3) unlockedBadges.add('half_way');
  if (completedCount === items.length) unlockedBadges.add('completionist');
  if (earnedXP >= 500) unlockedBadges.add('scholar');
  if ([...completed].some(i => items[i]?.priority === 'high')) unlockedBadges.add('high_roller');
  if (completedCount >= 2) unlockedBadges.add('speed_runner');

  const handleToggle = (i: number) => {
    setCompleted(prev => {
      const next = new Set(prev);
      if (next.has(i)) { next.delete(i); return next; }
      next.add(i);
      setJustUnlocked(i);
      setTimeout(() => setJustUnlocked(null), 1800);
      return next;
    });
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
          animate={{ scale: [1,1.2,1], rotate: [0,10,0] }} transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut' }} />
        <motion.div className="orb w-[400px] h-[400px] bg-violet-600/15 bottom-0 right-0"
          animate={{ scale: [1,1.3,1] }} transition={{ duration: 9, repeat: Infinity, ease: 'easeInOut', delay: 3 }} />
        <motion.div className="orb w-[250px] h-[250px] bg-amber-500/08 top-1/2 right-1/4"
          animate={{ scale: [1,1.4,1] }} transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut', delay: 1 }} />
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
            <p className="text-sm" style={{ color: '#52525b' }}>Complete quests to level up your skills and earn XP</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => navigate(-1)} className="btn-ghost">← Results</button>
            <button onClick={() => navigate('/')} className="btn-ghost">New analysis</button>
          </div>
        </motion.div>

        {/* Player card */}
        <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.1 }}
          className="rounded-3xl p-6 relative overflow-hidden" style={glass}>
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
              <div className="flex items-center gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-black text-white">Level {lvlData.level}</span>
                    <span className="text-xs font-bold px-2 py-0.5 rounded-full"
                      style={{ background: `${lvlData.color}22`, border: `1px solid ${lvlData.color}44`, color: lvlData.color }}>
                      {lvlData.title}
                    </span>
                  </div>
                  <p className="text-xs mt-0.5" style={{ color: '#52525b' }}>
                    {earnedXP} XP · {lvlData.next - earnedXP} XP to Level {lvlData.level + 1}
                  </p>
                </div>
              </div>

              {/* XP bar */}
              <div>
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
              </div>

              {/* Stats row */}
              <div className="flex gap-5">
                {[
                  { label: 'Quests done', value: `${completedCount}/${items.length}` },
                  { label: 'XP earned',   value: earnedXP },
                  { label: 'Badges',      value: unlockedBadges.size },
                ].map(s => (
                  <div key={s.label}>
                    <div className="text-base font-black text-white">{s.value}</div>
                    <div className="text-[10px] mt-0.5" style={{ color: '#52525b' }}>{s.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </motion.div>

        {/* Badges */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          className="rounded-2xl p-5" style={glass}>
          <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
            <span>🏅</span> Badges
            <span className="text-xs font-normal ml-1" style={{ color: '#52525b' }}>{unlockedBadges.size}/{ALL_BADGES.length} unlocked</span>
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
            <span className="text-xs font-normal" style={{ color: '#52525b' }}>Click to expand · checkbox to complete</span>
          </motion.h3>
          <div className="space-y-3">
            {items.map((item, i) => (
              <QuestCard key={i} item={item} index={i}
                completed={completed.has(i)}
                onToggle={() => handleToggle(i)}
                justUnlocked={justUnlocked === i} />
            ))}
          </div>
        </div>

        {/* Completion banner */}
        <AnimatePresence>
          {completedCount === items.length && items.length > 0 && (
            <motion.div initial={{ opacity: 0, scale: 0.9, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="rounded-3xl p-8 text-center relative overflow-hidden"
              style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.35)', boxShadow: '0 0 40px rgba(16,185,129,0.15)' }}>
              <div className="absolute top-0 left-8 right-8 h-px"
                style={{ background: 'linear-gradient(90deg, transparent, rgba(16,185,129,0.8), transparent)' }} />
              <motion.div animate={{ scale: [1, 1.2, 1], rotate: [0, 10, -10, 0] }} transition={{ duration: 0.8, delay: 0.2 }}
                className="text-5xl mb-3">👑</motion.div>
              <h3 className="text-xl font-black text-white mb-1">Quest Complete!</h3>
              <p className="text-sm" style={{ color: '#6ee7b7' }}>You've conquered all {items.length} quests and earned {earnedXP} XP. You are a Master.</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </PageTransition>
  );
}
