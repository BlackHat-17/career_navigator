import { useState } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, Tooltip } from 'recharts';
import PageTransition from '../components/PageTransition';
import type { AnalysisResult, SkillEntry, MissingSkill } from '../types';

// ═══════════════════════════════════════════════════════════════════════════
// V1 API Adapter
// ═══════════════════════════════════════════════════════════════════════════

interface V1SkillDetail {
  name: string;
  confidence?: number;
  evidence: string[];
}

interface V1AnalysisResult {
  analysis_id: string;
  status: string;
  candidate: { user_id: string };
  skills: {
    verified: V1SkillDetail[];
    partial: V1SkillDetail[];
    missing: V1SkillDetail[];
  };
  evidence: any[];
  projects: {
    existing: any[];
    recommended: any[];
  };
  roadmap: any[];
  summary: {
    skill_match: number;
    major_gaps: string[];
  };
}

/**
 * Adapts v1 API response format to the format expected by ResultsPage UI.
 * Maps:
 * - verified_skills → evidenced (with evidence)
 * - partial_skills → claimed (without full evidence)
 * - missing_skills → missing (with why explanation)
 * - roadmap items → UI roadmap format with priority
 */
function adaptV1ToLegacyFormat(v1Result: V1AnalysisResult): AnalysisResult {
  // Map verified skills to "evidenced" category
  const evidenced: SkillEntry[] = v1Result.skills.verified.map(skill => ({
    skill: skill.name,
    evidence: skill.evidence.length > 0 
      ? skill.evidence.join(' • ') 
      : `Verified with ${Math.round((skill.confidence || 0) * 100)}% confidence`,
  }));

  // Map partial skills to "claimed" category
  const claimed: SkillEntry[] = v1Result.skills.partial.map(skill => ({
    skill: skill.name,
    evidence: skill.evidence.length > 0
      ? `Partial evidence: ${skill.evidence.join(' • ')}`
      : 'Claimed on resume but limited code evidence',
  }));

  // Map missing skills to "missing" category
  const missing: MissingSkill[] = v1Result.skills.missing.map(skill => ({
    skill: skill.name,
    why: skill.evidence.length > 0
      ? skill.evidence.join(' • ')
      : 'Required for target role but not found in profile',
  }));

  // Map roadmap items (v1 may have different format, handle gracefully)
  const roadmap = v1Result.roadmap.map((item: any) => ({
    title: item.title || item.skill || item.name || 'Skill Development',
    description: item.description || item.reason || item.why || 'Focus on building this skill',
    priority: (item.priority || 'medium') as 'high' | 'medium' | 'low',
  }));

  // Generate summary text from v1 summary object
  const summary = `You match ${Math.round(v1Result.summary.skill_match)}% of the target role requirements. ${
    v1Result.summary.major_gaps.length > 0
      ? `Key gaps to address: ${v1Result.summary.major_gaps.join(', ')}.`
      : 'Strong alignment with the role!'
  }`;

  return {
    claimed,
    evidenced,
    missing,
    roadmap,
    summary,
  };
}

const PRIORITY: Record<string, { bg: string; border: string; color: string; dot: string }> = {
  high:   { bg: 'rgba(244,63,94,0.1)',   border: 'rgba(244,63,94,0.3)',   color: '#fda4af', dot: '#f43f5e' },
  medium: { bg: 'rgba(245,158,11,0.1)',  border: 'rgba(245,158,11,0.3)',  color: '#fcd34d', dot: '#f59e0b' },
  low:    { bg: 'rgba(16,185,129,0.1)',  border: 'rgba(16,185,129,0.3)',  color: '#6ee7b7', dot: '#10b981' },
};

const XP_MAP: Record<string, number> = { high: 500, medium: 300, low: 150 };

function Ring({ value, max, color, glow, label }: { value: number; max: number; color: string; glow: string; label: string }) {
  const r = 28; const c = 2 * Math.PI * r;
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative w-16 h-16">
        <svg className="w-16 h-16 -rotate-90" viewBox="0 0 64 64">
          <circle cx="32" cy="32" r={r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="5" />
          <motion.circle cx="32" cy="32" r={r} fill="none" stroke={color} strokeWidth="5" strokeLinecap="round"
            strokeDasharray={c} initial={{ strokeDashoffset: c }}
            animate={{ strokeDashoffset: c * (1 - Math.min(value / Math.max(max, 1), 1)) }}
            transition={{ duration: 1.1, delay: 0.3, ease: 'easeOut' }}
            style={{ filter: `drop-shadow(0 0 6px ${glow})` }} />
        </svg>
        <motion.div initial={{ opacity: 0, scale: 0.5 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.7 }}
          className="absolute inset-0 flex items-center justify-center">
          <span className="text-lg font-black" style={{ color }}>{value}</span>
        </motion.div>
      </div>
      <span className="text-xs font-medium" style={{ color: '#71717a' }}>{label}</span>
    </div>
  );
}

function SkillModal({ skill, detail, onClose }: { skill: string; detail: string; onClose: () => void }) {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center px-4" onClick={onClose}>
      <div className="absolute inset-0" style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(12px)' }} />
      <motion.div initial={{ scale: 0.88, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.88, y: 20 }}
        transition={{ type: 'spring', stiffness: 260, damping: 22 }}
        className="relative max-w-sm w-full rounded-2xl p-6"
        style={{ background: 'rgba(22,27,39,0.95)', border: '1px solid rgba(255,255,255,0.1)', boxShadow: '0 0 0 1px rgba(96,121,248,0.15), 0 32px 64px rgba(0,0,0,0.6)' }}
        onClick={e => e.stopPropagation()}>
        <div className="absolute top-0 left-6 right-6 h-px"
          style={{ background: 'linear-gradient(90deg, transparent, rgba(96,121,248,0.5), transparent)' }} />
        <div className="flex items-start justify-between mb-3">
          <h3 className="font-bold text-white">{skill}</h3>
          <button onClick={onClose} className="w-7 h-7 rounded-full flex items-center justify-center text-xs transition-all ml-4 shrink-0"
            style={{ background: 'rgba(255,255,255,0.07)', color: '#71717a' }}>✕</button>
        </div>
        <p className="text-sm leading-relaxed" style={{ color: '#a1a1aa' }}>{detail}</p>
      </motion.div>
    </motion.div>
  );
}

function Chip({ label, variant, detail, delay }: { label: string; variant: string; detail: string; delay: number }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <motion.button initial={{ opacity: 0, scale: 0.75 }} animate={{ opacity: 1, scale: 1 }}
        transition={{ delay, type: 'spring', stiffness: 200, damping: 18 }}
        onClick={() => setOpen(true)} className={`skill-chip-${variant}`}>{label}</motion.button>
      <AnimatePresence>
        {open && <SkillModal skill={label} detail={detail} onClose={() => setOpen(false)} />}
      </AnimatePresence>
    </>
  );
}

const COLS = [
  { key: 'claimed',   title: 'Claimed',          icon: '📋', color: '#fcd34d', border: 'rgba(245,158,11,0.2)',  bg: 'rgba(245,158,11,0.04)',  variant: 'claimed'   },
  { key: 'evidenced', title: 'Evidenced in code', icon: '✅', color: '#6ee7b7', border: 'rgba(16,185,129,0.2)', bg: 'rgba(16,185,129,0.04)', variant: 'evidenced' },
  { key: 'missing',   title: 'Missing for role',  icon: '⚠️', color: '#fda4af', border: 'rgba(244,63,94,0.2)',  bg: 'rgba(244,63,94,0.04)',  variant: 'missing'   },
];

export default function ResultsPage() {
  const { jobId }  = useParams<{ jobId: string }>();
  const location   = useLocation();
  const navigate   = useNavigate();
  const rawResult = location.state?.result;

  // Detect if we received v1 format (has analysis_id and skills object)
  let result: AnalysisResult | undefined;
  if (rawResult) {
    if ('analysis_id' in rawResult && 'skills' in rawResult) {
      // V1 format - adapt it
      result = adaptV1ToLegacyFormat(rawResult as V1AnalysisResult);
    } else {
      // Legacy format - use as-is
      result = rawResult as AnalysisResult;
    }
  }

  if (!result) {
    return (
      <PageTransition className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-zinc-400 mb-4">No results for job <code className="text-xs font-mono">{jobId}</code></p>
          <button onClick={() => navigate('/')} className="btn-primary">← Start over</button>
        </div>
      </PageTransition>
    );
  }

  const total = result.claimed.length + result.evidenced.length + result.missing.length;
  const score = total > 0 ? Math.round(((result.claimed.length + result.evidenced.length * 2) / (total * 2)) * 100) : 0;
  const radarData = [
    { category: 'Claimed',   value: result.claimed.length },
    { category: 'Evidenced', value: result.evidenced.length },
    { category: 'Missing',   value: result.missing.length },
  ];

  const glass = {
    background: 'rgba(22,27,39,0.8)',
    backdropFilter: 'blur(20px)',
    border: '1px solid rgba(255,255,255,0.07)',
    boxShadow: '0 0 0 1px rgba(96,121,248,0.08), 0 16px 48px rgba(0,0,0,0.4)',
  };

  return (
    <PageTransition className="min-h-screen px-4 py-12 overflow-hidden">
      {/* BG */}
      <div className="fixed inset-0 pointer-events-none">
        <motion.div className="orb w-[500px] h-[500px] bg-indigo-600/15 -top-40 right-0"
          animate={{ scale: [1,1.15,1] }} transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut' }} />
        <motion.div className="orb w-[400px] h-[400px] bg-violet-600/10 bottom-0 -left-24"
          animate={{ scale: [1,1.2,1] }} transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut', delay: 3 }} />
        <div className="absolute inset-0 opacity-[0.025]"
          style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)', backgroundSize: '60px 60px' }} />
      </div>

      <div className="relative max-w-5xl mx-auto space-y-6 z-10">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }}
          className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-4xl font-black">
              Your skill{' '}
              <span style={{ background: 'linear-gradient(135deg, #e0e7ff, #818cf8, #6079f8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                profile
              </span>
            </h1>
            <p className="text-sm mt-2 max-w-xl leading-relaxed" style={{ color: '#71717a' }}>{result.summary}</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => navigate('/')} className="btn-ghost shrink-0">← New analysis</button>
          </div>
        </motion.div>

        {/* Score card */}
        <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.1 }}
          className="rounded-3xl p-6 relative overflow-hidden" style={glass}>
          <div className="absolute top-0 left-8 right-8 h-px"
            style={{ background: 'linear-gradient(90deg, transparent, rgba(96,121,248,0.5), rgba(167,139,250,0.5), transparent)' }} />
          <div className="flex flex-col sm:flex-row items-center gap-8">
            {/* Big ring */}
            <div className="flex flex-col items-center gap-2 shrink-0">
              <div className="relative w-32 h-32">
                <svg className="w-32 h-32 -rotate-90" viewBox="0 0 128 128">
                  <circle cx="64" cy="64" r="54" fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="8" />
                  <motion.circle cx="64" cy="64" r="54" fill="none" stroke="url(#sg)" strokeWidth="8" strokeLinecap="round"
                    strokeDasharray={339} initial={{ strokeDashoffset: 339 }}
                    animate={{ strokeDashoffset: 339 * (1 - score / 100) }}
                    transition={{ duration: 1.6, delay: 0.2, ease: 'easeOut' }}
                    style={{ filter: 'drop-shadow(0 0 10px rgba(96,121,248,0.6))' }} />
                  <defs>
                    <linearGradient id="sg" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="#6079f8" /><stop offset="100%" stopColor="#a78bfa" />
                    </linearGradient>
                  </defs>
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <motion.span initial={{ opacity: 0, scale: 0.5 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.9, type: 'spring', stiffness: 200 }}
                    className="text-4xl font-black"
                    style={{ background: 'linear-gradient(135deg, #a5b4fc, #6079f8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                    {score}
                  </motion.span>
                  <span className="text-xs" style={{ color: '#52525b' }}>/ 100</span>
                </div>
              </div>
              <span className="text-xs font-semibold tracking-widest uppercase" style={{ color: '#52525b' }}>Readiness</span>
            </div>

            <div className="flex-1 space-y-5 w-full">
              {/* Sub-rings */}
              <div className="flex gap-8 justify-center sm:justify-start">
                <Ring value={result.claimed.length}   max={total} color="#fcd34d" glow="rgba(245,158,11,0.4)"  label="Claimed"   />
                <Ring value={result.evidenced.length} max={total} color="#6ee7b7" glow="rgba(16,185,129,0.4)"  label="Evidenced" />
                <Ring value={result.missing.length}   max={total} color="#fda4af" glow="rgba(244,63,94,0.4)"   label="Missing"   />
              </div>

              {/* Bar */}
              <div>
                <div className="flex h-2 rounded-full overflow-hidden gap-px">
                  <motion.div initial={{ width: 0 }} animate={{ width: `${(result.evidenced.length / Math.max(total,1)) * 100}%` }}
                    transition={{ duration: 1, delay: 0.5 }} className="h-full rounded-l-full" style={{ background: '#10b981' }} />
                  <motion.div initial={{ width: 0 }} animate={{ width: `${(result.claimed.length / Math.max(total,1)) * 100}%` }}
                    transition={{ duration: 1, delay: 0.6 }} className="h-full" style={{ background: '#f59e0b' }} />
                  <motion.div initial={{ width: 0 }} animate={{ width: `${(result.missing.length / Math.max(total,1)) * 100}%` }}
                    transition={{ duration: 1, delay: 0.7 }} className="h-full rounded-r-full" style={{ background: 'rgba(244,63,94,0.5)' }} />
                </div>
                <div className="flex gap-5 mt-2">
                  {[['#10b981','Evidenced'],['#f59e0b','Claimed'],['rgba(244,63,94,0.7)','Missing']].map(([c,l]) => (
                    <div key={l} className="flex items-center gap-1.5 text-xs" style={{ color: '#52525b' }}>
                      <span className="w-2 h-2 rounded-full shrink-0" style={{ background: c }} />{l}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Skill columns */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {COLS.map((col, ci) => {
            const items: (SkillEntry | MissingSkill)[] = col.key === 'claimed' ? result.claimed : col.key === 'evidenced' ? result.evidenced : result.missing;
            return (
              <motion.div key={col.key} initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 * ci }}
                className="rounded-2xl p-5"
                style={{ background: col.bg, border: `1px solid ${col.border}`, backdropFilter: 'blur(10px)' }}>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <span>{col.icon}</span>
                    <span className="text-sm font-bold" style={{ color: col.color }}>{col.title}</span>
                  </div>
                  <span className="text-xs font-bold px-2 py-0.5 rounded-full" style={{ background: `${col.border}`, color: col.color }}>
                    {items.length}
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {items.map((s, i) => (
                    <Chip key={s.skill} label={s.skill}
                      variant={col.variant}
                      detail={'evidence' in s ? s.evidence : s.why}
                      delay={0.04 * i} />
                  ))}
                  {items.length === 0 && (
                    <p className="text-xs italic" style={{ color: '#3f3f46' }}>
                      {col.key === 'missing' ? 'No critical gaps 🎉' : 'None found'}
                    </p>
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* Radar + Roadmap */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <motion.div initial={{ opacity: 0, x: -24 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 }}
            className="rounded-2xl p-5" style={glass}>
            <h3 className="text-sm font-bold text-white mb-1">Skill distribution</h3>
            <p className="text-xs mb-4" style={{ color: '#52525b' }}>Relative breakdown across categories</p>
            <ResponsiveContainer width="100%" height={220}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="rgba(255,255,255,0.05)" />
                <PolarAngleAxis dataKey="category" tick={{ fill: '#52525b', fontSize: 11, fontWeight: 600 }} />
                <Radar name="Skills" dataKey="value" stroke="#6079f8" fill="#6079f8" fillOpacity={0.18} strokeWidth={2}
                  style={{ filter: 'drop-shadow(0 0 6px rgba(96,121,248,0.5))' }} />
                <Tooltip contentStyle={{ background: '#0a0b0f', border: '1px solid rgba(96,121,248,0.2)', borderRadius: 12, fontSize: 12 }}
                  labelStyle={{ color: '#fff', fontWeight: 600 }} itemStyle={{ color: '#818cf8' }} />
              </RadarChart>
            </ResponsiveContainer>
          </motion.div>

          <motion.div initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.4 }}
            className="rounded-2xl p-5" style={glass}>
            <h3 className="text-sm font-bold text-white mb-1">Growth roadmap</h3>
            <p className="text-xs mb-5" style={{ color: '#52525b' }}>Prioritised steps to close your gaps</p>
            <div className="space-y-4">
              {result.roadmap.map((item, i) => {
                const p = PRIORITY[item.priority] ?? PRIORITY.low;
                return (
                  <motion.div key={i} initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.06 * i + 0.5 }}
                    className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.06 * i + 0.6, type: 'spring', stiffness: 250 }}
                        className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-black shrink-0"
                        style={{ background: 'rgba(96,121,248,0.15)', border: '1px solid rgba(96,121,248,0.35)', color: '#818cf8', boxShadow: '0 0 12px rgba(96,121,248,0.2)' }}>
                        {i + 1}
                      </motion.div>
                      {i < result.roadmap.length - 1 && (
                        <div className="w-px flex-1 mt-1" style={{ background: 'linear-gradient(to bottom, rgba(96,121,248,0.25), transparent)' }} />
                      )}
                    </div>
                    <div className="pb-4">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-semibold text-white">{item.title}</span>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1"
                          style={{ background: p.bg, border: `1px solid ${p.border}`, color: p.color }}>
                          <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: p.dot }} />
                          {item.priority}
                        </span>
                      </div>
                      <p className="text-xs leading-relaxed" style={{ color: '#71717a' }}>{item.description}</p>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        </div>

        {/* ── Big Quest Roadmap CTA ── */}
        <motion.div
          initial={{ opacity: 0, y: 32 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, type: 'spring', stiffness: 100, damping: 18 }}
          className="relative rounded-3xl p-8 text-center overflow-hidden"
          style={{
            background: 'linear-gradient(135deg, rgba(96,121,248,0.12) 0%, rgba(167,139,250,0.12) 100%)',
            border: '1px solid rgba(96,121,248,0.3)',
            backdropFilter: 'blur(20px)',
            boxShadow: '0 0 60px rgba(96,121,248,0.12), 0 16px 48px rgba(0,0,0,0.4)',
          }}>
          {/* Top glow */}
          <div className="absolute top-0 left-12 right-12 h-px"
            style={{ background: 'linear-gradient(90deg, transparent, rgba(167,139,250,0.8), rgba(96,121,248,0.8), transparent)' }} />
          {/* Floating orb */}
          <motion.div className="absolute -top-16 -right-16 w-48 h-48 rounded-full pointer-events-none"
            style={{ background: 'radial-gradient(circle, rgba(167,139,250,0.15), transparent)', filter: 'blur(30px)' }}
            animate={{ scale: [1, 1.3, 1] }} transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }} />

          <motion.div className="text-5xl mb-4" animate={{ y: [0, -6, 0], rotate: [0, 5, -5, 0] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}>🗺️</motion.div>

          <h3 className="text-2xl font-black text-white mb-2">Ready to level up?</h3>
          <p className="text-sm mb-6 max-w-sm mx-auto" style={{ color: '#a1a1aa' }}>
            Turn your roadmap into an interactive quest — earn XP, unlock badges, and get direct tutorial links for every skill gap.
          </p>

          {/* XP preview pills */}
          <div className="flex flex-wrap justify-center gap-2 mb-6">
            {result.roadmap.slice(0, 3).map((item, i) => (
              <span key={i} className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold"
                style={{
                  background: 'rgba(255,255,255,0.06)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  color: '#a1a1aa',
                }}>
                {item.priority === 'high' ? '🔥' : item.priority === 'medium' ? '⚡' : '🌱'}
                {item.title.length > 28 ? item.title.slice(0, 28) + '…' : item.title}
                <span className="font-black" style={{ color: '#818cf8' }}>+{XP_MAP[item.priority]}xp</span>
              </span>
            ))}
            {result.roadmap.length > 3 && (
              <span className="px-3 py-1 rounded-full text-xs" style={{ color: '#52525b', border: '1px solid rgba(255,255,255,0.06)' }}>
                +{result.roadmap.length - 3} more quests
              </span>
            )}
          </div>

          <motion.button
            onClick={() => navigate(`/roadmap/${jobId}`, { state: { result } })}
            whileHover={{ scale: 1.03, boxShadow: '0 0 48px rgba(96,121,248,0.6), 0 8px 32px rgba(0,0,0,0.4)' }}
            whileTap={{ scale: 0.97 }}
            className="relative inline-flex items-center gap-3 px-8 py-4 rounded-2xl font-black text-base text-white overflow-hidden"
            style={{
              background: 'linear-gradient(135deg, #4455f0, #6079f8, #818cf8)',
              boxShadow: '0 0 32px rgba(96,121,248,0.45), 0 8px 24px rgba(0,0,0,0.4)',
            }}>
            {/* Shimmer */}
            <motion.span className="absolute inset-0 pointer-events-none"
              animate={{ x: ['-100%', '200%'] }} transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut', repeatDelay: 1 }}
              style={{ background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent)', width: '50%' }} />
            <span className="relative flex items-center gap-3">
              <span className="text-xl">⚔️</span>
              Start Quest Roadmap
              <motion.span animate={{ x: [0, 5, 0] }} transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}>→</motion.span>
            </span>
          </motion.button>

          <p className="text-xs mt-4" style={{ color: '#3f3f46' }}>
            {result.roadmap.length} quests · up to {result.roadmap.reduce((s, i) => s + (XP_MAP[i.priority] ?? 0), 0)} XP · includes tutorial links
          </p>
        </motion.div>

      </div>
    </PageTransition>
  );
}
