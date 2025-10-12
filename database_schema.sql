-- Database schema for Nexus RPG
-- This file contains the required MySQL tables for the application

-- Create the database if it doesn't exist
CREATE DATABASE IF NOT EXISTS nexus_rpg CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Use the nexus_rpg database
USE nexus_rpg;

-- Table for storing player state information
CREATE TABLE IF NOT EXISTS PlayerState (
    player_id VARCHAR(255) NOT NULL PRIMARY KEY,
    current_area VARCHAR(255) NULL,
    current_npc_code VARCHAR(255) NULL,
    plot_flags JSON NULL,
    credits INT NOT NULL DEFAULT 220,
    brief_mode BOOLEAN NOT NULL DEFAULT FALSE,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for storing player inventory
CREATE TABLE IF NOT EXISTS PlayerInventory (
    id INT AUTO_INCREMENT PRIMARY KEY,
    player_id VARCHAR(255) NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    FOREIGN KEY (player_id) REFERENCES PlayerState(player_id) ON DELETE CASCADE,
    UNIQUE KEY (player_id, item_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for storing conversation history
CREATE TABLE IF NOT EXISTS ConversationHistory (
    player_id VARCHAR(255) NOT NULL,
    npc_code VARCHAR(255) NOT NULL,
    history JSON NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (player_id, npc_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for storing player profiles
CREATE TABLE IF NOT EXISTS PlayerProfiles (
    player_id VARCHAR(255) NOT NULL PRIMARY KEY,
    profile_data JSON NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES PlayerState(player_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for storing NPCs
CREATE TABLE IF NOT EXISTS NPCs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    area VARCHAR(255) NOT NULL,
    role VARCHAR(255) NULL,
    motivation TEXT NULL,
    goal TEXT NULL,
    needed_object VARCHAR(255) NULL,
    treasure VARCHAR(255) NULL,
    playerhint TEXT NULL,
    dialogue_hooks TEXT NULL,
    default_greeting TEXT NULL,
    repeat_greeting TEXT NULL,
    veil_connection TEXT NULL,
    emotes TEXT NULL,
    animations TEXT NULL,
    lookup TEXT NULL,
    llsettext TEXT NULL,
    teleport TEXT NULL,
    ai_behavior_notes TEXT NULL,
    conditional_responses TEXT NULL,
    conversation_state_tracking TEXT NULL,
    failure_conditions TEXT NULL,
    personality_traits TEXT NULL,
    prerequisites TEXT NULL,
    relationship_status TEXT NULL,
    relationships TEXT NULL,
    required_item VARCHAR(255) NULL,
    required_quantity INT NULL,
    required_source VARCHAR(255) NULL,
    reward_credits INT NULL,
    sl_commands TEXT NULL,
    success_conditions TEXT NULL,
    trading_rules TEXT NULL,
    storyboard_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for storing storyboards
CREATE TABLE IF NOT EXISTS Storyboards (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for storing locations
CREATE TABLE IF NOT EXISTS Locations (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    area_type VARCHAR(100),
    access_level VARCHAR(100),
    setting_description TEXT,
    veil_connection TEXT,
    primary_npcs TEXT,
    secondary_npcs TEXT,
    npc_density VARCHAR(100),
    interactive_objects TEXT,
    atmospheric_elements TEXT,
    location_purpose TEXT,
    special_properties TEXT,
    sl_environment TEXT,
    connected_locations TEXT,
    quest_relevance TEXT,
    storyboard_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for storing conversation analysis
CREATE TABLE IF NOT EXISTS ConversationAnalysis (
    id INT AUTO_INCREMENT PRIMARY KEY,
    player_id VARCHAR(255) NOT NULL,
    analysis TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES PlayerState(player_id) ON DELETE CASCADE,
    UNIQUE KEY (player_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_playerstate_area ON PlayerState(current_area);
CREATE INDEX IF NOT EXISTS idx_playerinventory_player ON PlayerInventory(player_id);
CREATE INDEX IF NOT EXISTS idx_conversationhistory_player ON ConversationHistory(player_id);
CREATE INDEX IF NOT EXISTS idx_npcs_area ON NPCs(area);
CREATE INDEX IF NOT EXISTS idx_npcs_name ON NPCs(name);