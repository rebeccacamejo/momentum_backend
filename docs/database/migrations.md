# Database Migrations

This document outlines the required database migrations for the Momentum backend, including new tables for Zoom integration and any schema updates.

## Migration Overview

The following migrations are required to support the full Momentum backend functionality:

1. **Initial Schema**: Core tables for users, deliverables, and organizations
2. **Zoom Integration**: Tables for OAuth credentials and meeting data
3. **Brand Settings**: Customization and branding features
4. **Storage Buckets**: File storage configuration

## Required Migrations

### Migration 001: Initial Schema

**File**: `001_initial_schema.sql`

```sql
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Profiles table (extends Supabase auth.users)
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Deliverables table
CREATE TABLE deliverables (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    client_name TEXT NOT NULL,
    html TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Organizations table
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL CHECK (length(name) > 0),
    slug TEXT UNIQUE NOT NULL,
    logo_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Organization members table
CREATE TABLE organization_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, organization_id)
);

-- Brand settings table
CREATE TABLE brand_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    primary_color TEXT DEFAULT '#2A3EB1',
    secondary_color TEXT DEFAULT '#4C6FE7',
    logo_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_deliverables_user_created ON deliverables(user_id, created_at DESC);
CREATE INDEX idx_org_members_user ON organization_members(user_id);
CREATE INDEX idx_org_members_org ON organization_members(organization_id);

-- Enable Row Level Security
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE deliverables ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE brand_settings ENABLE ROW LEVEL SECURITY;

-- RLS Policies for profiles
CREATE POLICY "Users can view own profile" ON profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON profiles
    FOR UPDATE USING (auth.uid() = id);

-- RLS Policies for deliverables
CREATE POLICY "Users can manage own deliverables" ON deliverables
    FOR ALL USING (auth.uid() = user_id);

-- RLS Policies for organizations
CREATE POLICY "Members can view organization" ON organizations
    FOR SELECT USING (
        id IN (
            SELECT organization_id
            FROM organization_members
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Admins can update organization" ON organizations
    FOR UPDATE USING (
        id IN (
            SELECT organization_id
            FROM organization_members
            WHERE user_id = auth.uid() AND role IN ('owner', 'admin')
        )
    );

-- RLS Policies for organization members
CREATE POLICY "Members can view org membership" ON organization_members
    FOR SELECT USING (
        organization_id IN (
            SELECT organization_id
            FROM organization_members
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Admins can manage members" ON organization_members
    FOR ALL USING (
        organization_id IN (
            SELECT organization_id
            FROM organization_members
            WHERE user_id = auth.uid() AND role IN ('owner', 'admin')
        )
    );

-- RLS Policies for brand settings
CREATE POLICY "Users can manage own brand settings" ON brand_settings
    FOR ALL USING (auth.uid() = user_id OR user_id IS NULL);
```

### Migration 002: Zoom Integration

**File**: `002_zoom_integration.sql`

```sql
-- Zoom credentials table for OAuth integration
CREATE TABLE zoom_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    zoom_user_id TEXT,
    zoom_email TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for token expiration cleanup
CREATE INDEX idx_zoom_credentials_expires ON zoom_credentials(expires_at);
CREATE INDEX idx_zoom_credentials_user ON zoom_credentials(user_id);

-- Enable RLS on zoom_credentials
ALTER TABLE zoom_credentials ENABLE ROW LEVEL SECURITY;

-- RLS Policy for zoom credentials
CREATE POLICY "Users can manage own zoom credentials" ON zoom_credentials
    FOR ALL USING (auth.uid() = user_id);

-- Function to automatically clean up expired tokens
CREATE OR REPLACE FUNCTION cleanup_expired_zoom_tokens()
RETURNS void AS $$
BEGIN
    DELETE FROM zoom_credentials
    WHERE expires_at < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;

-- Optional: Create a scheduled job to clean up expired tokens
-- This would typically be set up in Supabase dashboard or via pg_cron
-- SELECT cron.schedule('cleanup-zoom-tokens', '0 2 * * *', 'SELECT cleanup_expired_zoom_tokens();');
```

### Migration 003: Storage Buckets

**File**: `003_storage_buckets.sql`

```sql
-- Create storage buckets for file uploads
-- Note: These commands are typically run in Supabase dashboard or via API

-- Public bucket for logos
INSERT INTO storage.buckets (id, name, public)
VALUES ('logos', 'logos', true);

-- Private bucket for PDFs and sensitive files
INSERT INTO storage.buckets (id, name, public)
VALUES ('private', 'private', false);

-- Storage policies for logos bucket
CREATE POLICY "Public logo access" ON storage.objects
    FOR SELECT USING (bucket_id = 'logos');

CREATE POLICY "Authenticated users can upload logos" ON storage.objects
    FOR INSERT WITH CHECK (
        bucket_id = 'logos' AND
        auth.role() = 'authenticated'
    );

-- Storage policies for private bucket
CREATE POLICY "Users can access own private files" ON storage.objects
    FOR SELECT USING (
        bucket_id = 'private' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

CREATE POLICY "Users can upload to own private folder" ON storage.objects
    FOR INSERT WITH CHECK (
        bucket_id = 'private' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );
```

## Migration Rollback Scripts

### Rollback 003: Remove Storage Buckets

**File**: `rollback_003_storage_buckets.sql`

```sql
-- Drop storage policies
DROP POLICY IF EXISTS "Public logo access" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated users can upload logos" ON storage.objects;
DROP POLICY IF EXISTS "Users can access own private files" ON storage.objects;
DROP POLICY IF EXISTS "Users can upload to own private folder" ON storage.objects;

-- Remove buckets (this will delete all files!)
DELETE FROM storage.buckets WHERE id IN ('logos', 'private');
```

### Rollback 002: Remove Zoom Integration

**File**: `rollback_002_zoom_integration.sql`

```sql
-- Drop cleanup function
DROP FUNCTION IF EXISTS cleanup_expired_zoom_tokens();

-- Drop table (this will delete all Zoom credentials!)
DROP TABLE IF EXISTS zoom_credentials;
```

### Rollback 001: Remove Initial Schema

**File**: `rollback_001_initial_schema.sql`

```sql
-- Drop all tables (this will delete all data!)
DROP TABLE IF EXISTS brand_settings;
DROP TABLE IF EXISTS organization_members;
DROP TABLE IF EXISTS organizations;
DROP TABLE IF EXISTS deliverables;
DROP TABLE IF EXISTS profiles;
```

## Migration Execution

### Development Environment

```bash
# Apply migrations in order
psql -h localhost -d momentum_dev -f migrations/001_initial_schema.sql
psql -h localhost -d momentum_dev -f migrations/002_zoom_integration.sql
psql -h localhost -d momentum_dev -f migrations/003_storage_buckets.sql
```

### Supabase Environment

1. **Via Supabase Dashboard:**
   - Go to SQL Editor
   - Run each migration script manually
   - Verify successful execution

2. **Via Supabase CLI:**
   ```bash
   supabase db reset  # Reset to clean state
   supabase db push   # Push local schema changes
   ```

## Data Migration Considerations

### User Data Migration
If migrating from an existing system:

```sql
-- Example: Migrate existing user data
INSERT INTO profiles (id, email, name, created_at)
SELECT
    id,
    email,
    display_name,
    created_at
FROM legacy_users
ON CONFLICT (id) DO NOTHING;
```

### Deliverable Migration
```sql
-- Example: Migrate existing deliverables
INSERT INTO deliverables (id, user_id, client_name, html, created_at)
SELECT
    session_id,
    user_id,
    client_name,
    rendered_html,
    created_at
FROM legacy_sessions
WHERE rendered_html IS NOT NULL;
```

## Environment-Specific Considerations

### Development
- Use test data for migration testing
- Reset database frequently during development
- Enable verbose logging for debugging

### Staging
- Mirror production data structure
- Test all migrations before production
- Verify RLS policies work correctly

### Production
- **ALWAYS backup before migrations**
- Run during maintenance windows
- Have rollback plan ready
- Monitor system after migration

## Verification Scripts

### Post-Migration Verification

```sql
-- Verify all tables exist
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- Verify RLS is enabled
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
AND rowsecurity = true;

-- Verify indexes exist
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- Check foreign key constraints
SELECT
    tc.table_name,
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_schema = 'public';
```

## Troubleshooting

### Common Issues

**RLS Policy Conflicts:**
```sql
-- Check existing policies
SELECT schemaname, tablename, policyname, cmd, qual
FROM pg_policies
WHERE schemaname = 'public';
```

**Index Performance:**
```sql
-- Check index usage
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY tablename, attname;
```

**Storage Bucket Issues:**
```sql
-- Check bucket configuration
SELECT * FROM storage.buckets;

-- Check storage policies
SELECT * FROM storage.policies;
```