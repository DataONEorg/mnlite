-- Fixture for tests/test_fix_series_ids.py. date_modified NULL = unchanged.
CREATE TABLE thing (
  checksum_sha256 TEXT PRIMARY KEY, identifier TEXT UNIQUE, series_id TEXT,
  identifiers TEXT, obsoletes TEXT, obsoleted_by TEXT, archived BOOLEAN, date_modified TEXT);
CREATE TABLE thing_accessrule (thing_id TEXT, accessrule_id INTEGER);

-- Chain A (newest first): a1 DOI head -> a2 https -> a3 NULL series -> a4 plain
INSERT INTO thing VALUES ('a1','A1','old','["x", "doi:10.82144/AAA"]','A2',NULL,0,NULL);
INSERT INTO thing_accessrule VALUES ('a1',1);
INSERT INTO thing VALUES ('a2','A2','https://a2','[]','A3','A1',0,NULL);
INSERT INTO thing_accessrule VALUES ('a2',1);
INSERT INTO thing VALUES ('a3','A3',NULL,'[]','A4','A2',0,NULL);
INSERT INTO thing_accessrule VALUES ('a3',1);
INSERT INTO thing VALUES ('a4','A4','plain','[]',NULL,'A3',0,NULL);
INSERT INTO thing_accessrule VALUES ('a4',1);
-- Chain B: b1 DOI head -> b2 own DOI (walk stops) -> b3
INSERT INTO thing VALUES ('b1','B1','b1s','["doi:10.82144/B1"]','B2',NULL,0,NULL);
INSERT INTO thing_accessrule VALUES ('b1',1);
INSERT INTO thing VALUES ('b2','B2','b2s','["doi:10.82144/B2"]','B3','B1',0,NULL);
INSERT INTO thing_accessrule VALUES ('b2',1);
INSERT INTO thing VALUES ('b3','B3','b3s','[]',NULL,'B2',0,NULL);
INSERT INTO thing_accessrule VALUES ('b3',1);
-- Chain C: dangling obsoletes
INSERT INTO thing VALUES ('c1','C1','c1s','["doi:10.82144/C1"]','MISSING',NULL,0,NULL);
INSERT INTO thing_accessrule VALUES ('c1',1);
-- Chain D: cycle
INSERT INTO thing VALUES ('d1','D1','d1s','["doi:10.82144/D1"]','D2','D2',0,NULL);
INSERT INTO thing_accessrule VALUES ('d1',1);
INSERT INTO thing VALUES ('d2','D2','d2s','[]','D1','D1',0,NULL);
INSERT INTO thing_accessrule VALUES ('d2',1);
-- e1 already correct; f1 multiple DOIs; g1 non-matching DOI + https; h1 already archived; i1 plain; j1/j2 malformed identifiers; k1 DOI among others
INSERT INTO thing VALUES ('e1','E1','doi:10.82144/E1','["doi:10.82144/E1"]',NULL,NULL,0,NULL);
INSERT INTO thing_accessrule VALUES ('e1',1);
INSERT INTO thing VALUES ('f1','F1','f1s','["doi:10.5061/zzz", "doi:10.82144/F1a", "doi:10.82144/F1b"]',NULL,NULL,0,NULL);
INSERT INTO thing_accessrule VALUES ('f1',1);
INSERT INTO thing VALUES ('g1','G1','https://g1','["doi:10.5061/zzz"]',NULL,NULL,0,NULL);
INSERT INTO thing_accessrule VALUES ('g1',1);
INSERT INTO thing VALUES ('h1','H1','https://h1','[]',NULL,NULL,1,NULL);
INSERT INTO thing_accessrule VALUES ('h1',1);
INSERT INTO thing VALUES ('i1','I1','urn:uuid:1','[]',NULL,NULL,0,NULL);
INSERT INTO thing_accessrule VALUES ('i1',1);
INSERT INTO thing VALUES ('j1','J1','https://j1','not json',NULL,NULL,0,NULL);
INSERT INTO thing_accessrule VALUES ('j1',1);
INSERT INTO thing VALUES ('j2','J2','j2s',NULL,NULL,NULL,0,NULL);
INSERT INTO thing_accessrule VALUES ('j2',1);
INSERT INTO thing VALUES ('k1','K1','https://k1','["https://k1", "doi:10.82144/K1", "urn:uuid:K1"]',NULL,NULL,0,NULL);
INSERT INTO thing_accessrule VALUES ('k1',1);
-- seamap chain, 3 versions, all https series_id; newest has DOI; real-style sha256 PIDs
INSERT INTO thing VALUES ('ce02cd1d06a2c27527d5eda970d105e6a8b7a3f8be80ca813ae4ed4e9fb355eb','sha256:ce02cd1d06a2c27527d5eda970d105e6a8b7a3f8be80ca813ae4ed4e9fb355eb','https://seamap.env.duke.edu/dataset/2050','["https://k2", "urn:uuid:K2"]',NULL,'sha256:6c142b471b13faf094d7ddec8255413f41ebe53ec8117dc9166e0c10e96f56d1',0,NULL);
INSERT INTO thing_accessrule VALUES ('ce02cd1d06a2c27527d5eda970d105e6a8b7a3f8be80ca813ae4ed4e9fb355eb',1);
INSERT INTO thing VALUES ('6c142b471b13faf094d7ddec8255413f41ebe53ec8117dc9166e0c10e96f56d1','sha256:6c142b471b13faf094d7ddec8255413f41ebe53ec8117dc9166e0c10e96f56d1','https://seamap.env.duke.edu/dataset/2050','["10.82144/422375df", "https://doi.org/10.82144/422375df", "c0c017bf-f6e1-47ac-921b-906bca270fef"]','sha256:ce02cd1d06a2c27527d5eda970d105e6a8b7a3f8be80ca813ae4ed4e9fb355eb','sha256:02fd78dddb6ad9b28c0a3b9d3cc344a13ec06331e8e3dc984b401208bbe7f2a0',0,NULL);
INSERT INTO thing_accessrule VALUES ('6c142b471b13faf094d7ddec8255413f41ebe53ec8117dc9166e0c10e96f56d1',1);
INSERT INTO thing VALUES ('02fd78dddb6ad9b28c0a3b9d3cc344a13ec06331e8e3dc984b401208bbe7f2a0','sha256:02fd78dddb6ad9b28c0a3b9d3cc344a13ec06331e8e3dc984b401208bbe7f2a0','https://seamap.env.duke.edu/dataset/2050','["doi:10.82144/422375df", "https://doi.org/10.82144/422375df", "c0c017bf-f6e1-47ac-921b-906bca270fef"]','sha256:6c142b471b13faf094d7ddec8255413f41ebe53ec8117dc9166e0c10e96f56d1',NULL,0,NULL);
INSERT INTO thing_accessrule VALUES ('02fd78dddb6ad9b28c0a3b9d3cc344a13ec06331e8e3dc984b401208bbe7f2a0',1);
