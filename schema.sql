-- PostgreSQL schema for Neon database
-- Run this once to create the table in your Neon database

CREATE TABLE IF NOT EXISTS scores (
    id SERIAL PRIMARY KEY,
    AthleteName VARCHAR(255),
    Level VARCHAR(10),
    CompYear VARCHAR(10),
    MeetName VARCHAR(255),
    MeetDate DATE,
    Event VARCHAR(50),
    StartValue DECIMAL(5,3),
    Score DECIMAL(5,3),
    Place INTEGER
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_scores_athlete ON scores(AthleteName);
CREATE INDEX IF NOT EXISTS idx_scores_meet ON scores(MeetName, MeetDate);
CREATE INDEX IF NOT EXISTS idx_scores_comp_year ON scores(CompYear);
CREATE INDEX IF NOT EXISTS idx_scores_level ON scores(Level);
