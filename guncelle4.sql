USE ister_v2;
ALTER TABLE ister_node ADD COLUMN IlgiliAsamaID INT NULL;

-- Duplicate test yöntemi kayıtlarını temizle (aynı ada sahip olanların fazlalarını sil)
DELETE t1 FROM test_yontemi t1
INNER JOIN test_yontemi t2
WHERE t1.TestYontemiID > t2.TestYontemiID AND t1.YontemAdi = t2.YontemAdi;
