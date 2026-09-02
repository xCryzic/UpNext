import { api } from "../api/apiClient";

export type ModerationReport = { id: number; reason: string; details: string; status: "open" | "dismissed" | "actioned"; created_at: string; creator_id: number; display_name: string; username: string; reporter_email: string };

export async function listReports(): Promise<ModerationReport[]> {
  return (await api<{ reports: ModerationReport[] }>("/api/admin/reports")).reports;
}

export async function updateReportStatus(id: number, status: ModerationReport["status"]): Promise<void> {
  await api(`/api/admin/reports/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
}

export async function updateAdminCreatorVisibility(id: number, isPublic: boolean): Promise<void> {
  await api(`/api/admin/creators/${id}/visibility`, { method: "PATCH", body: JSON.stringify({ is_public: isPublic }) });
}
