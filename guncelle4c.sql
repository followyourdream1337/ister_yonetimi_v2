USE ister_v2;

-- Sadece kullanılmayan duplicate test yöntemlerini sil
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
