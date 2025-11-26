-- Migration: Add match_type column to rules table
-- This migration adds support for AND/OR logic in rule conditions

-- Add match_type column with default value 'all' (AND logic)
ALTER TABLE rules ADD COLUMN IF NOT EXISTS match_type VARCHAR NOT NULL DEFAULT 'all';
