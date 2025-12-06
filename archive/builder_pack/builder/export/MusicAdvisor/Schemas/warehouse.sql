-- schemas/warehouse.sql
-- Free-first, pasteboard-driven warehouse (logical reference)

CREATE TABLE dim_track (
  track_id TEXT PRIMARY KEY,
  isrc TEXT,
  title TEXT,
  artists TEXT,           -- comma-joined list
  label TEXT,
  release_date DATE,
  genres TEXT,            -- comma-joined tags
  canonical_key TEXT,
  canonical_mode TEXT
);

CREATE TABLE dim_platform (
  platform TEXT PRIMARY KEY,  -- e.g., spotify, youtube, apple, tiktok
  description TEXT
);

CREATE TABLE fact_daily_metrics (
  metric_date DATE,
  platform TEXT,
  region TEXT,
  track_id TEXT,
  isrc TEXT,
  streams BIGINT,
  unique_listeners BIGINT,
  skips BIGINT,
  completes BIGINT,
  saves BIGINT,
  playlist_adds BIGINT,
  paid_ratio FLOAT,
  est_bots_ratio FLOAT,
  confidence FLOAT,
  PRIMARY KEY (metric_date, platform, region, track_id)
);

CREATE TABLE fact_audio_features (
  track_id TEXT,
  isrc TEXT,
  bpm FLOAT,
  key TEXT,
  mode TEXT,
  loudness_lufs FLOAT,
  energy FLOAT,
  danceability FLOAT,
  valence FLOAT,
  rhythm_profile TEXT,
  features_version TEXT,
  updated_at TIMESTAMP
);

CREATE TABLE fact_lyrics_features (
  track_id TEXT,
  isrc TEXT,
  lyrics TEXT,
  analysis_version TEXT,
  updated_at TIMESTAMP
);

CREATE TABLE fact_chart_positions (
  chart_name TEXT,
  metric_date DATE,
  track_id TEXT,
  position INT,
  panel_size INT,
  methodology_tag TEXT,
  PRIMARY KEY (chart_name, metric_date, track_id)
);

CREATE TABLE fact_playlists (
  playlist_id TEXT,
  playlist_name TEXT,
  platform TEXT,
  followers BIGINT,
  track_id TEXT,
  date_added DATE,
  position INT,
  PRIMARY KEY (playlist_id, track_id)
);
