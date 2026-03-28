USE ister_v2;

-- 1. IlgiliAsamaID alanını ekle
ALTER TABLE ister_node ADD COLUMN IlgiliAsamaID INT NULL;

-- 2. Duplicate test yöntemlerini güvenli temizle:
--    Kullanılan ID'leri tut, kullanılmayanları sil
DELETE FROM test_yontemi 
WHERE TestYontemiID NOT IN (
    SELECT DISTINCT TestYontemiID FROM ister_node WHERE TestYontemiID IS NOT NULL
)
AND YontemAdi IN (
    SELECT YontemAdi FROM (
        SELECT YontemAdi FROM test_yontemi
        GROUP BY YontemAdi HAVING COUNT(*) > 1
    ) AS duplar
);
