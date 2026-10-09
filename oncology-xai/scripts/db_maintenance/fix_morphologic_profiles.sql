-- The columns are named with OLD pattern names.
-- The values need to be SWAPPED to match the correct mapping.
-- 
-- Old column → stores values for → correct pattern
-- pct_acinar → model index 0 → micropapillary
-- pct_lepidic → model index 1 → cribriform  
-- pct_micropapillary → model index 2 → papillary
-- pct_mucinous → model index 3 → lepidic
-- pct_papillary → model index 4 → solid
-- pct_solid → model index 5 → acinar
--
-- We need to rename columns to match reality.
-- PostgreSQL supports ALTER TABLE RENAME COLUMN.

-- Step 1: Rename to temp names
ALTER TABLE morphologic_profiles RENAME COLUMN pct_acinar TO pct_old_acinar;
ALTER TABLE morphologic_profiles RENAME COLUMN pct_lepidic TO pct_old_lepidic;
ALTER TABLE morphologic_profiles RENAME COLUMN pct_micropapillary TO pct_old_micropapillary;
ALTER TABLE morphologic_profiles RENAME COLUMN pct_mucinous TO pct_old_mucinous;
ALTER TABLE morphologic_profiles RENAME COLUMN pct_papillary TO pct_old_papillary;
ALTER TABLE morphologic_profiles RENAME COLUMN pct_solid TO pct_old_solid;

-- Step 2: Rename to correct names
-- pct_old_acinar (was model idx 0 = micropapillary)
ALTER TABLE morphologic_profiles RENAME COLUMN pct_old_acinar TO pct_micropapillary;
-- pct_old_lepidic (was model idx 1 = cribriform)
ALTER TABLE morphologic_profiles RENAME COLUMN pct_old_lepidic TO pct_cribriform;
-- pct_old_micropapillary (was model idx 2 = papillary)
ALTER TABLE morphologic_profiles RENAME COLUMN pct_old_micropapillary TO pct_papillary;
-- pct_old_mucinous (was model idx 3 = lepidic)
ALTER TABLE morphologic_profiles RENAME COLUMN pct_old_mucinous TO pct_lepidic;
-- pct_old_papillary (was model idx 4 = solid)
ALTER TABLE morphologic_profiles RENAME COLUMN pct_old_papillary TO pct_solid;
-- pct_old_solid (was model idx 5 = acinar)
ALTER TABLE morphologic_profiles RENAME COLUMN pct_old_solid TO pct_acinar;
