import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import keycloak from './keycloak';

interface AuthUser {
  sub: string;
  name: string;
  email: string;
  roles: string[];
  preferredLanguage: string;
}

interface AuthContextType {
  authenticated: boolean;
  user: AuthUser | null;
  token: string | null;
  roles: string[];
  hasRole: (role: string) => boolean;
  isAdmin: boolean;
  isClinician: boolean;
  isAuditor: boolean;
  preferredLanguage: string;
  setPreferredLanguage: (lang: string) => void;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType>({
  authenticated: false,
  user: null,
  token: null,
  roles: [],
  hasRole: () => false,
  isAdmin: false,
  isClinician: false,
  isAuditor: false,
  preferredLanguage: 'en',
  setPreferredLanguage: () => {},
  logout: () => {},
  loading: true,
});

export const useAuth = () => useContext(AuthContext);

const LANG_STORAGE_KEY = 'lchai_preferred_language';

function extractRoles(kc: typeof keycloak): string[] {
  const realmRoles = kc.realmAccess?.roles || [];
  const clientRoles = kc.resourceAccess?.['oncology-api']?.roles || [];
  return [...new Set([...realmRoles, ...clientRoles])];
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [roles, setRoles] = useState<string[]>([]);
  const [preferredLanguage, setPreferredLanguageState] = useState(
    () => localStorage.getItem(LANG_STORAGE_KEY) || 'en'
  );

  const setPreferredLanguage = useCallback((lang: string) => {
    localStorage.setItem(LANG_STORAGE_KEY, lang);
    setPreferredLanguageState(lang);
  }, []);

  useEffect(() => {
    keycloak.init({
      onLoad: 'login-required',
      checkLoginIframe: false,
      pkceMethod: 'S256',
    }).then((auth) => {
      setAuthenticated(auth);
      if (auth && keycloak.tokenParsed) {
        const r = extractRoles(keycloak);
        setRoles(r);
        setToken(keycloak.token || null);
        setUser({
          sub: keycloak.tokenParsed.sub || '',
          name: keycloak.tokenParsed.name || keycloak.tokenParsed.preferred_username || '',
          email: keycloak.tokenParsed.email || '',
          roles: r,
          preferredLanguage,
        });
      }
      setLoading(false);
    }).catch((err) => {
      console.error('Keycloak init failed', err);
      setLoading(false);
    });

    keycloak.onTokenExpired = () => {
      keycloak.updateToken(60).then((refreshed) => {
        if (refreshed) setToken(keycloak.token || null);
      }).catch(() => keycloak.logout());
    };
  }, []);

  const logout = useCallback(() => {
    keycloak.logout({ redirectUri: window.location.origin });
  }, []);

  const hasRole = useCallback((role: string) => roles.includes(role), [roles]);

  const value: AuthContextType = {
    authenticated,
    user,
    token,
    roles,
    hasRole,
    isAdmin: roles.includes('admin'),
    isClinician: roles.includes('clinician'),
    isAuditor: roles.includes('auditor'),
    preferredLanguage,
    setPreferredLanguage,
    logout,
    loading,
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">Authenticating...</p>
        </div>
      </div>
    );
  }

  if (!authenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="text-center">
          <p className="text-red-600 text-lg font-semibold">Authentication required</p>
          <button onClick={() => keycloak.login()} className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
            Login
          </button>
        </div>
      </div>
    );
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
