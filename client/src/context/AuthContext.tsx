/**
 * AuthContext
 * ───────────
 * Provides the Supabase session (and the extracted GitHub username +
 * OAuth access token) to the entire app.
 *
 * The GitHub access token is the one Supabase stores in
 * session.provider_token after a successful GitHub OAuth sign-in.
 * We pass it to the backend so it can call the GitHub API as the user
 * (authenticated, 5 000 req/h, access to private repos if scope allows).
 */
import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from 'react';
import type { Session, User } from '@supabase/supabase-js';
import { supabase } from '../lib/supabase';

interface AuthState {
  session:      Session | null;
  user:         User    | null;
  /** GitHub login handle, e.g. "BlackHat-17" */
  githubLogin:  string  | null;
  /** OAuth access token from GitHub — passed to the backend */
  githubToken:  string  | null;
  loading:      boolean;
  signInWithGitHub: () => Promise<void>;
  signOut:          () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session,     setSession]     = useState<Session | null>(null);
  const [user,        setUser]        = useState<User    | null>(null);
  const [githubLogin, setGithubLogin] = useState<string  | null>(null);
  const [githubToken, setGithubToken] = useState<string  | null>(null);
  const [loading,     setLoading]     = useState(true);

  const applySession = (s: Session | null) => {
    setSession(s);
    setUser(s?.user ?? null);
    // Supabase stores the provider token here after OAuth
    setGithubToken(s?.provider_token ?? null);
    // The GitHub username lives in user_metadata
    setGithubLogin(
      (s?.user?.user_metadata?.user_name as string | undefined) ?? null
    );
  };

  useEffect(() => {
    // Load any existing session on mount
    supabase.auth.getSession().then(({ data }) => {
      applySession(data.session);
      setLoading(false);
    });

    // Keep state in sync with auth events (login, logout, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, s) => applySession(s)
    );

    return () => subscription.unsubscribe();
  }, []);

  const signInWithGitHub = async () => {
    await supabase.auth.signInWithOAuth({
      provider: 'github',
      options: {
        // Request read-only access to public repos
        scopes: 'read:user public_repo',
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
  };

  const signOut = async () => {
    await supabase.auth.signOut();
    setSession(null);
    setUser(null);
    setGithubLogin(null);
    setGithubToken(null);
  };

  return (
    <AuthContext.Provider
      value={{
        session, user, githubLogin, githubToken,
        loading, signInWithGitHub, signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
