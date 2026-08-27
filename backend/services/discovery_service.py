import re


def _text(value):
    if isinstance(value, (list, tuple)):
        return " ".join(str(item) for item in value).lower()
    return str(value or "").lower()


def profile_completeness(profile):
    fields = ("display_name", "username", "bio", "avatar", "location", "website")
    return sum(bool(profile.get(field)) for field in fields)


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
    score = profile_completeness(profile) * 2
    if search:
        score += sum(3 for term in re.findall(r"\w+", search.lower()) if term in haystack)
    if category and category.lower() in _text(profile.get("categories")):
        score += 5
    return score


def sort_profiles(profiles, sort="discover", search="", category=""):
    if sort == "recent":
        return sorted(profiles, key=lambda p: p.get("updated_at") or "", reverse=True)
    if sort == "complete":
        return sorted(profiles, key=lambda p: profile_completeness(p), reverse=True)
    return sorted(
        profiles,
        key=lambda p: (discovery_score(p, search, category), p.get("updated_at") or ""),
        reverse=True,
    )
