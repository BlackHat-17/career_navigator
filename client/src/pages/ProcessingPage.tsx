import { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import PageTransition from '../components/PageTransition';

interface LogLine { id: number; message: string; type: 'step' | 'done' | 'error'; ts: string; }

const STEPS = [
  { id: 1, label: 'GitHub',   icon: '🐙', desc: 'Scanning repositories'  },
  { id: 2, label: 'Resume',   icon: '📄', desc: 'Reading resume content' },
  { id: 3, label: 'Skills',   icon: '🔍', desc: 'Cross-referencing skills' },
  { id: 4, label: 'Projects', icon: '💡', desc: 'Finding project ideas' },
  { id: 5, label: 'Roadmap',  icon: '🗺️', desc: 'Building learning path' },
];

// Map v1 status to step number
const statusToStep = (status: string): number => {
  switch (status) {
    case 'PENDING': return 0;
    case 'PROCESSING': return 3; // Middle of pipeline
    case 'COMPLETED': return 5;
    case 'FAILED': return 0;
    default: return 0;
  }
};

export default function ProcessingPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate  = useNavigate();
  const [log, setLog]           = useState<LogLine[]>([]);
  const [step, setStep]         = useState(0); // Start at 0 for initial loading
  const [failed, setFailed]     = useState('');
  const [complete, setComplete] = useState(false);
  const [initializing, setInitializing] = useState(true); // NEW: Track initialization
  const logRef  = useRef<HTMLDivElement>(null);
  const counter = useRef(0);
  const ts = () => new Date().toLocaleTimeString('en-US', { hour12: false });

  useEffect(() => {
    if (!jobId) return;

    let pollInterval: number;
    let isActive = true;

    const addLog = (message: string, type: 'step' | 'done' | 'error') => {
      setLog(prev => [...prev, { id: counter.current++, message, type, ts: ts() }]);
    };

    const pollStatus = async () => {
      try {
        const response = await fetch(`/api/v1/analysis/${jobId}`);
        
        if (!response.ok) {
          if (response.status === 404) {
            setFailed('Analysis job not found.');
          } else {
            setFailed(`Server error: ${response.status}`);
          }
          isActive = false;
          return;
        }

        const data = await response.json();
        const { status, result, error_message } = data;

        // First successful poll - hide initializing screen
        if (initializing) {
          setInitializing(false);
          addLog('Connected to analysis pipeline', 'step');
        }

        // Update step based on status
        const currentStep = statusToStep(status);
        setStep(currentStep);

        if (status === 'PROCESSING' && currentStep > 0) {
          addLog(`Processing step ${currentStep} of ${STEPS.length}...`, 'step');
        }

        if (status === 'COMPLETED') {
          addLog('Analysis complete — building your report…', 'done');
          setComplete(true);
          isActive = false;
          setTimeout(() => {
            navigate(`/results/${jobId}`, { state: { result } });
          }, 1400);
        } else if (status === 'FAILED') {
          setFailed(error_message || 'Analysis failed');
          isActive = false;
        }
      } catch (err) {
        console.error('Polling error:', err);
        setInitializing(false);
        setFailed('Lost connection to server.');
        isActive = false;
      }
    };

    // Initial poll
    pollStatus();

    // Poll every 2 seconds
    pollInterval = window.setInterval(() => {
      if (isActive) {
        pollStatus();
      } else {
        clearInterval(pollInterval);
      }
    }, 2000);

    return () => {
      isActive = false;
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [jobId, navigate, initializing]);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' });
  }, [log]);

  const pct = step > 0 ? Math.round(((step - 1) / 3) * 100) : 0;

  return (
    <PageTransition className="min-h-screen flex items-center justify-center px-4 py-16 overflow-hidden">
      {/* BG */}
      <div className="fixed inset-0 pointer-events-none">
        <motion.div className="orb w-[600px] h-[600px] bg-indigo-600/20 -top-40 left-1/4"
          animate={{ scale: [1,1.2,1] }} transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut' }} />
        <motion.div className="orb w-[400px] h-[400px] bg-violet-600/15 bottom-0 right-1/4"
          animate={{ scale: [1,1.3,1] }} transition={{ duration: 9, repeat: Infinity, ease: 'easeInOut', delay: 2 }} />
        <div className="absolute inset-0 opacity-[0.025]"
          style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)', backgroundSize: '60px 60px' }} />
      </div>

      <div className="relative w-full max-w-lg z-10">
        <AnimatePresence mode="wait">
          {/* Initial Loading Screen */}
          {initializing && !failed ? (
            <motion.div 
              key="initializing" 
              initial={{ opacity: 0, scale: 0.95 }} 
              animate={{ opacity: 1, scale: 1 }} 
              exit={{ opacity: 0, scale: 1.05 }}
              transition={{ duration: 0.3 }}
              className="text-center space-y-6"
            >
              {/* Animated Logo/Icon */}
              <div className="relative w-32 h-32 mx-auto">
                <motion.div
                  className="absolute inset-0 rounded-full"
                  style={{
                    background: 'linear-gradient(135deg, rgba(96,121,248,0.2), rgba(167,139,250,0.2))',
                    border: '2px solid rgba(96,121,248,0.3)',
                  }}
                  animate={{
                    scale: [1, 1.1, 1],
                    rotate: [0, 180, 360],
                  }}
                  transition={{
                    duration: 3,
                    repeat: Infinity,
                    ease: 'easeInOut',
                  }}
                />
                <motion.div
                  className="absolute inset-4 rounded-full flex items-center justify-center text-5xl"
                  style={{
                    background: 'rgba(10,11,15,0.8)',
                    backdropFilter: 'blur(10px)',
                  }}
                  animate={{
                    scale: [1, 0.95, 1],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: 'easeInOut',
                  }}
                >
                  🤖
                </motion.div>
              </div>

              {/* Loading Text */}
              <div>
                <motion.h2 
                  className="text-2xl font-black text-white mb-2"
                  animate={{ opacity: [0.7, 1, 0.7] }}
                  transition={{ duration: 2, repeat: Infinity }}
                >
                  Initializing AI Analysis
                </motion.h2>
                <p className="text-sm text-zinc-400">
                  Connecting to LLM providers...
                </p>
              </div>

              {/* Animated Dots */}
              <div className="flex items-center justify-center gap-2">
                {[0, 1, 2].map((i) => (
                  <motion.div
                    key={i}
                    className="w-2 h-2 rounded-full bg-brand-400"
                    animate={{
                      scale: [1, 1.5, 1],
                      opacity: [0.3, 1, 0.3],
                    }}
                    transition={{
                      duration: 1.5,
                      repeat: Infinity,
                      delay: i * 0.2,
                    }}
                  />
                ))}
              </div>

              {/* Status Messages */}
              <div className="mt-8 space-y-2 text-xs text-zinc-500">
                <motion.div
                  animate={{ opacity: [0, 1, 1, 0] }}
                  transition={{ duration: 4, repeat: Infinity, times: [0, 0.1, 0.9, 1] }}
                >
                  ⚡ Checking Gemini availability...
                </motion.div>
                <motion.div
                  animate={{ opacity: [0, 1, 1, 0] }}
                  transition={{ duration: 4, repeat: Infinity, times: [0, 0.1, 0.9, 1], delay: 1.3 }}
                >
                  🚀 Preparing fallback providers...
                </motion.div>
                <motion.div
                  animate={{ opacity: [0, 1, 1, 0] }}
                  transition={{ duration: 4, repeat: Infinity, times: [0, 0.1, 0.9, 1], delay: 2.6 }}
                >
                  🔐 Establishing secure connection...
                </motion.div>
              </div>
            </motion.div>
          ) : failed ? (
            <motion.div key="fail" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center">
              <div className="text-6xl mb-4">⚠️</div>
              <h2 className="text-2xl font-black text-rose-300 mb-2">Something went wrong</h2>
              <p className="text-sm text-zinc-400 mb-6">{failed}</p>
              <button onClick={() => navigate('/')} className="btn-ghost">← Try again</button>
            </motion.div>
          ) : (
            <motion.div key="running" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8">
              {/* Header */}
              <div className="text-center">
                {/* Ring */}
                <div className="relative w-24 h-24 mx-auto mb-6">
                  <svg className="w-24 h-24 -rotate-90" viewBox="0 0 96 96">
                    <circle cx="48" cy="48" r="40" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="6" />
                    <motion.circle cx="48" cy="48" r="40" fill="none" strokeWidth="6" strokeLinecap="round"
                      stroke="url(#pg)" strokeDasharray={251}
                      animate={{ strokeDashoffset: complete ? 0 : 251 - (pct / 100) * 251 }}
                      transition={{ duration: 0.8, ease: 'easeOut' }}
                      style={{ filter: 'drop-shadow(0 0 8px rgba(96,121,248,0.7))' }} />
                    <defs>
                      <linearGradient id="pg" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#6079f8" /><stop offset="100%" stopColor="#a78bfa" />
                      </linearGradient>
                    </defs>
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <AnimatePresence mode="wait">
                      {complete ? (
                        <motion.span key="done" initial={{ scale: 0 }} animate={{ scale: 1 }} className="text-2xl">✅</motion.span>
                      ) : step === 0 ? (
                        <motion.span 
                          key="loading" 
                          initial={{ scale: 0, opacity: 0 }} 
                          animate={{ scale: 1, opacity: 1, rotate: 360 }} 
                          transition={{ rotate: { duration: 2, repeat: Infinity, ease: 'linear' }}}
                          className="text-2xl"
                        >
                          ⚙️
                        </motion.span>
                      ) : (
                        <motion.span key={step} initial={{ scale: 0, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="text-2xl">
                          {STEPS[step - 1]?.icon}
                        </motion.span>
                      )}
                    </AnimatePresence>
                  </div>
                </div>

                <AnimatePresence mode="wait">
                  {complete ? (
                    <motion.div key="done-txt" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                      <h2 className="text-3xl font-black" style={{ background: 'linear-gradient(135deg, #a5b4fc, #6079f8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                        Done! Building report…
                      </h2>
                    </motion.div>
                  ) : (
                    <motion.div key={`step-${step}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                      <h2 className="text-2xl font-black text-white">
                        {step === 0 ? 'Connecting to AI...' : 'Analysing your profile'}
                      </h2>
                      <p className="text-sm text-zinc-500 mt-1">
                        {step === 0 ? 'Starting analysis engine...' : `${STEPS[step-1]?.desc} · ~20–40 seconds`}
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Step pills */}
              <div className="flex items-center justify-center">
                {STEPS.map((s, i) => {
                  const state = s.id < step ? 'done' : s.id === step ? 'active' : 'idle';
                  return (
                    <div key={s.id} className="flex items-center">
                      <motion.div
                        animate={state === 'active' ? { scale: [1, 1.05, 1] } : {}}
                        transition={{ duration: 1.5, repeat: Infinity }}
                        className="flex items-center gap-2 px-3.5 py-2 rounded-full text-xs font-semibold transition-all duration-500"
                        style={{
                          background: state === 'done' ? 'rgba(16,185,129,0.15)' : state === 'active' ? 'rgba(96,121,248,0.15)' : 'rgba(255,255,255,0.04)',
                          border: `1px solid ${state === 'done' ? 'rgba(16,185,129,0.4)' : state === 'active' ? 'rgba(96,121,248,0.5)' : 'rgba(255,255,255,0.08)'}`,
                          color: state === 'done' ? '#34d399' : state === 'active' ? '#a5b4fc' : '#52525b',
                          boxShadow: state === 'active' ? '0 0 20px rgba(96,121,248,0.3)' : 'none',
                        }}>
                        <AnimatePresence mode="wait">
                          {state === 'done' ? (
                            <motion.span key="check" initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: 'spring', stiffness: 300 }}>✓</motion.span>
                          ) : state === 'active' ? (
                            <motion.span key="pulse" animate={{ opacity: [1, 0.3, 1] }} transition={{ duration: 1, repeat: Infinity }}
                              className="w-1.5 h-1.5 rounded-full bg-brand-400 inline-block" />
                          ) : (
                            <span key="idle" className="w-1.5 h-1.5 rounded-full bg-zinc-700 inline-block" />
                          )}
                        </AnimatePresence>
                        {s.label}
                      </motion.div>
                      {i < STEPS.length - 1 && (
                        <div className="w-8 h-px transition-all duration-700"
                          style={{ background: s.id < step ? 'rgba(16,185,129,0.5)' : 'rgba(255,255,255,0.07)' }} />
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Terminal */}
              <div className="rounded-2xl overflow-hidden"
                style={{ background: 'rgba(10,11,15,0.9)', border: '1px solid rgba(255,255,255,0.07)', boxShadow: '0 24px 48px rgba(0,0,0,0.5)' }}>
                {/* Bar */}
                <div className="flex items-center gap-2 px-4 py-3 border-b border-white/5">
                  <div className="flex gap-1.5">
                    <span className="w-3 h-3 rounded-full bg-rose-500/60" />
                    <span className="w-3 h-3 rounded-full bg-amber-500/60" />
                    <span className="w-3 h-3 rounded-full bg-emerald-500/60" />
                  </div>
                  <span className="text-[11px] font-mono ml-1 flex-1" style={{ color: '#3f3f46' }}>skillgap-analyzer</span>
                  <motion.div animate={{ opacity: [1, 0.3, 1] }} transition={{ duration: 1.2, repeat: Infinity }}
                    className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    <span className="text-[10px] font-mono text-emerald-400">LIVE</span>
                  </motion.div>
                </div>

                {/* Log */}
                <div ref={logRef} className="px-4 py-4 font-mono text-xs space-y-1.5 h-52 overflow-y-auto"
                  style={{ scrollbarWidth: 'thin', scrollbarColor: '#1e2535 transparent' }}>
                  <AnimatePresence initial={false}>
                    {log.map(line => (
                      <motion.div key={line.id}
                        initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.2 }}
                        className="flex gap-2 items-start"
                        style={{ color: line.type === 'done' ? '#34d399' : line.type === 'error' ? '#f43f5e' : '#a1a1aa' }}>
                        <span className="shrink-0" style={{ color: '#3f3f46' }}>[{line.ts}]</span>
                        <span className="shrink-0">{line.type === 'done' ? '✓' : line.type === 'error' ? '✗' : '▸'}</span>
                        <span>{line.message}</span>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                  {log.length === 0 && (
                    <motion.span animate={{ opacity: [0.4, 0.8, 0.4] }} transition={{ duration: 1.5, repeat: Infinity }}
                      style={{ color: '#3f3f46' }}>Connecting to analysis engine…</motion.span>
                  )}
                  {!complete && !failed && (
                    <motion.span animate={{ opacity: [1, 0, 1] }} transition={{ duration: 0.8, repeat: Infinity }}
                      className="inline-block w-2 h-3.5 rounded-sm" style={{ background: '#6079f8' }} />
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </PageTransition>
  );
}
