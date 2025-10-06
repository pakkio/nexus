-- Add teleport column to NPCs table for coordinates storage
USE nexus_rpg;

ALTER TABLE NPCs ADD COLUMN teleport TEXT NULL AFTER llsettext;

-- Verify the column was added
DESCRIBE NPCs;