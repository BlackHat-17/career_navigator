/**
 * AuthCallbackPage
 * ────────────────
 * Supabase redirects the user back to /auth/callback after GitHub OAuth.
 * This page just waits for the session to be established, then sends
 * the user back to the upload page.
 */
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { supabase } from '../lib/supabase';

export default function AuthCallbackPage() {
  const navigate = useNavigate();

  useEffect(() => {
    // Supabase automatically exchanges the code in the URL for a session.
    // We just need to wait for onAuthStateChange to fire, then redirect.
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event) => {
        if (event === 'SIGNED_IN') {
          subscription.unsubscribe();
          navigate('/', { replace: true });
        }
      }
    );

    // Fallback — if the event fires before we subscribe, redirect anyway
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) {
        subscription.unsubscribe();
        navigate('/', { replace: true });
      }
    });

    return () => subscription.unsubscribe();
  }, [navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex flex-col items-center gap-4"
      >
        {/* Spinner */}
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 0.9, repeat: Infinity, ease: 'linear' }}
          className="w-10 h-10 rounded-full border-2 border-white/10 border-t-brand-500"
        />
        <p className="text-sm text-zinc-400">Connecting GitHub account…</p>
      </motion.div>
    </div>
  );
}
