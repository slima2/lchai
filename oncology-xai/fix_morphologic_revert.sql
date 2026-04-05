-- Revert column renames back to original names
ALTER TABLE morphologic_profiles RENAME COLUMN pct_micropapillary TO pct_tmp1;
ALTER TABLE morphologic_profiles RENAME COLUMN pct_cribriform TO pct_tmp2;
ALTER TABLE morphologic_profiles RENAME COLUMN pct_papillary TO pct_tmp3;
ALTER TABLE morphologic_profiles RENAME COLUMN pct_lepidic TO pct_tmp4;
ALTER TABLE morphologic_profiles RENAME COLUMN pct_solid TO pct_tmp5;
ALTER TABLE morphologic_profiles RENAME COLUMN pct_acinar TO pct_tmp6;

ALTER TABLE morphologic_profiles RENAME COLUMN pct_tmp1 TO pct_acinar;
ALTER TABLE morphologic_profiles RENAME COLUMN pct_tmp2 TO pct_lepidic;
ALTER TABLE morphologic_profiles RENAME COLUMN pct_tmp3 TO pct_micropapillary;
ALTER TABLE morphologic_profiles RENAME COLUMN pct_tmp4 TO pct_mucinous;
ALTER TABLE morphologic_profiles RENAME COLUMN pct_tmp5 TO pct_papillary;
ALTER TABLE morphologic_profiles RENAME COLUMN pct_tmp6 TO pct_solid;

-- Now the columns are back to original names with ORIGINAL values.
-- The data in these columns represents:
-- pct_acinar = model index 0 values (actually micropapillary)
-- pct_lepidic = model index 1 values (actually cribriform)
-- pct_micropapillary = model index 2 values (actually papillary)
-- pct_mucinous = model index 3 values (actually lepidic)
-- pct_papillary = model index 4 values (actually solid)
-- pct_solid = model index 5 values (actually acinar)
