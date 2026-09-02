import type { Creator } from "../../domain/creator";
import { api } from "../api/apiClient";
import { mapCreator } from "../creators/creatorApi";

export async function updateProfileVisibility(isPublic: boolean): Promise<Creator> {
  const result = await api<{ creator: Record<string, unknown> }>("/api/creator/visibility", {
    method: "PATCH",
    body: JSON.stringify({ is_public: isPublic }),
  });
  return mapCreator(result.creator);
}

export async function deleteAccount(): Promise<void> {
  await api("/api/account", { method: "DELETE" });
}
