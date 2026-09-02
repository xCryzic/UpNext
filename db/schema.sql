-- Archived V0 design reference. Do not apply this file: the runtime schema is
-- defined in backend/models.py and created through Alembic migrations.
CREATE TYPE verification_status AS ENUM ('unverified', 'identity_verified', 'eligibility_verified');
CREATE TYPE report_reason AS ENUM ('spam', 'impersonation', 'harassment', 'inappropriate_content', 'false_verification', 'other');
CREATE TYPE report_status AS ENUM ('open', 'reviewing', 'resolved', 'dismissed');
CREATE TABLE users (id UUID PRIMARY KEY, auth_subject TEXT UNIQUE NOT NULL, email TEXT UNIQUE, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE creator_profiles (id UUID PRIMARY KEY, user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE, display_name TEXT NOT NULL, username TEXT NOT NULL UNIQUE, bio TEXT NOT NULL DEFAULT '', avatar_url TEXT, website_url TEXT, location TEXT, categories TEXT[] NOT NULL DEFAULT '{}', skills TEXT[] NOT NULL DEFAULT '{}', looking_for TEXT[] NOT NULL DEFAULT '{}', created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX creator_profiles_username_idx ON creator_profiles (username);
CREATE INDEX creator_profiles_categories_idx ON creator_profiles USING GIN (categories);
CREATE TABLE social_accounts (id UUID PRIMARY KEY, creator_profile_id UUID NOT NULL REFERENCES creator_profiles(id) ON DELETE CASCADE, platform TEXT NOT NULL, username TEXT NOT NULL, profile_url TEXT NOT NULL, verification_status verification_status NOT NULL DEFAULT 'unverified', verification_provider TEXT, follower_count_at_verification INTEGER CHECK (follower_count_at_verification >= 0), verified_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE (platform, username));
CREATE INDEX social_accounts_creator_idx ON social_accounts (creator_profile_id);
CREATE TABLE projects (id UUID PRIMARY KEY, creator_profile_id UUID NOT NULL REFERENCES creator_profiles(id) ON DELETE CASCADE, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', url TEXT NOT NULL, type TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX projects_creator_idx ON projects (creator_profile_id);
CREATE TABLE reports (id UUID PRIMARY KEY, creator_profile_id UUID NOT NULL REFERENCES creator_profiles(id) ON DELETE CASCADE, reporter_id UUID REFERENCES users(id) ON DELETE SET NULL, reason report_reason NOT NULL, description TEXT NOT NULL DEFAULT '', status report_status NOT NULL DEFAULT 'open', created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX reports_profile_status_idx ON reports (creator_profile_id, status);
