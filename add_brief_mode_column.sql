-- Add brief_mode column to PlayerState table
USE nexus_rpg;

-- Add the brief_mode column to PlayerState table
ALTER TABLE PlayerState ADD COLUMN brief_mode BOOLEAN NOT NULL DEFAULT FALSE AFTER credits;

-- Verify the column was added
DESCRIBE PlayerState;