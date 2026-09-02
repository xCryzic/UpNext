export interface AuthUser {
  id: string;
  email: string;
  is_admin?: boolean;
}

export interface AuthProvider {
  currentUser(): Promise<AuthUser | null>;
  signIn(email: string, password: string): Promise<AuthUser>;
  signUp(email: string, password: string): Promise<AuthUser>;
  signOut(): Promise<void>;
}

import { api } from "../api/apiClient";

export class ApiAuthProvider implements AuthProvider {
  async currentUser() { return (await api<{ user: AuthUser | null }>("/api/auth/me")).user; }
  async signIn(email: string, password: string) { return (await api<{ user: AuthUser }>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) })).user; }
  async signUp(email: string, password: string) { return (await api<{ user: AuthUser }>("/api/auth/signup", { method: "POST", body: JSON.stringify({ email, password }) })).user; }
  async signOut() { await api("/api/auth/logout", { method: "POST" }); }
}
export const authProvider: AuthProvider = new ApiAuthProvider();
