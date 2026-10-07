-- Fixture for tests/test_fix_series_ids.py. date_modified is NULL = unchanged.
CREATE TABLE thing (
  checksum_sha256 TEXT PRIMARY KEY, identifier TEXT, series_id TEXT,
  identifiers TEXT, obsoletes TEXT, archived BOOLEAN, date_modified TEXT);

-- Chain A: DOI head -> https -> NULL -> plain, end of chain
INSERT INTO thing VALUES ('a1','A1','old','["x","doi:10.82144/AAA"]','A2',0,NULL);
INSERT INTO thing VALUES ('a2','A2','https://a2','[]','A3',0,NULL);
INSERT INTO thing VALUES ('a3','A3',NULL,'[]','A4',0,NULL);
INSERT INTO thing VALUES ('a4','A4','plain','[]',NULL,0,NULL);

-- Chain B: DOI head -> row with its own DOI (stops) -> older row
INSERT INTO thing VALUES ('b1','B1','b1s','["doi:10.82144/B1"]','B2',0,NULL);
INSERT INTO thing VALUES ('b2','B2','b2s','["doi:10.82144/B2"]','B3',0,NULL);
INSERT INTO thing VALUES ('b3','B3','b3s','[]',NULL,0,NULL);

-- Chain C: dangling obsoletes
INSERT INTO thing VALUES ('c1','C1','c1s','["doi:10.82144/C1"]','MISSING',0,NULL);

-- Chain D: cycle
INSERT INTO thing VALUES ('d1','D1','d1s','["doi:10.82144/D1"]','D2',0,NULL);
INSERT INTO thing VALUES ('d2','D2','d2s','[]','D1',0,NULL);

-- Already correct DOI row: no change
INSERT INTO thing VALUES ('e1','E1','doi:10.82144/E1','["doi:10.82144/E1"]',NULL,0,NULL);
-- Multiple DOIs: first 82144 one wins; other-prefix DOI ignored
INSERT INTO thing VALUES ('f1','F1','f1s','["doi:10.5061/zzz","doi:10.82144/F1a","doi:10.82144/F1b"]',NULL,0,NULL);
-- Non-82144 DOI only, https series -> archived
INSERT INTO thing VALUES ('g1','G1','https://g1','["doi:10.5061/zzz"]',NULL,0,NULL);
-- https series, already archived: untouched
INSERT INTO thing VALUES ('h1','H1','https://h1','[]',NULL,1,NULL);
-- Non-https, no DOI: untouched
INSERT INTO thing VALUES ('i1','I1','urn:uuid:1','[]',NULL,0,NULL);
-- Malformed / NULL identifiers
INSERT INTO thing VALUES ('j1','J1','https://j1','not json',NULL,0,NULL);
INSERT INTO thing VALUES ('j2','J2','j2s',NULL,NULL,0,NULL);
-- Existing https with multiple types of identifiers: DOI wins over others --
INSERT INTO thing VALUES ('k1','K1','https://k1','["https://k1","doi:10.82144/K1","urn:uuid:K1"]',NULL,0,NULL);
INSERT INTO thing VALUES ('ce02cd1d06a2c27527d5eda970d105e6a8b7a3f8be80ca813ae4ed4e9fb355eb','sha256:ce02cd1d06a2c27527d5eda970d105e6a8b7a3f8be80ca813ae4ed4e9fb355eb','https://seamap.env.duke.edu/dataset/2050','["https://k2","urn:uuid:K2"]',NULL,0,NULL);
INSERT INTO thing VALUES ('6c142b471b13faf094d7ddec8255413f41ebe53ec8117dc9166e0c10e96f56d1','sha256:6c142b471b13faf094d7ddec8255413f41ebe53ec8117dc9166e0c10e96f56d1','https://seamap.env.duke.edu/dataset/2050','["10.82144/422375df", "https://doi.org/10.82144/422375df", "c0c017bf-f6e1-47ac-921b-906bca270fef", "https://obis.org/dataset/c0c017bf-f6e1-47ac-921b-906bca270fef", "https://seamap.env.duke.edu/dataset/2050"]','sha256:ce02cd1d06a2c27527d5eda970d105e6a8b7a3f8be80ca813ae4ed4e9fb355eb',0,NULL);
INSERT INTO thing VALUES ('02fd78dddb6ad9b28c0a3b9d3cc344a13ec06331e8e3dc984b401208bbe7f2a0','sha256:02fd78dddb6ad9b28c0a3b9d3cc344a13ec06331e8e3dc984b401208bbe7f2a0','https://seamap.env.duke.edu/dataset/2050','["doi:10.82144/422375df", "https://doi.org/10.82144/422375df", "https://seamap.env.duke.edu/dataset/2050", "c0c017bf-f6e1-47ac-921b-906bca270fef", "https://obis.org/dataset/c0c017bf-f6e1-47ac-921b-906bca270fef"]','sha256:6c142b471b13faf094d7ddec8255413f41ebe53ec8117dc9166e0c10e96f56d1',0,NULL);