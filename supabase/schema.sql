create extension if not exists "uuid-ossp";

create table if not exists users (
  id text primary key,
  engagement_preference double precision default 0.5,
  brevity_preference double precision default 0.5,
  support_preference double precision default 0.5,
  task_focus double precision default 0.5,
  points integer default 0,
  created_at timestamptz default now()
);

create table if not exists interactions (
  id uuid primary key default uuid_generate_v4(),
  user_id text not null references users(id) on delete cascade,
  input text not null,
  response text not null,
  model_version text not null,
  metadata jsonb default '{}'::jsonb,
  timestamp timestamptz default now()
);

create table if not exists feedback (
  id uuid primary key default uuid_generate_v4(),
  interaction_id uuid not null references interactions(id) on delete cascade,
  user_id text not null references users(id) on delete cascade,
  vote text not null,
  reward double precision not null,
  tags text[] default '{}',
  notes text,
  created_at timestamptz default now()
);

create table if not exists embeddings (
  id uuid primary key default uuid_generate_v4(),
  interaction_id uuid references interactions(id) on delete cascade,
  user_id text not null references users(id) on delete cascade,
  embedding jsonb not null,
  source_text text not null,
  created_at timestamptz default now()
);

create table if not exists model_versions (
  id uuid primary key default uuid_generate_v4(),
  version text not null unique,
  status text not null default 'active',
  ab_bucket text not null default 'A',
  adapter_path text,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);
