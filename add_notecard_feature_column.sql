-- Add notecard_feature column to NPCs table
-- This column stores NPC-specific instructions for notecard generation

USE nexus_rpg;

ALTER TABLE NPCs ADD COLUMN notecard_feature TEXT NULL AFTER trading_rules;
