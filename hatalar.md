# Hatalar
+ Karşılaştırma yapıldıktan sonra güncelle yapılınca dış liste güncellenmiyor ve güncelle logu basmıyor.
## Göz Ardı Edilenler
+ Admin olmayan kullanıcılar kulanıcı ekleyip silebiliyor başkasının parolasını değiştirebiliyor? 
(hatta admin olmayanlar kulanıcılar side menüsünü görmemeli mi?)
+ Kullanıcılar kendi kendilerinin girişini kitleyebilir (neden?)
+ Platform (platformlar sayfası) name unique değil (olmalı mı?)
+ Admin kulanıcıları havuzun altındaki isterleri silebiliyor olmalı mı?
+ Excel import hatalı
+ Havuzda Platform isterdeki gibi firma görüşleri gözükmeli mi?
## Askıdakiler
+ gmt time hatası
+ firma görüş yanıt log da basmalı.
## Yapılanlar
+ Toplu upload route eklendi.
+ TA SGÖ ilişki kuralı eklendi.
+ Konfigürasayon silince ve eklenince değişiklik logu basmalı mı?
+ Platform silince ve eklenince değişiklik logu basmalı mı?
+ Havuz isterlerde maddeler (bullet) güncellenince değişiklik log basılmıyor.
+ tablo güncelede modal adı tablo ekle
+ Havuz isterlerde Tablolar güncellenemiyor silinemiyor.
+ Yeni column eklendi. 
+ Havuz isterlerdeki "Görüş" kısmı kaldırıldı.
+ Log basımı eksik olan kısımlar tamamlandı.
```` 
ALTER TABLE degisiklik_log
ADD Tur VARCHAR(10); 
```` 
+ Log sayfasında türe göre friltreleme eklendi.
+ Log sayfasında tür listelendi.
+ tabloda satır sütünlar güncellenince de log basılmalı mı?
+ tablo silme güncelleme platform isterde de gerekli mi?
+ log time hatalı global saat hatası -3 saat gözüküyot gmt+3 türkiye saati kullan
+ Havuz isterleri silinebilir olamlı.
+ Log kayıtları platform başlık ve seviyeye ile filtreleme olmalı.
+ Firma görüşü silinebilir ve güncellenebilir olmalı.