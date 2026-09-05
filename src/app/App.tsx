import { useEffect, useState } from "react";
import { categories, lookingForOptions, socialPlatforms, type Creator, type Project, type SocialAccount } from "../domain/creator";
import { authProvider, type AuthUser } from "../services/auth/AuthProvider";
import { createProject, createSocial, deleteProject, deleteSocial, getCreator, getMyCreator, getStatus, listCreators, saveCreator, updateProject, updateSocial, type CreatorInput } from "../services/creators/creatorApi";
import { reportReasons, submitReport } from "../services/reports/reportApi";
import { API_URL } from "../services/api/apiClient";
import { deleteAccount, updateProfileVisibility } from "../services/account/accountApi";
import { listReports, updateAdminCreatorVisibility, updateReportStatus, type ModerationReport } from "../services/admin/adminApi";
import authLogo from "../../assets/logo1.png";

const icons: Record<string, string> = { Artist: "🎨", Musician: "🎵", Developer: "💻", "Game Developer": "🎮", "Video Creator": "🎬", Writer: "✍️", Photographer: "📷", Designer: "✦", "3D Artist": "◒", Other: "✦" };
type AuthMode = "login" | "signup";
type ProfileStarter = Pick<CreatorInput, "displayName" | "username">;
type View = "home" | "discover" | "profile" | "onboarding" | "settings" | "admin" | "privacy" | "terms" | "guidelines" | "notfound";
const initials = (name: string) => name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase() || "U";
const isOwnershipVerified = (social: SocialAccount) => (social.platform === "GitHub" || social.platform === "Spotify") && social.ownershipVerified && social.verificationStatus === "verified";
const verifiedAccountLabel = (count: number) => `${count} linked account${count === 1 ? "" : "s"} ownership verified by UpNext`;

function VerificationSummary({ socials }: { socials: SocialAccount[] }) {
  const verifiedCount = socials.filter(isOwnershipVerified).length;
  return <section className="verification-summary" aria-label="Account verification"><p className="verification-summary-title">Account verification</p><p>{socials.length} linked account{socials.length === 1 ? "" : "s"} · {verifiedCount} ownership verified</p>{socials.length > 0 && <div>{socials.map((social) => <div key={social.id}><span>{social.platform}</span><span className={isOwnershipVerified(social) ? "ownership-verified" : "ownership-linked"}>{isOwnershipVerified(social) ? "✓ Ownership verified" : "Linked"}</span></div>)}</div>}</section>;
}

function AuthModal({ mode, onClose, onSuccess, onChangeMode }: { mode: AuthMode; onClose: () => void; onSuccess: (user: AuthUser) => void; onChangeMode: (mode: AuthMode) => void }) {
  const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [error, setError] = useState(""); const [loading, setLoading] = useState(false);
  const isLogin = mode === "login";
  async function submit(event: React.FormEvent) { event.preventDefault(); setError(""); setLoading(true); try { onSuccess(isLogin ? await authProvider.signIn(email, password) : await authProvider.signUp(email, password)); } catch (err) { setError(err instanceof Error ? err.message : "Please try again."); } finally { setLoading(false); } }
  return <div className="auth-overlay" role="dialog" aria-modal="true" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section className="auth-modal"><button className="auth-close" onClick={onClose} aria-label="Close">×</button><div className="auth-heading"><span className="auth-mark">upnext<span>.</span></span><p className="eyebrow">{isLogin ? "WELCOME BACK" : "JOIN UPNEXT"}</p><h2>{isLogin ? "Welcome back." : "Build your creator profile."}</h2><p>{isLogin ? "Log in to manage your work." : "Your session is stored securely by the server."}</p></div><form className="auth-form" onSubmit={submit}><label><span>Email</span><input type="email" required autoFocus autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label><label><span>Password</span><input type="password" required minLength={isLogin ? undefined : 8} autoComplete={isLogin ? "current-password" : "new-password"} value={password} onChange={(event) => setPassword(event.target.value)} /></label>{error && <div className="auth-error" role="alert">{error}</div>}<button className="auth-submit" disabled={loading}>{loading ? "Please wait…" : isLogin ? "Log in" : "Create account"}</button></form><div className="auth-switch"><span>{isLogin ? "New here?" : "Already have an account?"}</span><button onClick={() => onChangeMode(isLogin ? "signup" : "login")}>{isLogin ? "Create one" : "Log in"}</button></div></section></div>;
}

function PublicAuthLanding({ onAuth }: { onAuth: (mode: AuthMode) => void }) {
  return <main className="public-landing"><section className="public-landing-card"><span className="auth-mark">upnext<span>.</span></span><p className="eyebrow">EMERGING CREATOR DISCOVERY</p><h1>Discover emerging creators <em>before everyone else does.</em></h1><p className="public-landing-copy">UpNext is a work-first place to find artists, developers, writers, and builders while their work is still taking shape.</p><div className="public-landing-actions"><button className="secondary" onClick={() => onAuth("login")}>Log in</button><button className="join" onClick={() => onAuth("signup")}>Sign up <span>→</span></button></div><p className="public-landing-note">No feeds. No follower-chasing. Just thoughtful work.</p></section></main>;
}

function PublicAuthExperience({ mode, onChangeMode, onSuccess }: { mode: AuthMode; onChangeMode: (mode: AuthMode) => void; onSuccess: (user: AuthUser, starter?: ProfileStarter) => void }) {
  const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [displayName, setDisplayName] = useState(""); const [username, setUsername] = useState(""); const [error, setError] = useState(""); const [loading, setLoading] = useState(false);
  const isLogin = mode === "login";
  useEffect(() => setError(""), [mode]);
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setError(""); setLoading(true);
    try {
      const user = isLogin ? await authProvider.signIn(email, password) : await authProvider.signUp(email, password);
      onSuccess(user, isLogin ? undefined : { displayName: displayName.trim(), username: username.trim().toLowerCase() });
    } catch (err) { setError(err instanceof Error ? err.message : "Please try again."); } finally { setLoading(false); }
  }
  return <main className="public-auth">
    <section className="public-auth-left">
      <section className="public-auth-intro" aria-label="UpNext"><p className="public-auth-kicker">A work-in-progress directory for emerging creators</p><p className="public-auth-note">Make a place for your work before the crowd arrives.</p></section>
      <section className="public-auth-form-wrap" aria-labelledby="public-auth-title">
      <div className="public-auth-form-heading"><p className="public-auth-eyebrow">{isLogin ? "WELCOME BACK" : "JOIN THE DIRECTORY"}</p><h1 id="public-auth-title">{isLogin ? "Pick up where your work left off." : "Put your work on the map."}</h1><p>{isLogin ? "Log in to shape your profile and keep your links current." : "Start with the basics. You can finish shaping your public profile inside UpNext."}</p></div>
      <form className="public-auth-form" onSubmit={submit} key={mode}>
        {!isLogin && <div className="public-auth-name-row"><label><span>Display name</span><input required autoComplete="name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="How should people know you?" /></label><label><span>Username</span><input required pattern="[a-z0-9][a-z0-9_.-]{1,28}[a-z0-9]" autoCapitalize="none" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value.toLowerCase())} placeholder="your-handle" /></label></div>}
        <label><span>Email</span><input type="email" required autoFocus autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" /></label>
        <label><span>Password</span><input type="password" required minLength={isLogin ? undefined : 8} autoComplete={isLogin ? "current-password" : "new-password"} value={password} onChange={(event) => setPassword(event.target.value)} placeholder={isLogin ? "Your password" : "At least 8 characters"} /></label>
        {error && <div className="public-auth-error" role="alert">{error}</div>}
        <button className="public-auth-submit" disabled={loading}>{loading ? "Working…" : isLogin ? "Log in" : "Create your account"}<span aria-hidden="true">↗</span></button>
      </form>
      <p className="public-auth-switch">{isLogin ? "New here?" : "Already have an account?"} <button type="button" onClick={() => onChangeMode(isLogin ? "signup" : "login")}>{isLogin ? "Sign up" : "Log in"}</button></p>
      {!isLogin && <p className="public-auth-profile-note">Your display name and username will be ready in your profile setup after you join.</p>}
      </section>
    </section>
    <aside className="public-auth-art" aria-hidden="true">
      <div className="public-auth-paper" />
      <div className="public-auth-arc public-auth-arc-top" />
      <div className="public-auth-arc public-auth-arc-bottom" />
      <div className="public-auth-dotfield" />
      <div className="public-auth-scribble" />
      <div className="public-auth-brand"><img src={authLogo} alt="" /><span className="brand-cut brand-cut-one" /><span className="brand-cut brand-cut-two" /><span className="brand-arrow">↗</span></div>
    </aside>
  </main>;
}

function ReportModal({ creator, onClose }: { creator: Creator; onClose: () => void }) {
  const [reason, setReason] = useState(""); const [details, setDetails] = useState(""); const [message, setMessage] = useState(""); const [loading, setLoading] = useState(false);
  async function submit(event: React.FormEvent) { event.preventDefault(); setLoading(true); try { await submitReport(creator.id, reason, details); setMessage("Thanks. Your report has been received."); } catch (err) { setMessage(err instanceof Error ? err.message : "Could not submit the report."); } finally { setLoading(false); } }
  return <div className="auth-overlay" role="dialog" aria-modal="true"><section className="auth-modal compact"><button className="auth-close" onClick={onClose} aria-label="Close">×</button><div className="auth-heading"><p className="eyebrow">REPORT PROFILE</p><h2>Help keep UpNext useful.</h2></div>{message ? <p>{message}</p> : <form className="auth-form" onSubmit={submit}><label><span>Reason</span><select required value={reason} onChange={(event) => setReason(event.target.value)}><option value="">Select a reason</option>{reportReasons.map((value) => <option value={value} key={value}>{value.replaceAll("_", " ")}</option>)}</select></label><label><span>Details (optional)</span><textarea value={details} onChange={(event) => setDetails(event.target.value)} /></label><button className="auth-submit" disabled={loading}>{loading ? "Sending…" : "Submit report"}</button></form>}</section></div>;
}

function Profile({ creator, onBack, onReport }: { creator: Creator; onBack: () => void; onReport: () => void }) {
  const primary = creator.website || creator.socialAccounts[0]?.profileUrl;
  return <main className="profile-wrap"><button className="back" onClick={onBack}>← Back to discovery</button><section className="profile-hero"><div className="avatar large">{creator.avatar || initials(creator.displayName)}</div><div><h1>{creator.displayName}</h1><p className="handle">@{creator.username}{creator.location && ` · ${creator.location}`}</p><p className="profile-bio">{creator.bio}</p><div className="chips">{creator.categories.map((category) => <span key={category}>{icons[category]} {category}</span>)}</div>{primary && <a className="primary-link" target="_blank" rel="noreferrer" href={primary}>Visit portfolio ↗</a>}</div></section><section className="profile-grid"><div><h2>Selected work</h2>{creator.projects.map((project) => <a className="project" key={project.id} href={project.url} target="_blank" rel="noreferrer"><span>{project.type}</span><h3>{project.title} ↗</h3><p>{project.description}</p></a>)}</div><aside>{creator.skills.length > 0 && <><h2>Skills</h2><div className="chips">{creator.skills.map((skill) => <span key={skill}>{skill}</span>)}</div></>}<h2>Looking for</h2><div className="chips">{creator.lookingFor.map((value) => <span key={value}>{value}</span>)}</div><h2>Find them</h2><div className="social-list">{creator.socialAccounts.map((social) => <a key={social.id} href={social.profileUrl} target="_blank" rel="noreferrer">{social.platform}: @{social.username}{isOwnershipVerified(social) && <small className="ownership-verified">✓ Ownership verified</small>} ↗</a>)}</div>{creator.verifiedSocialCount > 0 && <p className="public-verification-summary" title={verifiedAccountLabel(creator.verifiedSocialCount)}>✓ {creator.verifiedSocialCount} linked account{creator.verifiedSocialCount === 1 ? "" : "s"} verified</p>}<p className="verification-note">Ownership verification confirms control of a linked account, not identity, safety, or follower count.</p><button className="report" onClick={onReport}>Report this profile</button></aside></section></main>;
}

function CreatorCard({ creator, onOpen }: { creator: Creator; onOpen: (creator: Creator) => void }) {
  const primaryLink = creator.website || creator.socialAccounts[0]?.profileUrl;
  const platforms = creator.socialAccounts.slice(0, 2).map((social) => social.platform);
  const extraPlatforms = creator.socialAccounts.length - platforms.length;

  return <article className="creator-card">
    <button className="card-hit" onClick={() => onOpen(creator)} aria-label={`View ${creator.displayName}`} />
    <div className="avatar">{creator.avatar || initials(creator.displayName)}</div>
    <div className="card-body">
      <div className="card-top"><div><h3>{creator.displayName}</h3><p>@{creator.username}</p></div></div>
      <div className="chips">{creator.categories.map((value) => <span key={value}>{icons[value]} {value}</span>)}</div>
      <p className="bio">{creator.bio}</p>
      <div className="card-meta">
        <span>{platforms.length ? `${platforms.join(" · ")}${extraPlatforms > 0 ? ` +${extraPlatforms}` : ""}` : "Portfolio"}</span>
        {creator.verifiedSocialCount > 0 && <small className="card-verification" title={verifiedAccountLabel(creator.verifiedSocialCount)}>✓ {creator.verifiedSocialCount} verified account{creator.verifiedSocialCount === 1 ? "" : "s"}</small>}
      </div>
      {primaryLink && <div className="card-action"><a href={primaryLink} onClick={(event) => event.stopPropagation()} target="_blank" rel="noreferrer">Visit work ↗</a></div>}
    </div>
  </article>;
}

function HomeWorkCard({ creator, onOpen }: { creator: Creator; onOpen: (creator: Creator) => void }) {
  const project = creator.projects[0];
  const workTitle = project?.title || creator.displayName;
  const workDescription = project?.description || creator.bio;
  const workType = project?.type || creator.categories[0] || "Creator work";

  return <article className="home-work-card">
    <button className="home-work-hit" onClick={() => onOpen(creator)} aria-label={`Open ${workTitle} by ${creator.displayName}`} />
    <div className="home-work-rule" aria-hidden="true" />
    <div className="home-work-main"><p className="home-work-type">{workType}</p><h3>{workTitle}</h3><p className="home-work-description">{workDescription}</p></div>
    <footer className="home-work-footer"><div><span className="home-work-by">By</span><strong>{creator.displayName}</strong><span>@{creator.username}</span></div><span className="home-work-categories">{creator.categories.slice(0, 2).join(" · ")}</span></footer>
  </article>;
}

function DiscoverWorkItem({ creator, onOpen }: { creator: Creator; onOpen: (creator: Creator) => void }) {
  const project = creator.projects[0];
  const workTitle = project?.title || "Work in progress";
  const workType = project?.type || creator.categories[0] || "Creator practice";

  return <article className="discover-work-item">
    <section className="discover-creator-context">
      <div className="discover-creator-top"><div className="avatar">{creator.avatar || initials(creator.displayName)}</div><div><p className="discover-context-label">Made by</p><h2>{creator.displayName}</h2><p className="discover-handle">@{creator.username}</p></div></div>
      <p className="discover-context-type">{workType}</p>
      <p className="discover-context-bio">{creator.bio || "An emerging creator building work worth a closer look."}</p>
      {creator.categories.length > 0 && <p className="discover-context-categories">{creator.categories.slice(0, 3).join(" / ")}</p>}
      <button className="discover-profile-link" onClick={() => onOpen(creator)}>Open profile <span aria-hidden="true">&rarr;</span></button>
    </section>
    <section className="discover-work-canvas" aria-label={`${workTitle} work preview`}>
      <div className="discover-work-placeholder" aria-hidden="true"><span className="work-mark work-mark-one" /><span className="work-mark work-mark-two" /><span className="work-mark work-mark-three" /></div>
      <div className="discover-work-caption"><p>WORK PREVIEW</p><h3>{workTitle}</h3>{project?.description && <span>{project.description}</span>}</div>
    </section>
  </article>;
}

function CreatorGridSkeleton({ count = 3 }: { count?: number }) {
  return <div className="creator-grid" aria-label="Loading creators">{Array.from({ length: count }, (_, index) => <div className="creator-card-skeleton" key={index} aria-hidden="true"><span /><div><i /><i /><i /></div></div>)}</div>;
}

function TagChoices({ values, options, onChange, freeText = false }: { values: string[]; options?: readonly string[]; onChange: (values: string[]) => void; freeText?: boolean }) {
  const [draft, setDraft] = useState(""); const toggle = (value: string) => onChange(values.includes(value) ? values.filter((item) => item !== value) : [...values, value]);
  return <><div className="tag-choices">{options?.map((option) => <button type="button" className={values.includes(option) ? "selected" : ""} onClick={() => toggle(option)} key={option}>{option}</button>)}</div>{freeText && <div className="tag-add"><input value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Add a skill" /><button type="button" onClick={() => { const value = draft.trim(); if (value && !values.includes(value)) onChange([...values, value]); setDraft(""); }}>Add</button></div>}{freeText && values.length > 0 && <div className="chips">{values.map((value) => <span key={value}>{value} <button type="button" onClick={() => toggle(value)}>×</button></span>)}</div>}</>;
}

function ProjectList({ projects, onChange, onStatus }: { projects: Project[]; onChange: (projects: Project[]) => void; onStatus: () => Promise<unknown> }) {
  const [editing, setEditing] = useState<Project | null>(null); const [error, setError] = useState(""); const [saving, setSaving] = useState(false);
  async function save() { if (!editing) return; setSaving(true); setError(""); try { const updated = await updateProject(editing.id, editing); onChange(projects.map((project) => project.id === updated.id ? updated : project)); setEditing(null); await onStatus(); } catch (err) { setError(err instanceof Error ? err.message : "Could not update project."); } finally { setSaving(false); } }
  async function remove(id: number) { setSaving(true); setError(""); try { await deleteProject(id); onChange(projects.filter((project) => project.id !== id)); await onStatus(); } catch (err) { setError(err instanceof Error ? err.message : "Could not remove project."); } finally { setSaving(false); } }
  return <><div className="item-list">{projects.map((project) => <div key={project.id}><strong>{project.title}</strong><span><button type="button" onClick={() => setEditing({ ...project })}>Edit</button><button type="button" onClick={() => remove(project.id)} disabled={saving}>Remove</button></span></div>)}</div>{editing && <div className="edit-panel"><h3>Edit project</h3><label>Title<input value={editing.title} onChange={(event) => setEditing({ ...editing, title: event.target.value })} /></label><label>Type<input value={editing.type} onChange={(event) => setEditing({ ...editing, type: event.target.value })} /></label><label>URL<input value={editing.url} onChange={(event) => setEditing({ ...editing, url: event.target.value })} /></label><label>Description<textarea value={editing.description} onChange={(event) => setEditing({ ...editing, description: event.target.value })} /></label><div><button className="secondary" type="button" onClick={() => setEditing(null)}>Cancel</button><button className="secondary" type="button" disabled={saving} onClick={save}>{saving ? "Saving…" : "Save changes"}</button></div></div>}{error && <div className="auth-error">{error}</div>}</>;
}

function SocialList({ socials, onChange, onStatus }: { socials: SocialAccount[]; onChange: (socials: SocialAccount[]) => void; onStatus: () => Promise<unknown> }) {
  const [editing, setEditing] = useState<SocialAccount | null>(null); const [error, setError] = useState(""); const [saving, setSaving] = useState(false);
  const verificationProvider = (social: SocialAccount) => social.platform === "GitHub" || social.platform === "Spotify" ? social.platform.toLowerCase() : null;
  async function save() { if (!editing) return; setSaving(true); setError(""); try { const updated = await updateSocial(editing.id, editing); onChange(socials.map((social) => social.id === updated.id ? updated : social)); setEditing(null); await onStatus(); } catch (err) { setError(err instanceof Error ? err.message : "Could not update account."); } finally { setSaving(false); } }
  async function remove(id: number) { setSaving(true); setError(""); try { await deleteSocial(id); onChange(socials.filter((social) => social.id !== id)); await onStatus(); } catch (err) { setError(err instanceof Error ? err.message : "Could not remove account."); } finally { setSaving(false); } }
  return <><div className="item-list">{socials.map((social) => { const provider = verificationProvider(social); const verified = isOwnershipVerified(social); return <div className="managed-social" key={social.id}><div><strong>{social.platform}</strong><a href={social.profileUrl} target="_blank" rel="noreferrer">{social.profileUrl}</a><small className={verified ? "ownership-verified" : "ownership-linked"}>{verified ? "✓ Ownership verified" : "Linked"}</small></div><span>{provider && !verified && <button className={`verify-${provider}`} type="button" onClick={() => { window.location.assign(`${API_URL}/api/creator/socials/${social.id}/verify/${provider}`); }}>Verify ownership</button>}<button type="button" onClick={() => setEditing({ ...social })}>Edit</button><button type="button" onClick={() => remove(social.id)} disabled={saving}>Remove</button></span></div>; })}</div><VerificationSummary socials={socials} />{editing && <div className="edit-panel"><h3>Edit account</h3><label>Platform<select value={editing.platform} onChange={(event) => setEditing({ ...editing, platform: event.target.value })}>{socialPlatforms.map((platform) => <option key={platform}>{platform}</option>)}</select></label><label>Username<input value={editing.username} onChange={(event) => setEditing({ ...editing, username: event.target.value })} /></label><label>Profile URL<input value={editing.profileUrl} onChange={(event) => setEditing({ ...editing, profileUrl: event.target.value })} /></label><div><button className="secondary" type="button" onClick={() => setEditing(null)}>Cancel</button><button className="secondary" type="button" disabled={saving} onClick={save}>{saving ? "Saving…" : "Save changes"}</button></div></div>}{error && <div className="auth-error">{error}</div>}</>;
}

function Onboarding({ existing, starter, onDone, onCancel }: { existing: Creator | null; starter: ProfileStarter | null; onDone: () => void; onCancel: () => void }) {
  const [step, setStep] = useState(0); const [error, setError] = useState(""); const [saving, setSaving] = useState(false); const [creatorExists, setCreatorExists] = useState(Boolean(existing));
  const [form, setForm] = useState<CreatorInput>({ displayName: existing?.displayName || starter?.displayName || "", username: existing?.username || starter?.username || "", bio: existing?.bio || "", avatar: existing?.avatar || "", location: existing?.location || "", website: existing?.website || "", categories: existing?.categories || [], skills: existing?.skills || [], lookingFor: existing?.lookingFor || [] });
  const [projects, setProjects] = useState<Project[]>(existing?.projects || []); const [socials, setSocials] = useState<SocialAccount[]>(existing?.socialAccounts || []); const [status, setStatus] = useState(existing?.publishability); const [project, setProject] = useState({ title: "", description: "", type: "", url: "" }); const [social, setSocial] = useState({ platform: "", username: "", profileUrl: "" });
  const titles = ["About you", "What you create", "Skills", "Looking for", "Projects", "Social accounts", "Review"];
  const patch = (value: Partial<CreatorInput>) => setForm((current) => ({ ...current, ...value }));
  async function refreshStatus() { const current = await getStatus(); setStatus(current); return current; }
  async function saveCore() { const creator = await saveCreator(form, creatorExists); setCreatorExists(true); return creator; }
  async function next() { setError(""); if (step === 0 && (!form.displayName || !form.username || !form.bio)) return setError("Display name, username, and bio are required."); if (step === 1 && !form.categories.length) return setError("Choose at least one category."); if (step === 2 && !form.skills.length) return setError("Add at least one skill."); setSaving(true); try { if (step <= 3) await saveCore(); if (step === 5) await refreshStatus(); setStep((value) => Math.min(value + 1, 6)); } catch (err) { setError(err instanceof Error ? err.message : "Could not save your profile."); } finally { setSaving(false); } }
  async function addProject() { setError(""); setSaving(true); try { if (!creatorExists) await saveCore(); const added = await createProject(project); setProjects((items) => [...items, added]); setProject({ title: "", description: "", type: "", url: "" }); await refreshStatus(); } catch (err) { setError(err instanceof Error ? err.message : "Could not add project."); } finally { setSaving(false); } }
  async function addSocial() { setError(""); setSaving(true); try { if (!creatorExists) await saveCore(); const added = await createSocial(social); setSocials((items) => [...items, added]); setSocial({ platform: "", username: "", profileUrl: "" }); await refreshStatus(); } catch (err) { setError(err instanceof Error ? err.message : "Could not add account."); } finally { setSaving(false); } }
  const missingMessage = (value: string) => value === "project" ? "Add at least one project to continue." : value === "social_account" ? "Connect at least one profile to continue." : `Complete ${value.replaceAll("_", " ")}.`;
  return <main className="onboarding"><button className="back" onClick={onCancel}>← Back</button><p className="eyebrow">{existing ? "EDIT PROFILE" : "CREATE PROFILE"}</p><h1>{titles[step]}</h1><p className="onboarding-sub">Step {step + 1} of {titles.length}</p><div className="stepper">{titles.map((title, index) => <span className={index === step ? "active" : index < step ? "done" : ""} key={title}>{index + 1}</span>)}</div><section className="onboarding-card">{step === 0 && <div className="form-grid"><label>Display name<input value={form.displayName} onChange={(event) => patch({ displayName: event.target.value })} /></label><label>Username<input value={form.username} onChange={(event) => patch({ username: event.target.value.toLowerCase() })} /><small>3–30 lowercase characters; dots, dashes, and underscores allowed.</small></label><label className="full">Bio<textarea value={form.bio} onChange={(event) => patch({ bio: event.target.value })} /></label><label>Location <small>(optional)</small><input value={form.location} onChange={(event) => patch({ location: event.target.value })} /></label><label>Website <small>(optional)</small><input value={form.website} onChange={(event) => patch({ website: event.target.value })} placeholder="https://" /></label></div>}{step === 1 && <TagChoices values={form.categories} options={categories} onChange={(values) => patch({ categories: values })} />}{step === 2 && <TagChoices values={form.skills} freeText onChange={(values) => patch({ skills: values })} />}{step === 3 && <TagChoices values={form.lookingFor} options={lookingForOptions} onChange={(values) => patch({ lookingFor: values })} />}{step === 4 && <><div className="form-grid"><label>Project title<input value={project.title} onChange={(event) => setProject({ ...project, title: event.target.value })} /></label><label>Type<input value={project.type} onChange={(event) => setProject({ ...project, type: event.target.value })} placeholder="Website, game, EP…" /></label><label className="full">URL<input value={project.url} onChange={(event) => setProject({ ...project, url: event.target.value })} placeholder="https://" /></label><label className="full">Description <small>(optional)</small><textarea value={project.description} onChange={(event) => setProject({ ...project, description: event.target.value })} /></label></div><button className="secondary" type="button" disabled={saving} onClick={addProject}>Add project</button><ProjectList projects={projects} onChange={setProjects} onStatus={refreshStatus} /></>}{step === 5 && <><div className="form-grid"><label>Platform<select value={social.platform} onChange={(event) => setSocial({ ...social, platform: event.target.value })}><option value="">Select platform</option>{socialPlatforms.map((platform) => <option key={platform}>{platform}</option>)}</select></label><label>Username/handle<input value={social.username} onChange={(event) => setSocial({ ...social, username: event.target.value })} /></label><label className="full">Profile URL<input value={social.profileUrl} onChange={(event) => setSocial({ ...social, profileUrl: event.target.value })} placeholder="https://" /></label></div><button className="secondary" type="button" disabled={saving} onClick={addSocial}>Add account</button><SocialList socials={socials} onChange={setSocials} onStatus={refreshStatus} /></>}{step === 6 && <div className="review"><h2>{status?.publishable ? "Your profile is ready to be discovered." : "A few things are still needed."}</h2>{status?.publishable ? <p>It now appears in the public directory.</p> : <ul>{(status?.missing || []).map((value) => <li key={value}>{missingMessage(value)}</li>)}</ul>}<VerificationSummary socials={socials} /><button className="secondary" type="button" onClick={async () => { try { await refreshStatus(); } catch (err) { setError(err instanceof Error ? err.message : "Could not check your profile."); } }}>Refresh status</button><button className="primary-link" disabled={!status?.publishable} onClick={onDone}>{status?.publishable ? "Finish" : "Finish unavailable"}</button></div>}{error && <div className="auth-error" role="alert">{error}</div>}{step < 6 && <div className="onboarding-actions"><button className="secondary" type="button" disabled={step === 0 || saving} onClick={() => setStep((value) => Math.max(value - 1, 0))}>Back</button><button className="auth-submit next" type="button" disabled={saving} onClick={next}>{saving ? "Saving…" : step === 5 ? "Review profile" : "Continue"}</button></div>}</section></main>;
}

function Header({ user, activeView, onAuth, onHome, onDiscover, onProfile, onSettings, onAdmin, onLogout }: { user: AuthUser | null; activeView: View; onAuth: (mode: AuthMode) => void; onHome: () => void; onDiscover: () => void; onProfile: () => void; onSettings: () => void; onAdmin: () => void; onLogout: () => void }) {
  const [open, setOpen] = useState(false);
  return <header className="site-header">
    <button className="brand site-logo-button" onClick={onHome} aria-label="UpNext home"><img className="site-logo" src={authLogo} alt="UpNext" /></button>
    <nav className="primary-nav" aria-label="Primary navigation">
      <button className={`nav-link ${activeView === "home" ? "active" : ""}`} onClick={onHome}>Home</button>
      <button className={`nav-link ${activeView === "discover" ? "active" : ""}`} onClick={onDiscover}>Discover</button>
      {user && <button className={`nav-link profile-nav-link ${activeView === "onboarding" ? "active" : ""}`} onClick={onProfile}>Your profile</button>}
    </nav>
    {user ? <div className="account-area"><button className="account-button" onClick={() => setOpen(!open)} aria-expanded={open}><span className="account-avatar">{user.email[0].toUpperCase()}</span><span className="account-email">{user.email}</span><span className="account-chevron" aria-hidden="true">⌄</span></button>{open && <div className="account-menu"><div className="account-menu-user"><span>Signed in as</span><strong>{user.email}</strong></div><button onClick={() => { setOpen(false); onProfile(); }}>Create or edit profile</button><button onClick={() => { setOpen(false); onSettings(); }}>Account settings</button>{user.is_admin && <button onClick={() => { setOpen(false); onAdmin(); }}>Moderation</button>}<button onClick={onLogout}>Log out</button></div>}</div> : <div className="header-actions"><button className="login-header" onClick={() => onAuth("login")}>Log in</button><button className="join" onClick={() => onAuth("signup")}>Join UpNext <span>→</span></button></div>}
  </header>;
}

function Settings({ creator, onBack, onCreatorUpdated, onDeleted }: { creator: Creator | null; onBack: () => void; onCreatorUpdated: (creator: Creator) => void; onDeleted: () => void }) {
  const [confirmDelete, setConfirmDelete] = useState(false); const [saving, setSaving] = useState(false); const [error, setError] = useState("");
  async function setVisibility(isPublic: boolean) { setSaving(true); setError(""); try { onCreatorUpdated(await updateProfileVisibility(isPublic)); } catch (err) { setError(err instanceof Error ? err.message : "Could not update profile visibility."); } finally { setSaving(false); } }
  async function removeAccount() { setSaving(true); setError(""); try { await deleteAccount(); onDeleted(); } catch (err) { setError(err instanceof Error ? err.message : "Could not delete your account."); } finally { setSaving(false); } }
  return <main className="settings-wrap"><button className="back" onClick={onBack}>← Back to discovery</button><p className="eyebrow">ACCOUNT SETTINGS</p><h1>Control your presence.</h1><section className="settings-section"><h2>Public profile</h2>{creator ? <><p>{creator.isPublic ? "Your publishable profile is currently visible in discovery." : "Your profile is hidden from public discovery."}</p><button className="secondary" disabled={saving || (!creator.isPublic && !creator.publishability.publishable)} onClick={() => setVisibility(!creator.isPublic)}>{creator.isPublic ? "Unpublish profile" : "Publish profile"}</button>{!creator.isPublic && !creator.publishability.publishable && <p className="settings-note">Complete the required profile sections before publishing.</p>}</> : <p>Create a creator profile to control its public visibility.</p>}</section><section className="settings-section danger-zone"><h2>Delete account</h2><p>This permanently removes your account, creator profile, projects, social links, and associated data.</p><label className="confirm-delete"><input type="checkbox" checked={confirmDelete} onChange={(event) => setConfirmDelete(event.target.checked)} /> I understand this cannot be undone.</label><button className="report" disabled={!confirmDelete || saving} onClick={removeAccount}>{saving ? "Deleting…" : "Delete account"}</button></section>{error && <p className="auth-error" role="alert">{error}</p>}</main>;
}

function LegalPage({ kind, onBack }: { kind: "privacy" | "terms" | "guidelines"; onBack: () => void }) {
  const content = kind === "privacy" ? ["Privacy Policy", "UpNext stores account and login information, creator profiles, projects, linked social profile information, ownership-verification status, reports, and necessary session and security data to operate the directory.", "GitHub and Spotify OAuth are used only to verify ownership of a linked account. UpNext does not retain provider access tokens after that verification flow completes."] : kind === "terms" ? ["Terms of Service", "Use UpNext lawfully and provide accurate information about your work and linked accounts. Ownership verification only confirms control of a linked platform account; it is not an identity, safety, or quality guarantee.", "These launch materials are a concise product notice and should be reviewed with qualified legal counsel before broader use."] : ["Community Guidelines", "Keep profiles and projects respectful, accurate, and relevant to creator discovery. Do not impersonate others, harass people, post inappropriate material, or misuse verification.", "Anyone can report a profile. Ownership verification does not prevent moderation action."];
  return <main className="legal-wrap"><button className="back" onClick={onBack}>← Back to discovery</button><p className="eyebrow">UPNEXT</p><h1>{content[0]}</h1><p>{content[1]}</p><p>{content[2]}</p></main>;
}

function Moderation({ onBack }: { onBack: () => void }) {
  const [reports, setReports] = useState<ModerationReport[]>([]); const [error, setError] = useState(""); const [loading, setLoading] = useState(true);
  const load = async () => { setLoading(true); setError(""); try { setReports(await listReports()); } catch (err) { setError(err instanceof Error ? err.message : "Could not load reports."); } finally { setLoading(false); } };
  useEffect(() => { void load(); }, []);
  async function setStatus(report: ModerationReport, status: ModerationReport["status"]) { try { await updateReportStatus(report.id, status); setReports((items) => items.map((item) => item.id === report.id ? { ...item, status } : item)); } catch (err) { setError(err instanceof Error ? err.message : "Could not update report."); } }
  async function hideCreator(report: ModerationReport) { try { await updateAdminCreatorVisibility(report.creator_id, false); } catch (err) { setError(err instanceof Error ? err.message : "Could not hide profile."); } }
  return <main className="settings-wrap"><button className="back" onClick={onBack}>← Back to discovery</button><p className="eyebrow">MODERATION</p><h1>Reports</h1>{error && <p className="auth-error" role="alert">{error}</p>}{loading ? <p className="empty">Loading reports…</p> : reports.length ? <div className="moderation-list">{reports.map((report) => <section key={report.id} className="settings-section"><p><strong>@{report.username}</strong> · {report.reason.replaceAll("_", " ")} · {report.status}</p>{report.details && <p>{report.details}</p>}<p className="settings-note">Reported by {report.reporter_email} · {report.created_at}</p><div className="moderation-actions"><button className="secondary" onClick={() => setStatus(report, "dismissed")}>Dismiss</button><button className="secondary" onClick={() => setStatus(report, "actioned")}>Mark actioned</button><button className="report" onClick={() => hideCreator(report)}>Hide profile</button></div></section>)}</div> : <p className="empty">No reports to review.</p>}</main>;
}

type RouteState = { view: View; profileUsername: string | null };

function routeFromPath(): RouteState {
  const path = window.location.pathname.replace(/\/$/, "") || "/";
  const profile = path.match(/^\/profile\/([^/]+)$/);
  if (path === "/") return { view: "home", profileUsername: null };
  if (path === "/discover") return { view: "discover", profileUsername: null };
  if (profile) return { view: "profile", profileUsername: decodeURIComponent(profile[1]) };
  if (path === "/admin") return { view: "admin", profileUsername: null };
  if (path === "/privacy") return { view: "privacy", profileUsername: null };
  if (path === "/terms") return { view: "terms", profileUsername: null };
  if (path === "/community-guidelines") return { view: "guidelines", profileUsername: null };
  return { view: "notfound", profileUsername: null };
}

export function App() {
  const initialRoute = routeFromPath();
  const [user, setUser] = useState<AuthUser | null>(null); const [ready, setReady] = useState(false); const [auth, setAuth] = useState<AuthMode | null>(null); const [view, setView] = useState<View>(initialRoute.view); const [profileUsername, setProfileUsername] = useState<string | null>(initialRoute.profileUsername); const [creators, setCreators] = useState<Creator[]>([]); const [total, setTotal] = useState(0); const [selected, setSelected] = useState<Creator | null>(null); const [mine, setMine] = useState<Creator | null>(null); const [profileStarter, setProfileStarter] = useState<ProfileStarter | null>(null); const [search, setSearch] = useState(""); const [category, setCategory] = useState(""); const [sort, setSort] = useState("discover"); const [filterOpen, setFilterOpen] = useState(false); const [loading, setLoading] = useState(false); const [profileLoading, setProfileLoading] = useState(false); const [error, setError] = useState(""); const [profileError, setProfileError] = useState(""); const [reloadToken, setReloadToken] = useState(0); const [reporting, setReporting] = useState(false); const [pendingReport, setPendingReport] = useState<Creator | null>(null);
  const refreshDiscovery = () => setReloadToken((current) => current + 1);
  const navigate = (path: string, nextView: View, username: string | null = null) => { if (window.location.pathname !== path) window.history.pushState({}, "", path); setSelected(null); setProfileUsername(username); setView(nextView); };
  const goHome = () => navigate("/", "home");
  const goDiscover = () => navigate("/discover", "discover");
  useEffect(() => { authProvider.currentUser().then(setUser).catch(() => setUser(null)).finally(() => setReady(true)); }, []);
  useEffect(() => { const onPopState = () => { const route = routeFromPath(); setSelected(null); setProfileUsername(route.profileUsername); setView(route.view); }; window.addEventListener("popstate", onPopState); return () => window.removeEventListener("popstate", onPopState); }, []);
  useEffect(() => {
    const onInternalLink = (event: MouseEvent) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const link = (event.target as Element | null)?.closest<HTMLAnchorElement>("a[href]");
      if (!link || link.target || link.hasAttribute("download")) return;
      const target = new URL(link.href, window.location.origin);
      if (target.origin !== window.location.origin || !["/privacy", "/terms", "/community-guidelines"].includes(target.pathname)) return;
      event.preventDefault();
      window.history.pushState({}, "", target.pathname);
      const route = routeFromPath(); setSelected(null); setProfileUsername(route.profileUsername); setView(route.view);
    };
    document.addEventListener("click", onInternalLink);
    return () => document.removeEventListener("click", onInternalLink);
  }, []);
  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    const spotifyResult = query.get("spotify_verification");
    const result = spotifyResult || query.get("github_verification");
    if (!result) return;
    const provider = spotifyResult ? "Spotify" : "GitHub";
    const message = result === "success" ? `${provider} account verified.` : result === "denied" ? `${provider} verification was cancelled.` : `${provider} verification could not be completed.`;
    const notice = document.createElement("div"); notice.className = "oauth-notice"; notice.textContent = message; document.body.appendChild(notice);
    window.history.replaceState({}, "", `${window.location.pathname}${window.location.hash}`);
    if (result === "success") getMyCreator().then((creator) => { setMine(creator); setView("onboarding"); }).catch(() => setError("Your account was verified, but your profile could not be refreshed."));
    const timer = window.setTimeout(() => notice.remove(), 5000);
    return () => { window.clearTimeout(timer); notice.remove(); };
  }, []);
  const activeSearch = view === "discover" ? search : "";
  const activeCategory = view === "discover" ? category : "";
  const activeSort = view === "discover" ? sort : "discover";
  useEffect(() => {
    if (!user || (view !== "home" && view !== "discover")) return;
    let active = true;
    const timer = window.setTimeout(async () => {
      setLoading(true); setError("");
      try {
        const result = await listCreators({ search: activeSearch, category: activeCategory, sort: activeSort, limit: view === "home" ? 3 : 48 });
        if (active) { setCreators(result.creators); setTotal(result.total); }
      } catch (err) { if (active) setError(err instanceof Error ? err.message : "Could not load creators."); } finally { if (active) setLoading(false); }
    }, view === "discover" ? 180 : 0);
    return () => { active = false; window.clearTimeout(timer); };
  }, [user, view, activeSearch, activeCategory, activeSort, reloadToken]);
  useEffect(() => {
    if (!user || view !== "profile" || !profileUsername) return;
    let active = true;
    setProfileLoading(true); setProfileError("");
    getCreator(profileUsername).then((creator) => { if (active) setSelected(creator); }).catch((err) => { if (active) setProfileError(err instanceof Error ? err.message : "Could not open this creator profile."); }).finally(() => { if (active) setProfileLoading(false); });
    return () => { active = false; };
  }, [user, view, profileUsername]);
  async function beginProfile() { if (!user) { setAuth("signup"); return; } try { setMine(await getMyCreator()); setView("onboarding"); } catch (err) { setError(err instanceof Error ? err.message : "Could not load your profile."); } }
  async function openSettings() { if (!user) return; try { setMine(await getMyCreator()); setView("settings"); } catch (err) { setError(err instanceof Error ? err.message : "Could not load your account settings."); } }
  function openProfile(creator: Creator) { navigate(`/profile/${encodeURIComponent(creator.username)}`, "profile", creator.username); }
  function beginReport() { if (!selected) return; if (user) { setReporting(true); return; } setPendingReport(selected); setAuth("login"); }
  function completeAuth(authenticatedUser: AuthUser, starter?: ProfileStarter) { setUser(authenticatedUser); setProfileStarter(starter || null); setAuth(null); goHome(); if (pendingReport) { setReporting(true); setPendingReport(null); } }
  const closeAuth = () => { setAuth(null); setPendingReport(null); };
  const logout = async () => { await authProvider.signOut(); setUser(null); setMine(null); goHome(); };
  if (!ready) return <div className="app-loading"><span className="loading-brand">upnext<span>.</span></span></div>;
  if (!user) return <PublicAuthExperience mode={auth ?? "signup"} onChangeMode={setAuth} onSuccess={completeAuth} />;
  if (view === "onboarding") return <><header><button className="brand" onClick={goHome}>upnext<span>.</span></button></header><Onboarding existing={mine} starter={profileStarter} onCancel={goHome} onDone={() => { setProfileStarter(null); goHome(); refreshDiscovery(); }} /></>;
  const shellHeader = <Header user={user} activeView={view} onAuth={setAuth} onHome={goHome} onDiscover={goDiscover} onProfile={beginProfile} onSettings={openSettings} onAdmin={() => setView("admin")} onLogout={logout} />;
  if (Boolean(view === "discover")) return <>{shellHeader}<main className="discover-catalogue"><section className="discover-catalogue-intro"><div><p className="home-kicker">UPNEXT / DISCOVER</p><h1>Work worth <em>stopping for.</em></h1></div><p>Browse emerging practices, projects, and the people making them.</p></section><section className="discover-catalogue-tools" aria-label="Discover controls"><label className="discover-search"><span className="sr-only">Search creators</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search work, people, or skills" /></label><button className={`discover-filter-button ${filterOpen ? "is-open" : ""}`} onClick={() => setFilterOpen((open) => !open)} aria-expanded={filterOpen} aria-controls="discover-filters">Filter {category && <span>1</span>}</button></section>{filterOpen && <section className="discover-filter-drawer" id="discover-filters" aria-label="Discover filters"><header><div><p className="home-kicker">REFINE THE DIRECTORY</p><h2>Find a different angle.</h2></div><button className="discover-filter-close" onClick={() => setFilterOpen(false)} aria-label="Close filters">Close</button></header><div className="discover-filter-options"><div><p>Category</p><div className="discover-category-list"><button className={!category ? "active" : ""} onClick={() => setCategory("")}>All creators</button>{categories.map((value) => <button key={value} className={category === value ? "active" : ""} onClick={() => setCategory(value)}>{value}</button>)}</div></div><label className="discover-sort-control"><span>Sort by</span><select value={sort} onChange={(event) => setSort(event.target.value)}><option value="discover">Curated discovery</option><option value="recent">Recently added</option><option value="complete">Profile depth</option></select></label></div><footer>{category ? <button className="discover-clear-filter" onClick={() => setCategory("")}>Clear current filter</button> : <span>All creators are currently shown.</span>}<button className="discover-apply-filter" onClick={() => setFilterOpen(false)}>Show work <span aria-hidden="true">&rarr;</span></button></footer></section>}<div className="discover-catalogue-meta"><span>{loading ? "Updating the directory…" : `${total} creator${total === 1 ? "" : "s"}`}</span><span>{category ? `Showing ${category}` : "Selected by practice, not popularity."}</span></div><section className="discover-work-list" aria-live="polite">{error ? <p className="empty">{error}</p> : loading && !creators.length ? <CreatorGridSkeleton count={3} /> : creators.length ? creators.map((creator) => <DiscoverWorkItem key={creator.id} creator={creator} onOpen={openProfile} />) : <p className="empty">No creators match those filters. Try a broader search.</p>}</section></main><footer className="site-footer"><div><button className="brand" onClick={goHome}>upnext<span>.</span></button><p>Discover emerging creative talent.</p></div><nav className="footer-links" aria-label="Legal"><a href="/privacy">Privacy</a><a href="/terms">Terms</a><a href="/community-guidelines">Community guidelines</a></nav></footer></>;
  if (Boolean(view === "home")) return <>{shellHeader}<main className="home-page"><section className="home-quickstart"><div><h1>Find your next <span>favourite thing.</span></h1><p>Fresh projects and emerging creators, all in one place.</p></div><button className="home-discover-action" onClick={goDiscover}>Start exploring <span aria-hidden="true">&rarr;</span></button><div className="home-quickstart-mark" aria-hidden="true"><i /><b /></div></section><section className="home-work-section" aria-labelledby="home-work-heading"><header className="home-work-heading"><div><h2 id="home-work-heading">Fresh from the directory</h2><p>Open a project. Meet the person behind it. Keep looking.</p></div><button className="home-directory-link" onClick={goDiscover}>See everything <span aria-hidden="true">&rarr;</span></button></header>{error ? <p className="empty">{error}</p> : loading && !creators.length ? <CreatorGridSkeleton /> : creators.length ? <div className="home-work-grid">{creators.map((creator) => <HomeWorkCard key={creator.id} creator={creator} onOpen={openProfile} />)}</div> : <p className="empty">No published creators yet. Complete your profile to help get the directory started.</p>}</section></main><footer className="site-footer"><div><button className="brand" onClick={goHome}>upnext<span>.</span></button><p>Discover emerging creative talent.</p></div><nav className="footer-links" aria-label="Legal"><a href="/privacy">Privacy</a><a href="/terms">Terms</a><a href="/community-guidelines">Community guidelines</a></nav></footer></>;
  if (view === "settings") return <>{shellHeader}<Settings creator={mine} onBack={goHome} onCreatorUpdated={(creator) => { setMine(creator); refreshDiscovery(); }} onDeleted={() => { setUser(null); setMine(null); goHome(); }} /></>;
  if (view === "admin") return <>{shellHeader}{user?.is_admin ? <Moderation onBack={goHome} /> : <main className="legal-wrap"><p className="eyebrow">403</p><h1>Not authorized.</h1><p>This area is limited to site administrators.</p></main>}</>;
  if (view === "privacy" || view === "terms" || view === "guidelines") return <>{shellHeader}<LegalPage kind={view} onBack={goHome} /></>;
  if (view === "notfound") return <>{shellHeader}<main className="legal-wrap"><p className="eyebrow">404</p><h1>Page not found.</h1><p>The page you requested does not exist.</p><button className="secondary" onClick={goHome}>Go home</button></main></>;
  if (view === "profile") return <>{shellHeader}{profileLoading ? <main className="profile-wrap profile-loading"><p className="eyebrow">CREATOR PROFILE</p><div className="profile-skeleton"><span /><div><i /><i /><i /></div></div></main> : profileError ? <main className="profile-wrap"><p className="empty">{profileError}</p><button className="secondary" onClick={goDiscover}>Back to discovery</button></main> : selected ? <Profile creator={selected} onBack={goDiscover} onReport={beginReport} /> : null}{reporting && selected && <ReportModal creator={selected} onClose={() => setReporting(false)} />}</>;
  if (view === "home") return <>{shellHeader}<main><section className="intro home-intro"><p className="eyebrow">YOUR CREATOR DIRECTORY</p><h1>Find the work<br /><em>worth noticing early.</em></h1><p>Explore thoughtful work from emerging artists, builders, writers and more. No feeds. No follower-chasing.</p></section><section className="discovery discovery-preview"><div className="section-heading"><div><p className="eyebrow">DISCOVER</p><h2>A few creators to explore</h2></div><button className="discover-more" onClick={goDiscover}>Discover more <span>→</span></button></div><p className="section-copy">A small selection from the directory. Browse the full collection when you are ready.</p>{error ? <p className="empty">{error}</p> : loading && !creators.length ? <CreatorGridSkeleton /> : creators.length ? <div className="creator-grid creator-grid-preview">{creators.map((creator) => <CreatorCard key={creator.id} creator={creator} onOpen={openProfile} />)}</div> : <p className="empty">No published creators yet. Complete your profile to help get the directory started.</p>}</section></main><footer><div><button className="brand" onClick={goHome}>upnext<span>.</span></button><p>Discover emerging creative talent.</p></div><nav className="footer-links" aria-label="Legal"><a href="/privacy">Privacy</a><a href="/terms">Terms</a><a href="/community-guidelines">Community guidelines</a></nav></footer></>;
  if (view === "discover") return <>{shellHeader}<main><section className="discover-page-heading"><p className="eyebrow">DISCOVER</p><h1>Find the work worth noticing early.</h1><p>Search emerging creators by their craft, skills, projects, and what they are looking for next.</p></section><section className="discovery discovery-full"><div className="discover-controls"><label className="search"><span>⌕</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search people, skills or projects" /></label><label className="sort-control"><span>Sort by</span><select value={sort} onChange={(event) => setSort(event.target.value)}><option value="discover">Curated discovery</option><option value="recent">Recently added</option><option value="complete">Profile depth</option></select></label></div><div className="filter-panel"><div><p>Browse by category</p><span>Refine the directory without changing its work-first ranking.</span></div><div className="filters"><button className={!category ? "active" : ""} onClick={() => setCategory("")}>All creators</button>{categories.map((value) => <button key={value} className={category === value ? "active" : ""} onClick={() => setCategory(value)}>{icons[value]} {value}</button>)}</div>{category && <button className="clear-filter" onClick={() => setCategory("")}>Clear {category}</button>}</div><div className="result-meta"><span>{loading ? "Updating results…" : `${total} creator${total === 1 ? "" : "s"}`}</span><span>{category ? `Showing ${category}` : "Work-first discovery, not popularity ranking."}</span></div>{error ? <p className="empty">{error}</p> : loading && !creators.length ? <CreatorGridSkeleton count={6} /> : creators.length ? <div className="creator-grid">{creators.map((creator) => <CreatorCard key={creator.id} creator={creator} onOpen={openProfile} />)}</div> : <p className="empty">No creators match those filters. Try a broader search.</p>}</section></main><footer><div><button className="brand" onClick={goHome}>upnext<span>.</span></button><p>Discover emerging creative talent.</p></div><nav className="footer-links" aria-label="Legal"><a href="/privacy">Privacy</a><a href="/terms">Terms</a><a href="/community-guidelines">Community guidelines</a></nav></footer></>;
  return <>{shellHeader}<main><section className="intro"><p className="eyebrow">DISCOVER WHAT'S NEXT</p><h1>Meet the creators<br /><em>before the crowd does.</em></h1><p>Explore thoughtful work from emerging artists, builders, writers and more. No feeds. No follower-chasing.</p></section><section className="discovery"><div className="toolbar"><label className="search"><span>⌕</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search people, skills or projects" /></label><select value={sort} onChange={(event) => setSort(event.target.value)}><option value="discover">Curated discovery</option><option value="recent">Recently added</option><option value="complete">Profile depth</option></select></div><div className="filters"><button className={!category ? "active" : ""} onClick={() => setCategory("")}>All</button>{categories.map((value) => <button key={value} className={category === value ? "active" : ""} onClick={() => setCategory(value)}>{icons[value]} {value}</button>)}</div><div className="result-meta"><span>{loading ? "Loading creators…" : `${total} creators`}</span><span>Work-first discovery, not popularity ranking.</span></div>{error ? <p className="empty">{error}</p> : loading ? <p className="empty">Loading the directory…</p> : creators.length ? <div className="creator-grid">{creators.map((creator) => <article className="creator-card" key={creator.id}><button className="card-hit" onClick={() => openProfile(creator)} aria-label={`View ${creator.displayName}`} /><div className="avatar">{creator.avatar || initials(creator.displayName)}</div><div className="card-body"><div className="card-top"><div><h3>{creator.displayName}</h3><p>@{creator.username}</p></div></div><div className="chips">{creator.categories.map((value) => <span key={value}>{icons[value]} {value}</span>)}</div><p className="bio">{creator.bio}</p><div className="card-footer"><span>{creator.socialAccounts[0]?.platform || "Portfolio"}</span>{creator.verifiedSocialCount > 0 && <small className="card-verification" title={verifiedAccountLabel(creator.verifiedSocialCount)}>✓ {creator.verifiedSocialCount} verified account{creator.verifiedSocialCount === 1 ? "" : "s"}</small>}{(creator.website || creator.socialAccounts[0]) && <a href={creator.website || creator.socialAccounts[0].profileUrl} onClick={(event) => event.stopPropagation()} target="_blank" rel="noreferrer">Visit work ↗</a>}</div></div></article>)}</div> : <p className="empty">No published creators yet. Create a complete profile to be the first.</p>}</section></main><footer><div><button className="brand" onClick={() => window.location.assign("/")}>upnext<span>.</span></button><p>Discover emerging creative talent.</p></div><nav className="footer-links" aria-label="Legal"><a href="/privacy">Privacy</a><a href="/terms">Terms</a><a href="/community-guidelines">Community guidelines</a></nav></footer>{auth && <AuthModal mode={auth} onClose={closeAuth} onChangeMode={setAuth} onSuccess={completeAuth} />}</>;
}
