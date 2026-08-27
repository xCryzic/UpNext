import { api } from "../api/apiClient";
export const reportReasons = ["misleading_work", "plagiarism", "spam", "fake_credentials", "ai_misrepresentation", "inappropriate_content", "other"] as const;
export async function submitReport(creatorId: number, reason: string, details: string) { await api("/api/reports", { method: "POST", body: JSON.stringify({ creator_id: creatorId, reason, details }) }); }
