import type { SocialAccount, VerificationStatus } from "../../domain/creator";

export interface VerificationResult { status: VerificationStatus; followerCountAtVerification?: number; verifiedAt?: string; provider: string; }
export interface VerificationProvider { name: string; verifyAccount(account: Pick<SocialAccount, "platform" | "username" | "profileUrl">): Promise<VerificationResult>; }

/** Future integration boundary. It is currently unused, makes no network calls, and never verifies an account. */
export class UnconfiguredVerificationProvider implements VerificationProvider {
  name = "unconfigured";
  async verifyAccount(): Promise<VerificationResult> { return { status: "unverified", provider: this.name }; }
}
