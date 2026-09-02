export const categories = ["Artist", "Musician", "Developer", "Game Developer", "Video Creator", "Writer", "Photographer", "Designer", "3D Artist", "Other"] as const;
export const socialPlatforms = ["Instagram", "TikTok", "YouTube", "GitHub", "Spotify", "X", "Twitch", "Behance", "Dribbble", "LinkedIn", "Website/Portfolio"] as const;
export const lookingForOptions = ["Collaborators", "Freelance work", "Full-time opportunities", "Studios", "Recruiters", "Clients", "Fans / audience", "Publishers", "Investors", "Other"] as const;
export type Category = (typeof categories)[number];
export type VerificationStatus = "unverified" | "identity_verified" | "eligibility_verified" | string;

export interface Project { id: number; title: string; description: string; url: string; type: string; createdAt?: string; updatedAt?: string; }
export interface SocialAccount { id: number; platform: string; username: string; profileUrl: string; verificationStatus: VerificationStatus; ownershipVerified: boolean; eligibilityVerified: boolean; followerCount?: number; verifiedAt?: string; }
export interface Publishability { publishable: boolean; missing: string[]; }
export interface Creator { id: number; displayName: string; username: string; bio: string; avatar: string; categories: Category[]; skills: string[]; location?: string; website?: string; lookingFor: string[]; projects: Project[]; socialAccounts: SocialAccount[]; createdAt: string; updatedAt: string; publishability: Publishability; verifiedSocialCount: number; profileStrength: number; }
