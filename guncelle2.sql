USE ister_v2;
ALTER TABLE ister_node ADD COLUMN SiraNo INT DEFAULT 0;
UPDATE ister_node SET SiraNo=NodeID WHERE SiraNo=0 OR SiraNo IS NULL;
