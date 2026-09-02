import re


def _text(value):
    if isinstance(value, (list, tuple)):
        return " ".join(str(item) for item in value).lower()
    return str(value or "").lower()


def profile_completeness(profile):
    fields = ("display_name", "username", "bio", "avatar", "location", "website")
    return sum(bool(profile.get(field)) for field in fields)


def calculate_profile_strength(profile):
    """Return a transparent 0–100 profile-strength signal for discovery.

    This measures directory completeness, not identity, safety, talent, or
    endorsement. Ownership verification is deliberately capped at 10 points.
    """
    projects = profile.get("projects") or []
    socials = profile.get("social_accounts") or []
    skills = profile.get("skills") or []
    categories = profile.get("categories") or []
    verified_social_count = int(profile.get("verified_social_count") or 0)
    score = 0
    score += 25 if (profile.get("publishability") or {}).get("publishable") else 0
    score += 10 if str(profile.get("bio") or "").strip() else 0
    score += 10 if categories else 0
    score += min(len(skills), 3) * 5
    score += 8 if projects else 0
    score += min(len(projects), 3) * 4
    score += 4 if socials else 0
    score += min(len(socials), 3) * 2
    score += min(verified_social_count, 2) * 5
    return min(score, 100)


def discovery_score(profile, search="", category=""):
    haystack = " ".join(
        [
            _text(profile.get("display_name")),
            _text(profile.get("username")),
            _text(profile.get("bio")),
            _text(profile.get("categories")),
            _text(profile.get("skills")),
            _text(profile.get("looking_for")),
            _text(profile.get("project_text")),
        ]
    )
    # Query/category relevance remains dominant when present. Profile strength
    # rewards useful, complete directory entries; verification is only 0–10 of it.
    score = calculate_profile_strength(profile)
    if search:
        score += sum(30 for term in re.findall(r"\w+", search.lower()) if term in haystack)
    if category and category.lower() in _text(profile.get("categories")):
        score += 20
    return score


def sort_profiles(profiles, sort="discover", search="", category=""):
    if sort == "recent":
        return sorted(profiles, key=lambda p: (p.get("updated_at") or "", p.get("username") or ""), reverse=True)
    if sort == "complete":
        return sorted(profiles, key=lambda p: (-calculate_profile_strength(p), p.get("username") or ""))
    return sorted(
        profiles,
        key=lambda p: (-discovery_score(p, search, category), p.get("username") or ""),
    )
