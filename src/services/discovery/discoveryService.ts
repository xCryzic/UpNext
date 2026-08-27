import type { Creator } from "../../domain/creator";

export type DiscoverySort = "discover" | "recent" | "complete";
export interface DiscoveryQuery { text: string; category: string; sort: DiscoverySort; }

// Legacy client-side implementation retained as a future fallback/reference.
// Production discovery uses the Flask-backed creatorApi listCreators() path.
export function discover(creators: Creator[], query: DiscoveryQuery) {
  const term = query.text.trim().toLowerCase();
  const filtered = creators.filter((creator) => {
    const searchable = [creator.displayName, creator.username, creator.bio, ...creator.categories, ...creator.skills, ...creator.lookingFor, ...creator.projects.flatMap((p) => [p.title, p.description])].join(" ").toLowerCase();
    return (!term || searchable.includes(term)) && (!query.category || creator.categories.includes(query.category as Creator["categories"][number]));
  });
  return [...filtered].sort((a, b) => query.sort === "recent" ? Date.parse(b.createdAt) - Date.parse(a.createdAt) : query.sort === "complete" ? completeness(b) - completeness(a) : discoveryScore(b) - discoveryScore(a));
}
function completeness(c: Creator) { return [c.bio, c.website, c.location, c.skills.length, c.projects.length, c.lookingFor.length].filter(Boolean).length; }
function discoveryScore(c: Creator) { return completeness(c) * 10 + (Date.parse(c.updatedAt) / 86_400_000) % 7; }
