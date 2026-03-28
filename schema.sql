CREATE DATABASE IF NOT EXISTS ister_v2 CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci;
USE ister_v2;

CREATE TABLE IF NOT EXISTS kullanici (
    KullaniciID INT AUTO_INCREMENT PRIMARY KEY,
    KullaniciAdi VARCHAR(100) NOT NULL UNIQUE,
    Sifre VARCHAR(255) NOT NULL,
    AdSoyad VARCHAR(200),
    AktifMi TINYINT(1) DEFAULT 1
);

CREATE TABLE IF NOT EXISTS konfig_list (
    KonfigID INT AUTO_INCREMENT PRIMARY KEY,
    KonfigAdi VARCHAR(200) NOT NULL
);

CREATE TABLE IF NOT EXISTS platform_list (
    PlatformID INT AUTO_INCREMENT PRIMARY KEY,
    PlatformAdi VARCHAR(200) NOT NULL,
    HavuzMu TINYINT(1) DEFAULT 0
);

CREATE TABLE IF NOT EXISTS platform_konfig (
    PlatformKonfigID INT AUTO_INCREMENT PRIMARY KEY,
    PlatformID INT NOT NULL,
    KonfigID INT NOT NULL,
    UNIQUE KEY (PlatformID, KonfigID),
    FOREIGN KEY (PlatformID) REFERENCES platform_list(PlatformID) ON DELETE CASCADE,
    FOREIGN KEY (KonfigID) REFERENCES konfig_list(KonfigID) ON DELETE CASCADE
);

-- Her platformun kendi seviye tanımları (TGD, SGÖ, vb.)
CREATE TABLE IF NOT EXISTS seviye_tanim (
    SeviyeID INT AUTO_INCREMENT PRIMARY KEY,
    PlatformID INT NOT NULL,
    SeviyeNo INT NOT NULL,
    SeviyeAdi VARCHAR(100) NOT NULL,
    UNIQUE KEY (PlatformID, SeviyeNo),
    FOREIGN KEY (PlatformID) REFERENCES platform_list(PlatformID) ON DELETE CASCADE
);

-- Her platformun kendi test aşamaları (FKT, BLG, vb.)
CREATE TABLE IF NOT EXISTS test_asama (
    TestAsamaID INT AUTO_INCREMENT PRIMARY KEY,
    PlatformID INT NOT NULL,
    AsamaNo INT NOT NULL,
    AsamaAdi VARCHAR(100) NOT NULL,
    UNIQUE KEY (PlatformID, AsamaNo),
    FOREIGN KEY (PlatformID) REFERENCES platform_list(PlatformID) ON DELETE CASCADE
);

-- Test yöntemi seçenekleri (sistem genelinde sabit)
CREATE TABLE IF NOT EXISTS test_yontemi (
    TestYontemiID INT AUTO_INCREMENT PRIMARY KEY,
    YontemAdi VARCHAR(100) NOT NULL
);

-- Ana ister ağacı — her node bir ister
CREATE TABLE IF NOT EXISTS ister_node (
    NodeID INT AUTO_INCREMENT PRIMARY KEY,
    PlatformID INT NOT NULL,
    SeviyeID INT NOT NULL,
    ParentID INT NULL,
    HavuzNodeID INT NULL,
    KonfigID INT NULL,
    NodeNumarasi VARCHAR(100) NULL,
    GignBaslik TINYINT(1) DEFAULT 0,
    UstBaslikID INT NULL,
    IsterTipi ENUM('B','G') DEFAULT 'G' COMMENT 'B=Başlık, G=Gereksinim',
    HavuzKodu VARCHAR(20) NULL COMMENT 'b1,b2,g1,g2 gibi havuz bazlı kod',
    Icerik LONGTEXT,
    TestYontemiID INT NULL,
    DegistirildiMi TINYINT(1) DEFAULT 0,
    OlusturanID INT,
    OlusturmaTarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (PlatformID) REFERENCES platform_list(PlatformID) ON DELETE CASCADE,
    FOREIGN KEY (SeviyeID) REFERENCES seviye_tanim(SeviyeID),
    FOREIGN KEY (ParentID) REFERENCES ister_node(NodeID) ON DELETE CASCADE,
    FOREIGN KEY (KonfigID) REFERENCES konfig_list(KonfigID),
    FOREIGN KEY (TestYontemiID) REFERENCES test_yontemi(TestYontemiID),
    FOREIGN KEY (OlusturanID) REFERENCES kullanici(KullaniciID)
);

-- İsterler arası çapraz bağlantılar (traceability için)
CREATE TABLE IF NOT EXISTS ister_baglanti (
    BaglantiID INT AUTO_INCREMENT PRIMARY KEY,
    KaynakNodeID INT NOT NULL,
    HedefNodeID INT NOT NULL,
    UNIQUE KEY (KaynakNodeID, HedefNodeID),
    FOREIGN KEY (KaynakNodeID) REFERENCES ister_node(NodeID) ON DELETE CASCADE,
    FOREIGN KEY (HedefNodeID) REFERENCES ister_node(NodeID) ON DELETE CASCADE
);

-- Test sonuçları — en alt seviye node'lara
CREATE TABLE IF NOT EXISTS test_sonuc (
    TestSonucID INT AUTO_INCREMENT PRIMARY KEY,
    NodeID INT NOT NULL,
    TestAsamaID INT NOT NULL,
    Sonuc ENUM('Basarili','Hatali') NOT NULL,
    Aciklama LONGTEXT,
    KullaniciID INT,
    Tarih DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY (NodeID, TestAsamaID),
    FOREIGN KEY (NodeID) REFERENCES ister_node(NodeID) ON DELETE CASCADE,
    FOREIGN KEY (TestAsamaID) REFERENCES test_asama(TestAsamaID) ON DELETE CASCADE,
    FOREIGN KEY (KullaniciID) REFERENCES kullanici(KullaniciID)
);

-- TA Dokümanları
CREATE TABLE IF NOT EXISTS ta_dokuman (
    TaID INT AUTO_INCREMENT PRIMARY KEY,
    PlatformID INT NOT NULL,
    SiraNo INT NOT NULL,
    HavuzTaID INT NULL,
    SolSistemAdi VARCHAR(200),
    SagSistemAdi VARCHAR(200),
    FOREIGN KEY (PlatformID) REFERENCES platform_list(PlatformID) ON DELETE CASCADE
);

-- TA içindeki veri satırları
CREATE TABLE IF NOT EXISTS ta_veri (
    TaVeriID INT AUTO_INCREMENT PRIMARY KEY,
    TaID INT NOT NULL,
    Sistem ENUM('sol','sag') NOT NULL,
    Yon ENUM('aldigi','verdigi') NOT NULL,
    Icerik VARCHAR(500),
    Sira INT DEFAULT 0,
    FOREIGN KEY (TaID) REFERENCES ta_dokuman(TaID) ON DELETE CASCADE
);

-- SGÖ — TA bağlantısı
CREATE TABLE IF NOT EXISTS ta_sgo_baglanti (
    BaglantiID INT AUTO_INCREMENT PRIMARY KEY,
    TaID INT NOT NULL,
    NodeID INT NOT NULL,
    UNIQUE KEY (TaID, NodeID),
    FOREIGN KEY (TaID) REFERENCES ta_dokuman(TaID) ON DELETE CASCADE,
    FOREIGN KEY (NodeID) REFERENCES ister_node(NodeID) ON DELETE CASCADE
);

-- Değişiklik logu
CREATE TABLE IF NOT EXISTS degisiklik_log (
    LogID INT AUTO_INCREMENT PRIMARY KEY,
    TabloAdi VARCHAR(100),
    KayitID INT,
    AlanAdi VARCHAR(100),
    EskiDeger LONGTEXT,
    YeniDeger LONGTEXT,
    KullaniciID INT,
    KullaniciAdi VARCHAR(100),
    DegisimTarihi DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Başlangıç verileri
INSERT IGNORE INTO kullanici (KullaniciAdi, Sifre, AdSoyad, AktifMi) VALUES ('admin', 'admin123', 'Sistem Yöneticisi', 1);
INSERT IGNORE INTO platform_list (PlatformAdi, HavuzMu) VALUES ('HAVUZ', 1);
INSERT IGNORE INTO test_yontemi (YontemAdi) VALUES ('Fonksiyonel Test'), ('Belge Sunumu'), ('Performans Testi'), ('Güvenlik Testi'), ('Entegrasyon Testi');

-- NodeNumarasi zaten CREATE TABLE içinde tanımlı, bu satır kaldırıldı

-- Yeni tablolar (v3 güncellemesi)

-- İster tablolar (kutucuk içi tablo)
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

-- Firma görüşleri
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

-- Firma görüşü yanıtları
CREATE TABLE IF NOT EXISTS firma_gorusu_yanit (
    YanitID INT AUTO_INCREMENT PRIMARY KEY,
    GorusID INT NOT NULL,
    YanitIcerik LONGTEXT,
    YazanID INT,
    OlusturmaTarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (GorusID) REFERENCES firma_gorusu(GorusID) ON DELETE CASCADE
);

-- İster onay durumu
CREATE TABLE IF NOT EXISTS ister_onay (
    OnayID INT AUTO_INCREMENT PRIMARY KEY,
    NodeID INT NOT NULL,
    PlatformID INT NOT NULL,
    OnayDurumu TINYINT(1) DEFAULT 0,
    OnaylayanID INT,
    OnayTarihi DATETIME,
    UNIQUE KEY (NodeID, PlatformID),
    FOREIGN KEY (NodeID) REFERENCES ister_node(NodeID) ON DELETE CASCADE,
    FOREIGN KEY (PlatformID) REFERENCES platform_list(PlatformID) ON DELETE CASCADE
);

-- ALTER TABLE güncellemeleri (mevcut kurulumlar için)
-- Bu alanlar zaten CREATE TABLE içinde tanımlı

-- v3.1 güncellemesi: yeni alanlar
ALTER TABLE ister_node ADD COLUMN IF NOT EXISTS IsterTipi ENUM('B','G') DEFAULT 'G' AFTER UstBaslikID;
ALTER TABLE ister_node ADD COLUMN IF NOT EXISTS HavuzKodu VARCHAR(20) NULL AFTER IsterTipi;
