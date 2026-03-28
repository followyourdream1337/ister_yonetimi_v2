-- Mevcut ister_v2 veritabanını güncelle (MySQL 8.0 uyumlu)

USE ister_v2;

-- ister_node tablosuna yeni alanlar ekle
-- (Hata verirse alan zaten var demek, devam et)

ALTER TABLE ister_node ADD COLUMN IsterTipi ENUM('B','G') DEFAULT 'G';
ALTER TABLE ister_node ADD COLUMN HavuzKodu VARCHAR(20) NULL;

-- Yeni tablolar
CREATE TABLE IF NOT EXISTS ister_tablo (
    TabloID INT AUTO_INCREMENT PRIMARY KEY,
    NodeID INT NOT NULL,
    TabloAdi VARCHAR(200),
    SutunBasliklari JSON,
    Satirlar JSON,
    OlusturanID INT,
    OlusturmaTarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (NodeID) REFERENCES ister_node(NodeID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS firma_gorusu (
    GorusID INT AUTO_INCREMENT PRIMARY KEY,
    NodeID INT NOT NULL,
    PlatformID INT NOT NULL,
    FirmaAdi VARCHAR(200) NOT NULL,
    GorusIcerik LONGTEXT,
    GorusOzet VARCHAR(500),
    GorusKategori VARCHAR(200),
    OlusturanID INT,
    OlusturmaTarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (NodeID) REFERENCES ister_node(NodeID) ON DELETE CASCADE,
    FOREIGN KEY (PlatformID) REFERENCES platform_list(PlatformID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS firma_gorusu_yanit (
    YanitID INT AUTO_INCREMENT PRIMARY KEY,
    GorusID INT NOT NULL,
    YanitIcerik LONGTEXT,
    YazanID INT,
    OlusturmaTarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (GorusID) REFERENCES firma_gorusu(GorusID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ister_onay (
    OnayID INT AUTO_INCREMENT PRIMARY KEY,
    NodeID INT NOT NULL,
    PlatformID INT NOT NULL,
    OnayDurumu TINYINT(1) DEFAULT 0,
    OnaylayanID INT,
    OnayTarihi DATETIME,
    UNIQUE KEY uq_node_plat (NodeID, PlatformID),
    FOREIGN KEY (NodeID) REFERENCES ister_node(NodeID) ON DELETE CASCADE,
    FOREIGN KEY (PlatformID) REFERENCES platform_list(PlatformID) ON DELETE CASCADE
);
