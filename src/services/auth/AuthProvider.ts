export interface AuthUser {
  id: string;
  email: string;
  is_admin?: boolean;
}

export type SignupIdentity = {
  displayName: string;
  username: string;
};

export interface AuthProvider {
  currentUser(): Promise<AuthUser | null>;
  signIn(email: string, password: string): Promise<AuthUser>;
  signUp(email: string, password: string, identity?: SignupIdentity): Promise<AuthUser>;
  signOut(): Promise<void>;
}

import { api } from "../api/apiClient";

export class ApiAuthProvider implements AuthProvider {
  async currentUser() { return (await api<{ user: AuthUser | null }>("/api/auth/me")).user; }
  async signIn(email: string, password: string) { return (await api<{ user: AuthUser }>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) })).user; }
  async signUp(email: string, password: string, identity?: SignupIdentity) {
    return (await api<{ user: AuthUser }>("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        ...(identity ? { display_name: identity.displayName, username: identity.username } : {}),
      }),
    })).user;
  }
  async signOut() { await api("/api/auth/logout", { method: "POST" }); }
}
export const authProvider: AuthProvider = new ApiAuthProvider();
