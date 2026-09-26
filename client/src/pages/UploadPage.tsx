import { useState, useCallback, DragEvent, ChangeEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import PageTransition from '../components/PageTransition';
import { useAuth } from '../context/AuthContext';

const COMMON_ROLES = [
  'Frontend Engineer',
  'Backend Engineer',
  'Full-Stack Engineer',
  'DevOps / Platform Engineer',
  'ML Engineer',
  'Data Engineer',
  'Product Manager',
  'Custom…',
];

const FEATURES = [
  { icon: '📄', label: 'Resume parsing' },
  { icon: '🐙', label: 'GitHub evidence' },
  { icon: '🤖', label: 'Gemini analysis' },
  { icon: '🗺️', label: 'Growth roadmap' },
];

export default function UploadPage() {
  const navigate = useNavigate();
  const { githubLogin, signInWithGitHub, signOut, loading: authLoading } = useAuth();

  const [file, setFile]             = useState<File | null>(null);
  const [dragging, setDragging]     = useState(false);
  const [role, setRole]             = useState('');
  const [customRole, setCustomRole] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState('');

  const resolvedRole = role === 'Custom…' ? customRole : role;

  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  }, []);

  const handleFileInput = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) setFile(e.target.files[0]);
  };

  const handleSubmit = async () => {
    if (!file || !resolvedRole) {
      setError('Please attach a resume and select a role.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      // Prepare FormData for v1 API endpoint
      const form = new FormData();
      form.append('resume_file', file);  // v1 expects 'resume_file'
      form.append('target_role', resolvedRole);  // v1 expects 'target_role'
      
      // Add optional job_description if provided
      if (jobDescription.trim()) {
        form.append('job_description', jobDescription);  // v1 expects 'job_description'
      }
      
      // Add GitHub username if connected
      if (githubLogin) {
        form.append('github_username', githubLogin);  // v1 expects 'github_username'
      }
      
      // Generate or get user_id from auth context
      // For testing: use a fixed UUID that will be auto-created
      const userId = '00000000-0000-0000-0000-000000000001';
      form.append('user_id', userId);

      // Call the v1 orchestrated analysis endpoint
      const { data } = await axios.post<{ analysis_id: string }>('/api/v1/analysis', form, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      // Wait a moment for the job to be fully initialized before navigating
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Navigate to processing page with analysis_id (v1 format)
      navigate(`/processing/${data.analysis_id}`);
    } catch (err: unknown) {
      const backendError = axios.isAxiosError(err)
        ? err.response?.data?.error?.message ??
          err.response?.data?.detail ??
          err.response?.data?.message ??
          err.message
        : 'Upload failed';

      setError(
        typeof backendError === 'string'
          ? backendError
          : JSON.stringify(backendError)
      );
      setLoading(false);
    }
  };

  return (
    <PageTransition className="min-h-screen flex items-center justify-center px-4 py-16 overflow-hidden relative">
      {/* Animated background */}
      <div className="fixed inset-0 pointer-events-none">
        <motion.div className="orb w-[700px] h-[700px] bg-indigo-600/20 -top-60 -left-60"
          animate={{ scale: [1,1.2,1], rotate: [0,15,0] }}
          transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut' }} />
        <motion.div className="orb w-[500px] h-[500px] bg-violet-600/15 bottom-0 right-0"
          animate={{ scale: [1,1.3,1], rotate: [0,-10,0] }}
          transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut', delay: 2 }} />
        <motion.div className="orb w-[300px] h-[300px] bg-cyan-500/10 top-1/3 right-1/3"
          animate={{ scale: [1,1.4,1] }}
          transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut', delay: 4 }} />
        <div className="absolute inset-0 opacity-[0.03]"
          style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)', backgroundSize: '60px 60px' }} />
      </div>

      <div className="relative w-full max-w-lg z-10">
        {/* Badge */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
          className="flex justify-center mb-6">
          <div className="flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold"
            style={{ background: 'rgba(96,121,248,0.12)', border: '1px solid rgba(96,121,248,0.3)', color: '#a5b4fc' }}>
            <motion.span animate={{ opacity: [1,0.3,1] }} transition={{ duration: 1.5, repeat: Infinity }}
              className="w-1.5 h-1.5 rounded-full bg-brand-400 inline-block" />
            AI-Powered Skill Gap Analyzer
          </div>
        </motion.div>

        {/* Headline */}
        <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="text-center mb-10">
          <h1 className="text-6xl font-black tracking-tight leading-none mb-5">
            Know your<br />
            <span style={{ background: 'linear-gradient(135deg, #e0e7ff 0%, #818cf8 35%, #6079f8 65%, #a78bfa 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              real edge.
            </span>
          </h1>
          <p className="text-zinc-400 text-base max-w-sm mx-auto leading-relaxed">
            Upload your resume, connect GitHub, pick a target role — get a precise skill gap report in seconds.
          </p>
        </motion.div>

        {/* Feature pills */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}
          className="flex flex-wrap justify-center gap-2 mb-8">
          {FEATURES.map((f, i) => (
            <motion.span key={f.label}
              initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2 + i * 0.06, type: 'spring', stiffness: 220 }}
              className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium"
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', color: '#a1a1aa' }}>
              {f.icon} {f.label}
            </motion.span>
          ))}
        </motion.div>

        {/* Glass card */}
        <motion.div
          initial={{ opacity: 0, y: 32, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ delay: 0.25, type: 'spring', stiffness: 120, damping: 20 }}
          className="relative rounded-3xl p-7 space-y-5"
          style={{
            background: 'rgba(22, 27, 39, 0.8)',
            backdropFilter: 'blur(20px)',
            border: '1px solid rgba(255,255,255,0.08)',
            boxShadow: '0 0 0 1px rgba(96,121,248,0.1), 0 24px 64px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.06)',
          }}>

          {/* Top glow line */}
          <div className="absolute top-0 left-8 right-8 h-px rounded-full"
            style={{ background: 'linear-gradient(90deg, transparent, rgba(96,121,248,0.6), rgba(167,139,250,0.6), transparent)' }} />

          {/* ── Drop zone ──────────────────────────────────────────────── */}
          <div
            onDragOver={e => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => document.getElementById('file-input')?.click()}
            className="relative rounded-2xl border-2 border-dashed p-8 text-center cursor-pointer transition-all duration-300 overflow-hidden"
            style={{
              borderColor: dragging ? 'rgba(96,121,248,0.7)' : file ? 'rgba(16,185,129,0.5)' : 'rgba(255,255,255,0.1)',
              background:  dragging ? 'rgba(96,121,248,0.08)' : file ? 'rgba(16,185,129,0.05)' : 'rgba(255,255,255,0.02)',
              boxShadow:   dragging ? '0 0 40px rgba(96,121,248,0.2) inset' : 'none',
            }}>
            <input id="file-input" type="file" accept=".pdf,.txt,.doc,.docx" className="hidden" onChange={handleFileInput} />
            <AnimatePresence mode="wait">
              {file ? (
                <motion.div key="file" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}
                  className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-2xl flex items-center justify-center text-2xl shrink-0"
                    style={{ background: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.3)' }}>📄</div>
                  <div className="text-left flex-1 min-w-0">
                    <p className="text-sm font-semibold text-white truncate">{file.name}</p>
                    <p className="text-xs mt-0.5" style={{ color: '#34d399' }}>{(file.size / 1024).toFixed(1)} KB · Ready to analyze</p>
                  </div>
                  <button className="w-8 h-8 rounded-full flex items-center justify-center text-xs transition-all shrink-0"
                    style={{ background: 'rgba(255,255,255,0.06)', color: '#71717a' }}
                    onClick={e => { e.stopPropagation(); setFile(null); }}>✕</button>
                </motion.div>
              ) : (
                <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <motion.div
                    animate={{ y: dragging ? -8 : [0, -6, 0] }}
                    transition={dragging ? { duration: 0.15 } : { duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
                    className="text-5xl mb-3 inline-block">
                    {dragging ? '⬇️' : '📎'}
                  </motion.div>
                  <p className="text-sm font-semibold text-white">{dragging ? 'Release to upload' : 'Drop your resume here'}</p>
                  <p className="text-xs mt-1.5 mb-3" style={{ color: '#52525b' }}>PDF, DOCX, TXT · up to 10 MB</p>
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs"
                    style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#71717a' }}>
                    or click to browse
                  </span>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* ── GitHub OAuth connect ────────────────────────────────────── */}
          <div>
            <label className="block text-xs font-semibold mb-2 tracking-widest uppercase"
              style={{ color: '#71717a' }}>
              GitHub <span className="normal-case font-normal tracking-normal"
                style={{ color: '#3f3f46' }}>— optional, adds real evidence</span>
            </label>

            <AnimatePresence mode="wait">
              {authLoading ? (
                /* Skeleton while session loads */
                <motion.div key="loading"
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                  className="h-12 rounded-xl animate-pulse"
                  style={{ background: 'rgba(255,255,255,0.04)' }} />

              ) : githubLogin ? (
                /* ── Connected state ── */
                <motion.div key="connected"
                  initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="flex items-center justify-between px-4 py-3 rounded-xl"
                  style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.3)' }}>

                  <div className="flex items-center gap-3">
                    {/* GitHub avatar */}
                    <img
                      src={`https://github.com/${githubLogin}.png?size=40`}
                      alt={githubLogin}
                      className="w-8 h-8 rounded-full"
                      style={{ border: '1px solid rgba(16,185,129,0.4)' }}
                    />
                    <div>
                      <p className="text-sm font-semibold text-white leading-tight">@{githubLogin}</p>
                      <p className="text-xs" style={{ color: '#34d399' }}>✓ Connected via GitHub</p>
                    </div>
                  </div>

                  <button
                    onClick={signOut}
                    className="text-xs px-3 py-1.5 rounded-lg transition-all"
                    style={{ background: 'rgba(255,255,255,0.05)', color: '#71717a', border: '1px solid rgba(255,255,255,0.08)' }}
                    onMouseEnter={e => (e.currentTarget.style.color = '#fda4af')}
                    onMouseLeave={e => (e.currentTarget.style.color = '#71717a')}
                  >
                    Disconnect
                  </button>
                </motion.div>

              ) : (
                /* ── Not connected state ── */
                <motion.button key="connect"
                  initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  onClick={signInWithGitHub}
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.98 }}
                  className="w-full flex items-center justify-center gap-3 py-3 rounded-xl font-medium text-sm transition-all duration-200"
                  style={{
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    color: '#e4e4e7',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.background = 'rgba(255,255,255,0.09)';
                    e.currentTarget.style.borderColor = 'rgba(96,121,248,0.4)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
                    e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)';
                  }}
                >
                  {/* GitHub SVG icon */}
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path d="M12 0C5.37 0 0 5.373 0 12c0 5.303 3.438 9.8 8.205 11.387.6.113.82-.258.82-.577
                      0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.387-1.333-1.757
                      -1.333-1.757-1.089-.745.083-.729.083-.729 1.205.084 1.838 1.236 1.838 1.236
                      1.07 1.835 2.809 1.305 3.495.998.108-.776.418-1.305.762-1.605-2.665-.3-5.466
                      -1.332-5.466-5.93 0-1.31.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176
                      0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0 1 12 5.803c1.02.005 2.047.138
                      3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84
                      1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823
                      2.222 0 1.606-.015 2.898-.015 3.293 0 .322.216.694.825.577C20.565 21.796 24
                      17.3 24 12c0-6.627-5.373-12-12-12z" />
                  </svg>
                  Connect GitHub account
                </motion.button>
              )}
            </AnimatePresence>
          </div>

          {/* ── Target role ─────────────────────────────────────────────── */}
          <div>
            <label className="block text-xs font-semibold mb-2 tracking-widest uppercase"
              style={{ color: '#71717a' }}>
              Target role <span className="text-rose-500 normal-case font-normal tracking-normal">*</span>
            </label>
            <div className="relative">
              <select
                value={role} onChange={e => setRole(e.target.value)}
                className="w-full px-4 py-3 text-sm text-white appearance-none focus:outline-none cursor-pointer rounded-xl"
                style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
                <option value="" style={{ background: '#161b27' }}>Select a role…</option>
                {COMMON_ROLES.map(r => (
                  <option key={r} value={r} style={{ background: '#161b27' }}>{r}</option>
                ))}
              </select>
              <span className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-zinc-600">▾</span>
            </div>
            <AnimatePresence>
              {role === 'Custom…' && (
                <motion.input
                  initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 46 }} exit={{ opacity: 0, height: 0 }}
                  type="text" placeholder="e.g. Staff iOS Engineer"
                  value={customRole} onChange={e => setCustomRole(e.target.value)}
                  className="mt-2 w-full px-4 text-sm text-white placeholder-zinc-700 focus:outline-none rounded-xl"
                  style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }} />
              )}
            </AnimatePresence>
          </div>

          {/* ── Job Description ──────────────────────────────────────────── */}
          <div>
            <label className="block text-xs font-semibold mb-2 tracking-widest uppercase"
              style={{ color: '#71717a' }}>
              Job Description
              <span className="normal-case font-normal tracking-normal text-zinc-500 ml-2">
                — paste the full job posting
              </span>
            </label>
            <textarea
              value={jobDescription}
              onChange={e => setJobDescription(e.target.value)}
              placeholder="Paste the full job description here... Include requirements, qualifications, and responsibilities."
              rows={6}
              className="w-full px-4 py-3 text-sm text-white placeholder-zinc-700 focus:outline-none rounded-xl resize-none"
              style={{ 
                background: 'rgba(255,255,255,0.04)', 
                border: '1px solid rgba(255,255,255,0.08)' 
              }}
            />
            <p className="text-xs text-zinc-600 mt-1.5">
              Include key skills, experience requirements, and job responsibilities
            </p>
          </div>

          {/* ── Error banner ────────────────────────────────────────────── */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                className="flex items-center gap-2 px-4 py-3 rounded-xl text-xs"
                style={{ background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.2)', color: '#fda4af' }}>
                ⚠️ {error}
              </motion.div>
            )}
          </AnimatePresence>

          {/* ── Submit ──────────────────────────────────────────────────── */}
          <motion.button
            onClick={handleSubmit}
            disabled={loading || !file || !resolvedRole}
            whileHover={!loading && !!file && !!resolvedRole ? { scale: 1.01 } : {}}
            whileTap={!loading && !!file && !!resolvedRole ? { scale: 0.98 } : {}}
            className="relative w-full py-4 rounded-2xl font-bold text-sm text-white overflow-hidden transition-all duration-200 disabled:opacity-40 disabled:pointer-events-none"
            style={{ background: 'linear-gradient(135deg, #4455f0, #6079f8, #818cf8)', boxShadow: '0 0 32px rgba(96,121,248,0.4), 0 4px 20px rgba(0,0,0,0.3)' }}>
            {/* Shimmer */}
            {!loading && file && resolvedRole && (
              <motion.span className="absolute inset-0 pointer-events-none"
                animate={{ x: ['-100%', '200%'] }}
                transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut', repeatDelay: 1 }}
                style={{ background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent)', width: '60%' }} />
            )}
            <span className="relative flex items-center justify-center gap-2">
              {loading ? (
                <>
                  <motion.span animate={{ rotate: 360 }} transition={{ duration: 0.7, repeat: Infinity, ease: 'linear' }}
                    className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white inline-block" />
                  Analysing…
                </>
              ) : (
                <>
                  Analyze my skills
                  <motion.span animate={{ x: [0, 5, 0] }} transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}>→</motion.span>
                </>
              )}
            </span>
          </motion.button>
        </motion.div>

        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1 }}
          className="text-center text-xs mt-5" style={{ color: '#3f3f46' }}>
          {githubLogin
            ? `Analyzing public repos for @${githubLogin} · resume processed in memory`
            : 'Connect GitHub for deeper analysis · resume processed in memory'}
        </motion.p>
      </div>
    </PageTransition>
  );
}
