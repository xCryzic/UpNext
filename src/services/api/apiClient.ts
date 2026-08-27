const configuredUrl = import.meta.env.VITE_API_URL as string | undefined;
export const API_URL = (configuredUrl || "http://localhost:5000").replace(/\/$/, "");
export class ApiError extends Error { constructor(message: string, public status: number) { super(message); } }
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_URL}${path}`, { ...options, credentials: "include", headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(body.error || "Something went wrong. Please try again.", response.status);
  return body as T;
}
