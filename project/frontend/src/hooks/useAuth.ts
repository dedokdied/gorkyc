import { useCallback, useEffect, useState } from "react";
import {
  linkTelegram as linkTelegramRequest,
  login as loginRequest,
  me,
  register as registerRequest,
  updateProfile as updateProfileRequest,
} from "../api/auth";
import {
  clearAuthToken,
  getAuthToken,
  setAuthToken,
  UNAUTHORIZED_EVENT,
} from "../api/client";
import { clearSessionId } from "../store/session";
import type { AuthUser } from "../types/auth";

export function useAuth() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [booting, setBooting] = useState(() => Boolean(getAuthToken()));

  const signOut = useCallback(() => {
    clearAuthToken();
    clearSessionId();
    setUser(null);
    setBooting(false);
  }, []);

  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      setBooting(false);
      return;
    }

    let active = true;
    void me()
      .then((nextUser) => {
        if (active) {
          setUser(nextUser);
        }
      })
      .catch(() => {
        if (active) {
          signOut();
        }
      })
      .finally(() => {
        if (active) {
          setBooting(false);
        }
      });

    return () => {
      active = false;
    };
  }, [signOut]);

  useEffect(() => {
    const handleUnauthorized = () => signOut();
    window.addEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
  }, [signOut]);

  const signIn = useCallback(async (email: string, password: string) => {
    const response = await loginRequest(email, password);
    setAuthToken(response.access_token);
    clearSessionId();
    setUser(response.user);
  }, []);

  const signUp = useCallback(
    async (email: string, password: string, displayName?: string) => {
      const response = await registerRequest({
        email,
        password,
        display_name: displayName?.trim() || undefined,
      });
      setAuthToken(response.access_token);
      clearSessionId();
      setUser(response.user);
    },
    [],
  );

  const linkTelegram = useCallback(async (code: string) => {
    const nextUser = await linkTelegramRequest(code.trim());
    setUser(nextUser);
    return nextUser;
  }, []);

  const updateProfile = useCallback(
    async (payload: { display_name?: string; timezone?: string }) => {
      const nextUser = await updateProfileRequest(payload);
      setUser(nextUser);
      return nextUser;
    },
    [],
  );

  return { user, booting, signIn, signUp, signOut, linkTelegram, updateProfile };
}
