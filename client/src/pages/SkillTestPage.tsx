import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';

// ─── Types ───────────────────────────────────────────────────────────────────
interface MCQOption { id: string; text: string }
interface TestQuestion {
  id: string; skill: string; skill_category: string; difficulty: string;
  question: string; options: MCQOption[]; time_limit_secs: number;
}
interface SkillTestSession {
  session_id: string; questions: TestQuestion[];
  total_questions: number; time_limit_total_secs: number; instructions: string[];
}
interface AntiCheatEvent {
  event_type: string; timestamp_ms: number; question_id?: string;
}
interface SkillScore {
  skill: string; skill_category: string; questions_asked: number;
  correct: number; score_pct: number; verdict: string; verdict_color: string;
  recommended_resources: string[];
}
interface SkillTestResult {
  session_id: string; overall_score_pct: number; overall_verdict: string;
  skill_scores: SkillScore[]; verified_count: number; partial_count: number;
  needs_work_count: number;
  integrity: { tab_switches: number; focus_losses: number; copy_attempts: number; paste_attempts: number; integrity_score: number; integrity_label: string };
  learning_priorities: string[]; next_steps: string[];
}

type Phase = 'instructions' | 'testing' | 'submitting' | 'results';

// ─── Anti-cheat hook ─────────────────────────────────────────────────────────
function useAntiCheat(active: boolean, currentQId: string | undefined) {
  const events = useRef<AntiCheatEvent[]>([]);
  const violations = useRef(0);
  const [warningMsg, setWarningMsg] = useState('');

  const record = useCallback((type: string) => {
    violations.current += 1;
    events.current.push({ event_type: type, timestamp_ms: Date.now(), question_id: currentQId });
    const msgs: Record<string, string> = {
      tab_switch: '⚠️ Tab switch detected and recorded!',
      focus_loss: '⚠️ Window lost focus — recorded!',
      copy_attempt: '⚠️ Copy is disabled during the test!',
      paste_attempt: '⚠️ Paste is disabled during the test!',
    };
    setWarningMsg(msgs[type] || '⚠️ Action recorded!');
    setTimeout(() => setWarningMsg(''), 3000);
  }, [currentQId]);

  useEffect(() => {
    if (!active) return;

    const onVisibility = () => {
      if (document.hidden) record('tab_switch');
    };
    const onBlur = () => record('focus_loss');
    const onCopy = (e: ClipboardEvent) => { e.preventDefault(); record('copy_attempt'); };
    const onPaste = (e: ClipboardEvent) => { e.preventDefault(); record('paste_attempt'); };
    const onCut = (e: ClipboardEvent) => { e.preventDefault(); record('copy_attempt'); };
    const onContextMenu = (e: MouseEvent) => e.preventDefault();
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && ['c', 'v', 'x', 'a'].includes(e.key.toLowerCase())) {
        e.preventDefault();
        record(e.key.toLowerCase() === 'v' ? 'paste_attempt' : 'copy_attempt');
      }
    };

    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener('blur', onBlur);
    document.addEventListener('copy', onCopy);
    document.addEventListener('paste', onPaste);
    document.addEventListener('cut', onCut);
    document.addEventListener('contextmenu', onContextMenu);
    document.addEventListener('keydown', onKeyDown);

    return () => {
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('blur', onBlur);
      document.removeEventListener('copy', onCopy);
      document.removeEventListener('paste', onPaste);
      document.removeEventListener('cut', onCut);
      document.removeEventListener('contextmenu', onContextMenu);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [active, record]);

  return { events: events.current, violations: violations.current, warningMsg };
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function SkillTestPage() {
  const location = useLocation();
  const navigate = useNavigate();

  // Passed via navigation state from ResultsPage
  const { claimed_skills = [], missing_skills = [], partial_skills = [], target_role = 'Software Engineer', job_id } =
    (location.state as any) || {};

  // Guard: if navigated directly without analysis state, redirect home
  const totalSkills = claimed_skills.length + missing_skills.length + partial_skills.length;
  if (totalSkills === 0) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="text-center space-y-4">
          <div className="text-4xl">🎯</div>
          <p className="text-white font-semibold">No skill data found.</p>
          <p className="text-slate-400 text-sm">Complete an analysis first to take the skill test.</p>
          <button onClick={() => navigate('/')} className="mt-4 px-6 py-2 rounded-xl bg-indigo-600 text-white font-bold hover:bg-indigo-500 transition-colors">
            ← Go to Analysis
          </button>
        </div>
      </div>
    );
  }

  const [phase, setPhase] = useState<Phase>('instructions');
  const [session, setSession] = useState<SkillTestSession | null>(null);
  const [result, setResult] = useState<SkillTestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Test state
  const [currentIdx, setCurrentIdx] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [answers, setAnswers] = useState<{ question_id: string; selected_option: string; time_taken_secs: number }[]>([]);
  const [qStartTime, setQStartTime] = useState(Date.now());
  const [qTimeLeft, setQTimeLeft] = useState(60);
  const [totalTimeLeft, setTotalTimeLeft] = useState(0);

  const currentQ = session?.questions[currentIdx];
  const { events: antiCheatEvents, warningMsg } = useAntiCheat(phase === 'testing', currentQ?.id);

  // Per-question timer
  useEffect(() => {
    if (phase !== 'testing' || !currentQ) return;
    setQTimeLeft(currentQ.time_limit_secs);
    setQStartTime(Date.now());
    const iv = setInterval(() => {
      setQTimeLeft(prev => {
        if (prev <= 1) { autoAdvance(); return 0; }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(iv);
  }, [phase, currentIdx]);

  // Total timer
  useEffect(() => {
    if (phase !== 'testing' || !session) return;
    setTotalTimeLeft(session.time_limit_total_secs);
    const iv = setInterval(() => {
      setTotalTimeLeft(prev => {
        if (prev <= 1) { submitTest([]); return 0; }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(iv);
  }, [phase, session]);

  const autoAdvance = useCallback(() => {
    const timeTaken = Math.round((Date.now() - qStartTime) / 1000);
    const newAnswers = [
      ...answers,
      { question_id: currentQ!.id, selected_option: selected || '__skipped__', time_taken_secs: timeTaken },
    ];
    setAnswers(newAnswers);
    setSelected(null);
    if (currentIdx + 1 < (session?.questions.length ?? 0)) {
      setCurrentIdx(i => i + 1);
    } else {
      submitTest(newAnswers);
    }
  }, [answers, currentIdx, currentQ, selected, qStartTime, session]);

  const handleSelect = (optId: string) => setSelected(optId);

  const handleNext = () => autoAdvance();

  // ── API calls ──
  const startTest = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/v1/skill-test/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ claimed_skills, missing_skills, partial_skills, target_role, num_questions_per_skill: 3 }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data: SkillTestSession = await res.json();
      setSession(data);
      setCurrentIdx(0);
      setAnswers([]);
      setPhase('testing');
    } catch (e: any) {
      setError(e.message || 'Failed to generate test');
    } finally {
      setLoading(false);
    }
  };

  const submitTest = async (finalAnswers: typeof answers) => {
    if (!session) return;
    setPhase('submitting');
    try {
      const res = await fetch('/api/v1/skill-test/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: session.session_id,
          answers: finalAnswers,
          anti_cheat_events: antiCheatEvents,
          total_time_secs: session.time_limit_total_secs - totalTimeLeft,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data: SkillTestResult = await res.json();
      setResult(data);
      setPhase('results');
    } catch (e: any) {
      setError(e.message || 'Failed to submit test');
      setPhase('testing');
    }
  };

  // ── Render phases ──
  if (phase === 'instructions') return <InstructionsScreen
    claimed={claimed_skills} partial={partial_skills} missing={missing_skills}
    targetRole={target_role} loading={loading} error={error}
    onStart={startTest} onBack={() => navigate(-1)} />;

  if (phase === 'testing' && session && currentQ) return <TestScreen
    question={currentQ} questionIdx={currentIdx} totalQuestions={session.total_questions}
    selected={selected} qTimeLeft={qTimeLeft} totalTimeLeft={totalTimeLeft}
    warningMsg={warningMsg} onSelect={handleSelect} onNext={handleNext} />;

  if (phase === 'submitting') return (
    <FullScreen>
      <div className="text-center space-y-4">
        <div className="text-5xl animate-spin">⚙️</div>
        <p className="text-xl font-bold text-white">Scoring your answers…</p>
        <p className="text-slate-400 text-sm">Answer key verified server-side</p>
      </div>
    </FullScreen>
  );

  if (phase === 'results' && result) return <ResultsScreen
    result={result} onRetake={() => { setPhase('instructions'); setSession(null); setResult(null); setAnswers([]); setCurrentIdx(0); }}
    onBack={() => navigate(-1)} />;

  return <FullScreen><p className="text-white">Loading…</p></FullScreen>;
}

// ─── Instructions Screen ──────────────────────────────────────────────────────
function InstructionsScreen({ claimed, partial, missing, targetRole, loading, error, onStart, onBack }: any) {
  const total = claimed.length + partial.length + missing.length;
  return (
    <FullScreen>
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-2xl mx-auto space-y-6 p-6">
        <div className="text-center">
          <div className="text-5xl mb-3">🎯</div>
          <h1 className="text-3xl font-bold text-white mb-1">Skill Verification Test</h1>
          <p className="text-slate-400">Target role: <span className="text-indigo-400 font-semibold">{targetRole}</span></p>
        </div>

        {/* Skill breakdown */}
        <div className="grid grid-cols-3 gap-3">
          <SkillPill label="Claimed" skills={claimed} color="text-blue-400" bg="bg-blue-900/30 border-blue-700" />
          <SkillPill label="Partial" skills={partial} color="text-yellow-400" bg="bg-yellow-900/30 border-yellow-700" />
          <SkillPill label="Missing" skills={missing} color="text-red-400" bg="bg-red-900/30 border-red-700" />
        </div>

        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 space-y-2">
          <h2 className="text-white font-bold mb-3">📋 Test Rules</h2>
          {[
            '🚫 Tab switching is detected and recorded',
            '🚫 Copy & paste are disabled',
            '⏱️ Each question has a countdown timer',
            '🔒 Answers are verified server-side — you cannot modify them',
            '➡️ You cannot go back to a previous question',
            '📊 Your integrity score is shown with results',
          ].map((r, i) => (
            <div key={i} className="flex items-start gap-2 text-sm text-slate-300">
              <span className="flex-shrink-0">{r}</span>
            </div>
          ))}
        </div>

        <div className="bg-indigo-900/30 border border-indigo-700 rounded-xl p-4 text-sm text-indigo-200">
          <strong>~{total * 3} questions</strong> across {total} skills · Estimated <strong>~{Math.round(total * 3)}–{Math.round(total * 4)} minutes</strong>
        </div>

        {error && <div className="bg-red-900/40 border border-red-700 rounded-lg p-3 text-red-300 text-sm">{error}</div>}

        <div className="flex gap-3">
          <button onClick={onBack} className="flex-1 py-3 rounded-xl border border-slate-600 text-slate-300 hover:bg-slate-800 transition-colors">
            ← Back
          </button>
          <button onClick={onStart} disabled={loading || total === 0}
            className="flex-1 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-bold transition-colors flex items-center justify-center gap-2">
            {loading ? <><span className="animate-spin">⚙️</span> Generating…</> : '🚀 Start Test'}
          </button>
        </div>
      </motion.div>
    </FullScreen>
  );
}

function SkillPill({ label, skills, color, bg }: any) {
  return (
    <div className={`rounded-xl border p-3 ${bg}`}>
      <div className={`text-xs font-bold uppercase ${color} mb-2`}>{label} ({skills.length})</div>
      <div className="space-y-1">
        {skills.slice(0, 4).map((s: string) => (
          <div key={s} className="text-xs text-slate-300 truncate">{s}</div>
        ))}
        {skills.length > 4 && <div className="text-xs text-slate-500">+{skills.length - 4} more</div>}
      </div>
    </div>
  );
}

// ─── Test Screen ─────────────────────────────────────────────────────────────
function TestScreen({ question, questionIdx, totalQuestions, selected, qTimeLeft, totalTimeLeft, warningMsg, onSelect, onNext }: any) {
  const progress = ((questionIdx) / totalQuestions) * 100;
  const qUrgent = qTimeLeft <= 10;
  const totalUrgent = totalTimeLeft <= 60;

  return (
    <FullScreen>
      <div className="w-full max-w-2xl mx-auto flex flex-col gap-4 p-4 h-full">
        {/* Anti-cheat warning overlay */}
        <AnimatePresence>
          {warningMsg && (
            <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}
              className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-red-600 text-white px-6 py-3 rounded-xl font-bold shadow-2xl text-sm">
              {warningMsg}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="text-sm text-slate-400">
            Question <span className="text-white font-bold">{questionIdx + 1}</span>/{totalQuestions}
          </div>
          <div className="flex gap-3">
            <div className={`text-sm font-mono font-bold ${qUrgent ? 'text-red-400 animate-pulse' : 'text-slate-300'}`}>
              ⏱️ {qTimeLeft}s
            </div>
            <div className={`text-sm font-mono ${totalUrgent ? 'text-orange-400' : 'text-slate-500'}`}>
              Total: {Math.floor(totalTimeLeft / 60)}:{String(totalTimeLeft % 60).padStart(2, '0')}
            </div>
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-slate-800 rounded-full h-1.5">
          <div className="bg-indigo-500 h-1.5 rounded-full transition-all duration-300" style={{ width: `${progress}%` }} />
        </div>

        {/* Skill badge */}
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-1 rounded-full font-medium ${
            question.skill_category === 'claimed' ? 'bg-blue-900/50 text-blue-300' :
            question.skill_category === 'partial' ? 'bg-yellow-900/50 text-yellow-300' :
            'bg-red-900/50 text-red-300'
          }`}>{question.skill}</span>
          <span className="text-xs text-slate-500 capitalize">{question.difficulty}</span>
          <span className={`text-xs ml-auto px-2 py-1 rounded-full ${
            qTimeLeft > 20 ? 'bg-slate-800 text-slate-400' :
            qTimeLeft > 10 ? 'bg-yellow-900/40 text-yellow-300' : 'bg-red-900/50 text-red-300 animate-pulse'
          }`}>{qTimeLeft > 20 ? '🟢' : qTimeLeft > 10 ? '🟡' : '🔴'} {qTimeLeft}s</span>
        </div>

        {/* Question */}
        <motion.div key={question.id} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}
          className="bg-slate-800 border border-slate-700 rounded-2xl p-6 flex-1">
          <p className="text-white text-lg leading-relaxed font-medium mb-6">{question.question}</p>

          <div className="space-y-3">
            {question.options.map((opt: MCQOption) => (
              <button key={opt.id} onClick={() => onSelect(opt.id)}
                className={`w-full text-left p-4 rounded-xl border transition-all duration-150 flex items-start gap-3 ${
                  selected === opt.id
                    ? 'border-indigo-500 bg-indigo-900/40 text-white'
                    : 'border-slate-700 bg-slate-900/50 text-slate-300 hover:border-slate-500 hover:bg-slate-800'
                }`}>
                <span className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold ${
                  selected === opt.id ? 'bg-indigo-600 text-white' : 'bg-slate-700 text-slate-400'
                }`}>{opt.id}</span>
                <span className="flex-1 text-sm leading-relaxed">{opt.text}</span>
              </button>
            ))}
          </div>
        </motion.div>

        {/* Next button */}
        <button onClick={onNext}
          className={`w-full py-3.5 rounded-xl font-bold transition-all ${
            selected
              ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-900/40'
              : 'bg-slate-700 text-slate-400 cursor-not-allowed'
          }`}>
          {questionIdx + 1 === totalQuestions ? '✅ Submit Test' : 'Next Question →'}
        </button>
      </div>
    </FullScreen>
  );
}

// ─── Results Screen ───────────────────────────────────────────────────────────
function ResultsScreen({ result, onRetake, onBack }: { result: SkillTestResult; onRetake: () => void; onBack: () => void }) {
  const verdictColor = result.overall_score_pct >= 75 ? 'text-green-400' : result.overall_score_pct >= 50 ? 'text-yellow-400' : 'text-red-400';
  const integrityColor = result.integrity.integrity_label === 'Clean' ? 'text-green-400' : result.integrity.integrity_label === 'Suspicious' ? 'text-yellow-400' : 'text-red-400';

  return (
    <FullScreen>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
        className="w-full max-w-2xl mx-auto space-y-5 p-5 overflow-y-auto">

        {/* Header */}
        <div className="text-center space-y-2">
          <div className="text-5xl">{result.overall_score_pct >= 75 ? '🎉' : result.overall_score_pct >= 50 ? '💪' : '📚'}</div>
          <div className={`text-4xl font-bold ${verdictColor}`}>{result.overall_score_pct}%</div>
          <div className="text-xl text-white font-semibold">{result.overall_verdict}</div>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-3">
          <StatCard icon="✅" label="Verified" val={result.verified_count} color="text-green-400" />
          <StatCard icon="⚡" label="Partial" val={result.partial_count} color="text-yellow-400" />
          <StatCard icon="📖" label="Needs Work" val={result.needs_work_count} color="text-red-400" />
        </div>

        {/* Per-skill breakdown */}
        <div className="bg-slate-800 border border-slate-700 rounded-2xl p-5 space-y-3">
          <h2 className="text-white font-bold">Skill Breakdown</h2>
          {result.skill_scores.map(s => (
            <div key={s.skill} className="flex items-center gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm text-white font-medium truncate">{s.skill}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-bold ${
                    s.verdict === 'Verified' ? 'bg-green-900/50 text-green-300' :
                    s.verdict === 'Partial' ? 'bg-yellow-900/50 text-yellow-300' : 'bg-red-900/50 text-red-300'
                  }`}>{s.verdict}</span>
                </div>
                <div className="w-full bg-slate-700 rounded-full h-1.5">
                  <div className={`h-1.5 rounded-full transition-all ${
                    s.verdict_color === 'green' ? 'bg-green-500' : s.verdict_color === 'yellow' ? 'bg-yellow-500' : 'bg-red-500'
                  }`} style={{ width: `${s.score_pct}%` }} />
                </div>
              </div>
              <div className="text-sm font-bold text-white w-10 text-right">{s.score_pct}%</div>
            </div>
          ))}
        </div>

        {/* Integrity report */}
        <div className="bg-slate-800 border border-slate-700 rounded-2xl p-5">
          <h2 className="text-white font-bold mb-3">🔒 Integrity Report</h2>
          <div className="flex items-center justify-between mb-3">
            <span className="text-slate-400 text-sm">Overall integrity</span>
            <span className={`font-bold ${integrityColor}`}>{result.integrity.integrity_label} ({result.integrity.integrity_score}%)</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs text-slate-400">
            <span>Tab switches: <strong className="text-white">{result.integrity.tab_switches}</strong></span>
            <span>Focus losses: <strong className="text-white">{result.integrity.focus_losses}</strong></span>
            <span>Copy attempts: <strong className="text-white">{result.integrity.copy_attempts}</strong></span>
            <span>Paste attempts: <strong className="text-white">{result.integrity.paste_attempts}</strong></span>
          </div>
        </div>

        {/* Next steps */}
        {result.next_steps.length > 0 && (
          <div className="bg-indigo-900/30 border border-indigo-700 rounded-2xl p-5">
            <h2 className="text-white font-bold mb-3">🗺️ Next Steps</h2>
            <ul className="space-y-2">
              {result.next_steps.map((s, i) => (
                <li key={i} className="flex gap-2 text-sm text-indigo-200">
                  <span className="text-indigo-400 flex-shrink-0">{i + 1}.</span>{s}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Learning priorities */}
        {result.learning_priorities.length > 0 && (
          <div className="bg-slate-800 border border-slate-700 rounded-2xl p-5">
            <h2 className="text-white font-bold mb-3">📋 Learning Priority Order</h2>
            <div className="flex flex-wrap gap-2">
              {result.learning_priorities.map((skill, i) => (
                <span key={skill} className="flex items-center gap-1 bg-slate-700 text-slate-200 px-3 py-1 rounded-full text-sm">
                  <span className="text-slate-500 text-xs">#{i + 1}</span> {skill}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3 pb-4">
          <button onClick={onBack} className="flex-1 py-3 rounded-xl border border-slate-600 text-slate-300 hover:bg-slate-800 transition-colors">
            ← Back to Results
          </button>
          <button onClick={onRetake} className="flex-1 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold transition-colors">
            🔄 Retake Test
          </button>
        </div>
      </motion.div>
    </FullScreen>
  );
}

function StatCard({ icon, label, val, color }: any) {
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 text-center">
      <div className="text-2xl mb-1">{icon}</div>
      <div className={`text-2xl font-bold ${color}`}>{val}</div>
      <div className="text-xs text-slate-400 mt-1">{label}</div>
    </div>
  );
}

function FullScreen({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 select-none">
      {children}
    </div>
  );
}
