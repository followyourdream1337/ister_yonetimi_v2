from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_mysqldb import MySQL
import MySQLdb.cursors
from functools import wraps
from datetime import datetime,timezone,timedelta
from enum import Enum

app = Flask(__name__)
app.secret_key = 'ister_v2_secret_2024'
app.config['MYSQL_HOST'] = 'sql8.freesqldatabase.com'
app.config['MYSQL_USER'] = 'sql8820996'
app.config['MYSQL_PASSWORD'] = 'KjmvNC1FV6'
app.config['MYSQL_DB'] = 'sql8820996'
app.config['MYSQL_CHARSET'] = 'utf8mb4'
mysql = MySQL(app)

class LogTur(Enum):
    CREATE = "Ekleme"
    UPDATE = "Güncelleme"
    DELETE = "Silme"

def login_gerekli(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'kullanici_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def log_kaydet(tablo, kayit_id, alan, eski, yeni, tur):
    if str(eski or '') == str(yeni or ''):
        return
    cur = mysql.connection.cursor()
    cur.execute("""INSERT INTO degisiklik_log (TabloAdi,KayitID,AlanAdi,EskiDeger,YeniDeger,KullaniciID,KullaniciAdi,DegisimTarihi,Tur)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (tablo, kayit_id, alan, str(eski or ''), str(yeni or ''),
                 session.get('kullanici_id'), session.get('kullanici_adi'), datetime.now(timezone(timedelta(hours=3))),tur))
    mysql.connection.commit()
    cur.close()

def cur_dict():
    return mysql.connection.cursor(MySQLdb.cursors.DictCursor)

# ── AUTH ──────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return redirect(url_for('ana_menu') if 'kullanici_id' in session else url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    hata = None
    if request.method == 'POST':
        cur = cur_dict()
        cur.execute("SELECT * FROM kullanici WHERE KullaniciAdi=%s AND Sifre=%s AND AktifMi=1",
                    (request.form['kullanici_adi'], request.form['sifre']))
        k = cur.fetchone(); cur.close()
        if k:
            session.update({'kullanici_id': k['KullaniciID'], 'kullanici_adi': k['KullaniciAdi'], 'ad_soyad': k['AdSoyad']})
            return redirect(url_for('ana_menu'))
        hata = 'Kullanıcı adı veya şifre hatalı.'
    return render_template('login.html', hata=hata)

@app.route('/cikis')
def cikis():
    session.clear(); return redirect(url_for('login'))

# ── SAYFALAR ──────────────────────────────────────────────────────────────────
@app.route('/ana_menu')
@login_gerekli
def ana_menu(): return render_template('ana_menu.html')

@app.route('/platform')
@login_gerekli
def platform_sayfasi(): return render_template('platform.html')

@app.route('/konfig')
@login_gerekli
def konfig_sayfasi(): return render_template('konfig.html')

@app.route('/ister')
@login_gerekli
def ister_sayfasi(): return render_template('ister.html')

@app.route('/test_girisi')
@login_gerekli
def test_girisi_sayfasi(): return render_template('test_girisi.html')

@app.route('/traceability')
@login_gerekli
def traceability_sayfasi(): return render_template('traceability.html')

@app.route('/ta_dokuman')
@login_gerekli
def ta_dokuman_sayfasi(): return render_template('ta_dokuman.html')

@app.route('/log')
@login_gerekli
def log_sayfasi(): return render_template('log.html',LogTur=LogTur)

@app.route('/kullanici')
@login_gerekli
def kullanici_sayfasi(): return render_template('kullanici.html')

@app.route('/havuz_ister')
@login_gerekli
def havuz_ister_sayfasi(): return render_template('havuz_ister.html')

@app.route('/platform_ister')
@login_gerekli
def platform_ister_sayfasi(): return render_template('platform_ister.html')

@app.route('/karsilastirma')
@login_gerekli
def karsilastirma_sayfasi(): return render_template('karsilastirma.html')

# ── KARŞILAŞTIRMA API ─────────────────────────────────────────────────────────
def levenshtein(s1, s2):
    if not s1: return len(s2 or '')
    if not s2: return len(s1 or '')
    s1, s2 = str(s1).lower(), str(s2).lower()
    if len(s1) < len(s2): s1, s2 = s2, s1
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            curr.append(min(prev[j] + (0 if c1 == c2 else 1), curr[j] + 1, prev[j + 1] + 1))
        prev = curr
    return prev[-1]

def benzerlik_orani(s1, s2):
    if not s1 and not s2: return 100
    if not s1 or not s2: return 0
    maks = max(len(str(s1)), len(str(s2)))
    if maks == 0: return 100
    return round((1 - levenshtein(s1, s2) / maks) * 100, 1)

@app.route('/api/karsilastir/dis_liste', methods=['POST'])
@login_gerekli
def karsilastir_dis_liste():
    d = request.json
    platform_id = d.get('platform_id')
    dis_liste = d.get('dis_liste', [])
    esik = d.get('esik', 80)
    seviye_no = d.get('seviye_no', 2)
    cur = cur_dict()
    cur.execute("""SELECT n.NodeID, n.Icerik, s.SeviyeAdi, s.SeviyeNo
                   FROM ister_node n JOIN seviye_tanim s ON n.SeviyeID=s.SeviyeID
                   WHERE n.PlatformID=%s AND s.SeviyeNo=%s""", (platform_id, seviye_no))
    bizim = cur.fetchall()
    cur.close()
    sonuclar = []
    for dis in dis_liste:
        dis_metin = str(dis.get('metin') or '')
        en_iyi = None; en_iyi_oran = -1
        for b in bizim:
            oran = benzerlik_orani(dis_metin, b['Icerik'])
            if oran > en_iyi_oran:
                en_iyi_oran = oran; en_iyi = b
        durum = 'ayni' if en_iyi_oran == 100 else 'benzer' if en_iyi_oran >= esik else 'yeni'
        sonuclar.append({'dis_metin': dis_metin, 'bizim_id': en_iyi['NodeID'] if en_iyi else None,
                         'bizim_metin': en_iyi['Icerik'] if en_iyi else None,
                         'benzerlik': en_iyi_oran, 'durum': durum})
    fazlalar = []
    for b in bizim:
        en_iyi_oran = max([benzerlik_orani(b['Icerik'], str(d.get('metin') or '')) for d in dis_liste], default=0)
        if en_iyi_oran < esik:
            fazlalar.append({'bizim_id': b['NodeID'], 'bizim_metin': b['Icerik'], 'durum': 'fazla'})
    return jsonify({'sonuclar': sonuclar, 'fazlalar': fazlalar})

@app.route('/api/karsilastir/havuz', methods=['POST'])
@login_gerekli
def karsilastir_havuz_v2():
    d = request.json
    platform_id = d.get('platform_id')
    esik = d.get('esik', 80)
    seviye_no = d.get('seviye_no', 2)
    cur = cur_dict()
    cur.execute("SELECT PlatformID FROM platform_list WHERE HavuzMu=1 LIMIT 1")
    havuz = cur.fetchone()
    if not havuz: cur.close(); return jsonify({'hata': 'Havuz bulunamadı'}), 400
    cur.execute("""SELECT n.NodeID, n.Icerik, s.SeviyeNo FROM ister_node n
                   JOIN seviye_tanim s ON n.SeviyeID=s.SeviyeID
                   WHERE n.PlatformID=%s AND s.SeviyeNo=%s""", (platform_id, seviye_no))
    platform_nodes = cur.fetchall()
    cur.execute("""SELECT n.NodeID, n.Icerik FROM ister_node n
                   JOIN seviye_tanim s ON n.SeviyeID=s.SeviyeID
                   WHERE n.PlatformID=%s AND s.SeviyeNo=%s""", (havuz['PlatformID'], seviye_no))
    havuz_nodes = cur.fetchall()
    cur.close()
    sonuclar = []
    for pn in platform_nodes:
        en_iyi = None; en_iyi_oran = -1
        for hn in havuz_nodes:
            oran = benzerlik_orani(pn['Icerik'], hn['Icerik'])
            if oran > en_iyi_oran:
                en_iyi_oran = oran; en_iyi = hn
        durum = 'ayni' if en_iyi_oran == 100 else 'benzer' if en_iyi_oran >= esik else 'farkli'
        sonuclar.append({'platform_node_id': pn['NodeID'], 'platform_metin': pn['Icerik'],
                         'havuz_id': en_iyi['NodeID'] if en_iyi else None,
                         'havuz_metin': en_iyi['Icerik'] if en_iyi else None,
                         'benzerlik': en_iyi_oran, 'durum': durum})
    havuzda_fazla = []
    for hn in havuz_nodes:
        en_iyi_oran = max([benzerlik_orani(hn['Icerik'], pn['Icerik']) for pn in platform_nodes], default=0)
        if en_iyi_oran < esik:
            havuzda_fazla.append({'havuz_id': hn['NodeID'], 'havuz_metin': hn['Icerik']})
    return jsonify({'sonuclar': sonuclar, 'havuzda_fazla': havuzda_fazla})

# ── EXPORT API'LERİ ───────────────────────────────────────────────────────────
@app.route('/api/export/ister_listesi', methods=['GET'])
@login_gerekli
def export_ister_listesi():
    """Platforma göre ister listesini JSON olarak döner (frontend Excel/print yapacak)"""
    pid = request.args.get('platform_id')
    seviye_no = request.args.get('seviye_no')
    cur = cur_dict()
    q = """SELECT n.NodeID, n.NodeNumarasi, n.Icerik, s.SeviyeAdi, s.SeviyeNo, k.KonfigAdi,
                  ty.YontemAdi AS TestYontemi, pn.Icerik AS UstIster, pn.NodeNumarasi AS UstNumara
           FROM ister_node n
           JOIN seviye_tanim s ON n.SeviyeID=s.SeviyeID
           LEFT JOIN konfig_list k ON n.KonfigID=k.KonfigID
           LEFT JOIN test_yontemi ty ON n.TestYontemiID=ty.TestYontemiID
           LEFT JOIN ister_node pn ON n.ParentID=pn.NodeID
           WHERE n.PlatformID=%s"""
    params = [pid]
    if seviye_no:
        q += " AND s.SeviyeNo=%s"
        params.append(seviye_no)
    q += " ORDER BY s.SeviyeNo, n.NodeID"
    cur.execute(q, params)
    data = cur.fetchall()
    # Test sonuçlarını ekle
    for row in data:
        cur.execute("""SELECT ts.Sonuc, ta.AsamaAdi FROM test_sonuc ts
                       JOIN test_asama ta ON ts.TestAsamaID=ta.TestAsamaID
                       WHERE ts.NodeID=%s""", (row['NodeID'],))
        row['TestSonuclari'] = cur.fetchall()
    cur.execute("SELECT PlatformAdi FROM platform_list WHERE PlatformID=%s", (pid,))
    p = cur.fetchone()
    cur.close()
    return jsonify({'platform': p['PlatformAdi'] if p else '', 'isterler': data})

@app.route('/api/export/ta_dokuman/<int:ta_id>', methods=['GET'])
@login_gerekli
def export_ta_dokuman(ta_id):
    cur = cur_dict()
    cur.execute("SELECT t.*, p.PlatformAdi FROM ta_dokuman t JOIN platform_list p ON t.PlatformID=p.PlatformID WHERE t.TaID=%s", (ta_id,))
    ta = cur.fetchone()
    if not ta: cur.close(); return jsonify({'hata': 'Bulunamadı'}), 404
    ta['Adi'] = f"TA-{ta['PlatformAdi'].replace(' ','')}-%03d" % ta['SiraNo']
    cur.execute("SELECT * FROM ta_veri WHERE TaID=%s ORDER BY Sistem,Yon,Sira", (ta_id,))
    ta['veriler'] = cur.fetchall()
    cur.execute("""SELECT n.Icerik, s.SeviyeAdi FROM ta_sgo_baglanti b
                   JOIN ister_node n ON b.NodeID=n.NodeID
                   JOIN seviye_tanim s ON n.SeviyeID=s.SeviyeID
                   WHERE b.TaID=%s""", (ta_id,))
    ta['sgo_ler'] = cur.fetchall()
    cur.close()
    return jsonify(ta)

@app.route('/api/export/dashboard', methods=['GET'])
@login_gerekli
def export_dashboard():
    return dashboard()

# ── KONFİG ────────────────────────────────────────────────────────────────────
@app.route('/api/konfig', methods=['GET'])
@login_gerekli
def konfig_listesi():
    cur = cur_dict()
    cur.execute("SELECT * FROM konfig_list ORDER BY KonfigAdi")
    d = cur.fetchall(); cur.close(); return jsonify(d)

@app.route('/api/konfig', methods=['POST'])
@login_gerekli
def konfig_ekle():
    d = request.json; cur = mysql.connection.cursor()
    cur.execute("INSERT INTO konfig_list (KonfigAdi) VALUES (%s)", (d['KonfigAdi'],))
    mysql.connection.commit(); nid = cur.lastrowid; cur.close()
    log_kaydet('konfig_list', nid, 'Konfig', '-', d['KonfigAdi'],LogTur.CREATE.value)
    return jsonify({'KonfigID': nid, 'KonfigAdi': d['KonfigAdi']})

@app.route('/api/konfig/<int:kid>', methods=['PUT'])
@login_gerekli
def konfig_guncelle(kid):
    d = request.json; cur = cur_dict()
    cur.execute("SELECT KonfigAdi FROM konfig_list WHERE KonfigID=%s", (kid,))
    eski = cur.fetchone()
    cur.execute("UPDATE konfig_list SET KonfigAdi=%s WHERE KonfigID=%s", (d['KonfigAdi'], kid))
    mysql.connection.commit()
    if eski: log_kaydet('konfig_list', kid, 'KonfigAdi', eski['KonfigAdi'], d['KonfigAdi'],LogTur.UPDATE.value)
    cur.close(); return jsonify({'ok': True})

@app.route('/api/konfig/<int:kid>', methods=['DELETE'])
@login_gerekli
def konfig_sil(kid):     
    cur = mysql.connection.cursor() 
    cur.execute("SELECT KonfigAdi FROM konfig_list WHERE KonfigID=%s", (kid,))
    eski = cur.fetchone() 
    if eski:
        log_kaydet('konfig_list', kid, 'Konfig', eski[0], '-', LogTur.DELETE.value)
    cur.execute("DELETE FROM konfig_list WHERE KonfigID=%s", (kid,))
    mysql.connection.commit()
    cur.close()
    return jsonify({'ok': True})

# ── PLATFORM ──────────────────────────────────────────────────────────────────
@app.route('/api/platform', methods=['GET'])
@login_gerekli
def platform_listesi():
    cur = cur_dict()
    cur.execute("SELECT * FROM platform_list ORDER BY HavuzMu DESC, PlatformAdi")
    d = cur.fetchall()
    for p in d:
        p['HavuzMu'] = 1 if p.get('HavuzMu') else 0
    cur.close(); return jsonify(d)

@app.route('/api/platform', methods=['POST'])
@login_gerekli
def platform_ekle():
    d = request.json; cur = mysql.connection.cursor()
    cur.execute("INSERT INTO platform_list (PlatformAdi, HavuzMu) VALUES (%s, 0)", (d['PlatformAdi'],))
    mysql.connection.commit(); nid = cur.lastrowid; cur.close()
    log_kaydet('platform_list', nid, 'Platform','-', d['PlatformAdi'],LogTur.CREATE.value)
    return jsonify({'PlatformID': nid})

@app.route('/api/platform/<int:pid>', methods=['PUT'])
@login_gerekli
def platform_guncelle(pid):
    d = request.json; cur = cur_dict()
    cur.execute("SELECT PlatformAdi FROM platform_list WHERE PlatformID=%s", (pid,))
    eski = cur.fetchone()
    cur.execute("UPDATE platform_list SET PlatformAdi=%s WHERE PlatformID=%s", (d['PlatformAdi'], pid))
    mysql.connection.commit()
    if eski: log_kaydet('platform_list', pid, 'PlatformAdi', eski['PlatformAdi'], d['PlatformAdi'],LogTur.UPDATE.value)
    cur.close(); return jsonify({'ok': True})

@app.route('/api/platform/<int:pid>', methods=['DELETE'])
@login_gerekli
def platform_sil(pid):
    cur=cur_dict()
    cur.execute("SELECT HavuzMu,PlatformAdi FROM platform_list WHERE PlatformID=%s",(pid,))
    p=cur.fetchone()
    if not p:
        cur.close()
        return jsonify({'hata':'Platform bulunamadı.'}),404
    if p['HavuzMu']:
        cur.close()
        return jsonify({'hata':'Havuz silinemez.'}),400
    cur.execute("SELECT n.NodeID,n.Icerik FROM ister_node n WHERE n.PlatformID=%s",(pid,))
    nodes=cur.fetchall()
    for n in nodes:
        log_kaydet('ister_node',n['NodeID'],'Node',n['Icerik'],'-',LogTur.DELETE.value)
        cur.execute("DELETE FROM ister_node WHERE NodeID=%s",(n['NodeID'],))
    log_kaydet('platform_list',pid,'Platform',p['PlatformAdi'],'-',LogTur.DELETE.value)
    cur.execute("DELETE FROM platform_list WHERE PlatformID=%s",(pid,))
    mysql.connection.commit()
    cur.close()
    return jsonify({'ok':True})

# ── SEVİYE TANIM ──────────────────────────────────────────────────────────────
@app.route('/api/platform/<int:pid>/seviye', methods=['GET'])
@login_gerekli
def seviye_listesi(pid):
    cur = cur_dict()
    cur.execute("SELECT * FROM seviye_tanim WHERE PlatformID=%s ORDER BY SeviyeNo", (pid,))
    d = cur.fetchall(); cur.close(); return jsonify(d)

@app.route('/api/platform/<int:pid>/seviye_ve_asama', methods=['GET'])
@login_gerekli
def seviye_ve_asama_listesi(pid):
    """Seviyeler + test aşamalarını birleşik döner (ister ekleme dropdown için)
    Test aşamaları için SeviyeID = son seviyenin SeviyeID'si, AsamaID ayrı gelir"""
    cur = cur_dict()
    cur.execute("SELECT SeviyeID, SeviyeNo, SeviyeAdi, 'seviye' AS tip, NULL AS AsamaID FROM seviye_tanim WHERE PlatformID=%s ORDER BY SeviyeNo", (pid,))
    seviyeler = cur.fetchall()
    # Son seviyeyi bul — test isterleri bu seviyede oluşturulacak
    son_seviye_id = seviyeler[-1]['SeviyeID'] if seviyeler else None
    cur.execute("SELECT TestAsamaID, AsamaNo, AsamaAdi FROM test_asama WHERE PlatformID=%s ORDER BY AsamaNo", (pid,))
    asamalar = cur.fetchall()
    # Test aşamaları için gerçek SeviyeID (son seviye), AsamaID ayrı
    asama_listesi = [{'SeviyeID': son_seviye_id, 'SeviyeNo': 999, 'SeviyeAdi': a['AsamaAdi'],
                      'tip': 'asama', 'AsamaID': a['TestAsamaID']} for a in asamalar] if son_seviye_id else []
    cur.close()
    return jsonify(list(seviyeler) + asama_listesi)

@app.route('/api/platform/<int:pid>/seviye', methods=['POST'])
@login_gerekli
def seviye_ekle(pid):
    d = request.json; cur = cur_dict()
    cur.execute("SELECT COALESCE(MAX(SeviyeNo),0)+1 AS sira FROM seviye_tanim WHERE PlatformID=%s", (pid,))
    sira = cur.fetchone()['sira']
    cur.execute("INSERT INTO seviye_tanim (PlatformID, SeviyeNo, SeviyeAdi) VALUES (%s,%s,%s)", (pid, sira, d['SeviyeAdi']))
    mysql.connection.commit(); nid = cur.lastrowid; cur.close()
    return jsonify({'SeviyeID': nid, 'SeviyeNo': sira, 'SeviyeAdi': d['SeviyeAdi']})

@app.route('/api/seviye/<int:sid>', methods=['PUT'])
@login_gerekli
def seviye_guncelle(sid):
    d = request.json; cur = mysql.connection.cursor()
    cur.execute("UPDATE seviye_tanim SET SeviyeAdi=%s WHERE SeviyeID=%s", (d['SeviyeAdi'], sid))
    mysql.connection.commit(); cur.close(); return jsonify({'ok': True})

@app.route('/api/seviye/<int:sid>', methods=['DELETE'])
@login_gerekli
def seviye_sil(sid):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM seviye_tanim WHERE SeviyeID=%s", (sid,))
    mysql.connection.commit(); cur.close(); return jsonify({'ok': True})

# ── TEST AŞAMA ────────────────────────────────────────────────────────────────
@app.route('/api/platform/<int:pid>/test_asama', methods=['GET'])
@login_gerekli
def test_asama_listesi(pid):
    cur = cur_dict()
    cur.execute("SELECT * FROM test_asama WHERE PlatformID=%s ORDER BY AsamaNo", (pid,))
    d = cur.fetchall(); cur.close(); return jsonify(d)

@app.route('/api/platform/<int:pid>/test_asama', methods=['POST'])
@login_gerekli
def test_asama_ekle(pid):
    d = request.json; cur = cur_dict()
    cur.execute("SELECT COALESCE(MAX(AsamaNo),0)+1 AS sira FROM test_asama WHERE PlatformID=%s", (pid,))
    sira = cur.fetchone()['sira']
    cur.execute("INSERT INTO test_asama (PlatformID, AsamaNo, AsamaAdi) VALUES (%s,%s,%s)", (pid, sira, d['AsamaAdi']))
    mysql.connection.commit(); nid = cur.lastrowid; cur.close()
    return jsonify({'TestAsamaID': nid, 'AsamaNo': sira, 'AsamaAdi': d['AsamaAdi']})

@app.route('/api/test_asama/<int:aid>', methods=['PUT'])
@login_gerekli
def test_asama_guncelle(aid):
    d = request.json; cur = mysql.connection.cursor()
    cur.execute("UPDATE test_asama SET AsamaAdi=%s WHERE TestAsamaID=%s", (d['AsamaAdi'], aid))
    mysql.connection.commit(); cur.close(); return jsonify({'ok': True})

@app.route('/api/test_asama/<int:aid>', methods=['DELETE'])
@login_gerekli
def test_asama_sil(aid):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM test_asama WHERE TestAsamaID=%s", (aid,))
    mysql.connection.commit(); cur.close(); return jsonify({'ok': True})

# ── PLATFORM KONFİG ───────────────────────────────────────────────────────────
@app.route('/api/platform/<int:pid>/konfig', methods=['GET'])
@login_gerekli
def platform_konfig_listesi(pid):
    cur = cur_dict()
    cur.execute("SELECT KonfigID FROM platform_konfig WHERE PlatformID=%s", (pid,))
    d = cur.fetchall(); cur.close()
    return jsonify([r['KonfigID'] for r in d])

@app.route('/api/platform/<int:pid>/konfig', methods=['POST'])
@login_gerekli
def platform_konfig_kaydet(pid):
    ids = request.json.get('konfig_ids', [])
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM platform_konfig WHERE PlatformID=%s", (pid,))
    for kid in ids:
        cur.execute("INSERT INTO platform_konfig (PlatformID, KonfigID) VALUES (%s,%s)", (pid, kid))
    mysql.connection.commit(); cur.close(); return jsonify({'ok': True})

# ── İSTER AĞACI ───────────────────────────────────────────────────────────────
@app.route('/api/platform/<int:pid>/ister_agaci', methods=['GET'])
@login_gerekli
def ister_agaci(pid):
    numara_filtre = request.args.get('numara', '').strip()
    cur = cur_dict()
    q = """SELECT n.NodeID, n.PlatformID, n.SeviyeID, n.ParentID, n.HavuzNodeID,
                  n.KonfigID, n.NodeNumarasi, n.IsterTipi, n.HavuzKodu,
                  n.Icerik, n.TestYontemiID, n.DegistirildiMi,
                  COALESCE(n.SiraNo, n.NodeID) AS SiraNo,
                  s.SeviyeAdi, s.SeviyeNo, k.KonfigAdi, ty.YontemAdi AS TestYontemiAdi,
                  (SELECT t2.TaID FROM ta_sgo_baglanti b2
                   JOIN ta_dokuman t2 ON b2.TaID=t2.TaID WHERE b2.NodeID=n.NodeID LIMIT 1) AS ta_id
           FROM ister_node n
           JOIN seviye_tanim s ON n.SeviyeID=s.SeviyeID
           LEFT JOIN konfig_list k ON n.KonfigID=k.KonfigID
           LEFT JOIN test_yontemi ty ON n.TestYontemiID=ty.TestYontemiID
           WHERE n.PlatformID=%s"""
    params = [pid]
    if numara_filtre:
        q += " AND n.NodeNumarasi LIKE %s"
        params.append(f'%{numara_filtre}%')
    q += " ORDER BY n.ParentID IS NULL DESC, n.SiraNo, n.NodeID"
    cur.execute(q, params)
    nodes = cur.fetchall()
    cur.execute("""SELECT ts.NodeID, ts.Sonuc, ta.AsamaAdi, ta.TestAsamaID
                   FROM test_sonuc ts JOIN test_asama ta ON ts.TestAsamaID=ta.TestAsamaID
                   WHERE ta.PlatformID=%s""", (pid,))
    sonuclar = cur.fetchall()
    cur.close()
    sonuc_map = {}
    for s in sonuclar:
        if s['NodeID'] not in sonuc_map:
            sonuc_map[s['NodeID']] = []
        sonuc_map[s['NodeID']].append(s)
    for n in nodes:
        n['test_sonuclari'] = sonuc_map.get(n['NodeID'], [])
    return jsonify(nodes)

@app.route('/api/ister_node/siralama', methods=['POST'])
@login_gerekli
def ister_siralama_guncelle():
    """Sıralama değiştir — yukarı/aşağı"""
    d = request.json
    nid = d['NodeID']
    yon = d['Yon']  # 'yukari' veya 'asagi'
    cur = cur_dict()
    cur.execute("SELECT ParentID, PlatformID, SiraNo FROM ister_node WHERE NodeID=%s", (nid,))
    node = cur.fetchone()
    if not node: cur.close(); return jsonify({'hata': 'Bulunamadı'}), 404
    parent_id = node['ParentID']
    pid = node['PlatformID']
    sira = node['SiraNo'] or 0
    # Aynı seviyedeki kardeşleri bul
    if parent_id:
        cur.execute("SELECT NodeID, SiraNo FROM ister_node WHERE ParentID=%s ORDER BY SiraNo, NodeID", (parent_id,))
    else:
        cur.execute("SELECT NodeID, SiraNo FROM ister_node WHERE PlatformID=%s AND ParentID IS NULL ORDER BY SiraNo, NodeID", (pid,))
    kardesler = cur.fetchall()
    idx = next((i for i,k in enumerate(kardesler) if k['NodeID']==nid), -1)
    if idx == -1: cur.close(); return jsonify({'ok': True})
    hedef_idx = idx - 1 if yon == 'yukari' else idx + 1
    if hedef_idx < 0 or hedef_idx >= len(kardesler): cur.close(); return jsonify({'ok': True})
    hedef = kardesler[hedef_idx]
    # Sıraları değiştir
    cur2 = mysql.connection.cursor()
    cur2.execute("UPDATE ister_node SET SiraNo=%s WHERE NodeID=%s", (hedef['SiraNo'] or hedef_idx, nid))
    cur2.execute("UPDATE ister_node SET SiraNo=%s WHERE NodeID=%s", (sira or idx, hedef['NodeID']))
    mysql.connection.commit()
    cur.close(); cur2.close()
    return jsonify({'ok': True})

@app.route('/api/ister_node', methods=['POST'])
@login_gerekli
def ister_node_ekle():
    d = request.json; cur = cur_dict()
    ister_tipi = d.get('IsterTipi', 'G')
    havuz_kodu = d.get('HavuzKodu', '')
    # HavuzKodu otomatik üret (sadece havuz platformunda ve manuel girilmemişse)
    if not havuz_kodu:
        cur.execute("SELECT HavuzMu FROM platform_list WHERE PlatformID=%s", (d['PlatformID'],))
        p = cur.fetchone()
        if p and p.get('HavuzMu'):
            prefix = 'b' if ister_tipi == 'B' else 'g'
            cur.execute("SELECT COUNT(*) as cnt FROM ister_node WHERE PlatformID=%s AND IsterTipi=%s", (d['PlatformID'], ister_tipi))
            cnt = cur.fetchone()['cnt']
            havuz_kodu = f"{prefix}{cnt+1}"
    # SiraNo: en sona ekle
    if d.get('ParentID'):
        cur.execute("SELECT COALESCE(MAX(SiraNo),0)+1 AS sira FROM ister_node WHERE ParentID=%s", (d['ParentID'],))
    else:
        cur.execute("SELECT COALESCE(MAX(SiraNo),0)+1 AS sira FROM ister_node WHERE PlatformID=%s AND ParentID IS NULL", (d['PlatformID'],))
    row = cur.fetchone()
    sira = (row['sira'] if row else None) or 1
    cur2 = mysql.connection.cursor()
    cur2.execute("""INSERT INTO ister_node (PlatformID,SeviyeID,ParentID,KonfigID,NodeNumarasi,IsterTipi,HavuzKodu,SiraNo,Icerik,TestYontemiID,IlgiliAsamaID,OlusturanID)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (d['PlatformID'], d['SeviyeID'], d.get('ParentID'), d.get('KonfigID'),
                 d.get('NodeNumarasi',''), ister_tipi, havuz_kodu, sira,
                 d.get('Icerik',''), d.get('TestYontemiID'), d.get('IlgiliAsamaID'),
                 session['kullanici_id']))
    mysql.connection.commit(); nid = cur2.lastrowid; cur.close(); cur2.close()
    log_kaydet('ister_node', nid, 'Node', '-', d.get('Icerik',''),LogTur.CREATE.value)
    return jsonify({'NodeID': nid, 'HavuzKodu': havuz_kodu})

@app.route('/api/ister_node/<int:nid>', methods=['PUT'])
@login_gerekli
def ister_node_guncelle(nid):
    d = request.json; cur = cur_dict()
    cur.execute("SELECT * FROM ister_node WHERE NodeID=%s", (nid,))
    eski = cur.fetchone()
    # ParentID değişikliği — başlığa çevirince veya yerini değiştirince
    parent_id = d.get('ParentID', -1)  # -1 = değiştirilmemiş
    if parent_id != -1:
        cur.execute("""UPDATE ister_node SET Icerik=%s, TestYontemiID=%s, NodeNumarasi=%s,
                       IsterTipi=COALESCE(%s,IsterTipi),
                       HavuzKodu=COALESCE(%s,HavuzKodu),
                       KonfigID=COALESCE(%s,KonfigID),
                       SeviyeID=COALESCE(%s,SeviyeID),
                       ParentID=%s, DegistirildiMi=1
                       WHERE NodeID=%s""",
                    (d.get('Icerik'), d.get('TestYontemiID'), d.get('NodeNumarasi',''),
                     d.get('IsterTipi'), d.get('HavuzKodu') or None,
                     d.get('KonfigID'), d.get('SeviyeID'),
                     parent_id if parent_id else None, nid))
    else:
        cur.execute("""UPDATE ister_node SET Icerik=%s, TestYontemiID=%s, NodeNumarasi=%s,
                       IsterTipi=COALESCE(%s,IsterTipi),
                       HavuzKodu=COALESCE(%s,HavuzKodu),
                       KonfigID=COALESCE(%s,KonfigID),
                       SeviyeID=COALESCE(%s,SeviyeID),
                       DegistirildiMi=1
                       WHERE NodeID=%s""",
                    (d.get('Icerik'), d.get('TestYontemiID'), d.get('NodeNumarasi',''),
                     d.get('IsterTipi'), d.get('HavuzKodu') or None,
                     d.get('KonfigID'), d.get('SeviyeID'), nid))
    mysql.connection.commit()
    if eski:
        if str(eski.get('Icerik') or '') != str(d.get('Icerik') or ''):
            log_kaydet('ister_node', nid, 'Icerik', eski.get('Icerik'), d.get('Icerik'),LogTur.UPDATE.value)
        if str(eski.get('NodeNumarasi') or '') != str(d.get('NodeNumarasi') or ''):
            log_kaydet('ister_node', nid, 'NodeNumarasi', eski.get('NodeNumarasi'), d.get('NodeNumarasi'),LogTur.UPDATE.value)
    cur.close(); return jsonify({'ok': True})

@app.route('/api/ister_node/<int:nid>', methods=['DELETE'])
@login_gerekli
def ister_node_sil(nid):
    cur = cur_dict()
    cur.execute("SELECT n.PlatformID, p.HavuzMu, n.Icerik FROM ister_node n JOIN platform_list p ON n.PlatformID=p.PlatformID WHERE n.NodeID=%s", (nid,))
    node = cur.fetchone()
    log_kaydet('ister_node', nid, 'Node', node['Icerik'], '-', LogTur.DELETE.value)
    cur.execute("DELETE FROM ister_node WHERE NodeID=%s", (nid,))
    mysql.connection.commit(); cur.close(); return jsonify({'ok': True})

# ── İSTER SETİ OLUŞTUR (Havuzdan platforma kopyala) ─────────────────────────
@app.route('/api/platform/<int:pid>/ister_seti_olustur', methods=['POST'])
@login_gerekli
def ister_seti_olustur(pid):
    print(pid)
    cur = cur_dict(); cur2 = mysql.connection.cursor()
    # Havuz platformunu bul
    cur.execute("SELECT PlatformID FROM platform_list WHERE HavuzMu=1 LIMIT 1")
    havuz = cur.fetchone()
    if not havuz:
        cur.close(); return jsonify({'hata': 'Havuz platformu bulunamadı.'}), 400
    havuz_pid = havuz['PlatformID']
    print(havuz_pid)
    # Platformun seçili konfiglerini al
    cur.execute("SELECT KonfigID FROM platform_konfig WHERE PlatformID=%s", (pid,))
    konfig_ids = [r['KonfigID'] for r in cur.fetchall()]
    print(konfig_ids)

    if not konfig_ids:
        cur.close(); return jsonify({'hata': 'Platform için konfig seçilmemiş. Konfigleri kaydetiğinizden emin olun!'}), 400

    # Platformun seviyelerini al
    cur.execute("SELECT * FROM seviye_tanim WHERE PlatformID=%s ORDER BY SeviyeNo", (pid,))
    seviyeler = cur.fetchall()
    if not seviyeler:
        cur.close(); return jsonify({'hata': 'Platform için seviye tanımlanmamış.'}), 400

    # Havuzun seviyelerini al (eşleştirmek için)
    cur.execute("SELECT * FROM seviye_tanim WHERE PlatformID=%s ORDER BY SeviyeNo", (havuz_pid,))
    havuz_seviyeler = cur.fetchall()
    havuz_sev_map = {s['SeviyeNo']: s['SeviyeID'] for s in havuz_seviyeler}
    plat_sev_map = {s['SeviyeNo']: s['SeviyeID'] for s in seviyeler}

    # Mevcut node'ları sil
    cur2.execute("DELETE FROM ister_node WHERE PlatformID=%s", (pid,))
    mysql.connection.commit()

    # TA dokümanlarını sil
    cur2.execute("DELETE FROM ta_dokuman WHERE PlatformID=%s", (pid,))
    mysql.connection.commit()

    # Havuzdan seçili konfiglere ait node'ları kopyala
    konfig_str = ','.join(str(k) for k in konfig_ids)
    cur.execute(f"""SELECT n.* FROM ister_node n
                   WHERE n.PlatformID=%s AND (n.KonfigID IN ({konfig_str}) OR n.KonfigID IS NULL)
                   ORDER BY n.NodeID""", (havuz_pid,))
    havuz_nodes = cur.fetchall()

    # node_id eşleştirme haritası
    id_map = {}
    for hn in havuz_nodes:
        # Seviye eşleştirme: havuz seviye no → platform seviye ID
        cur.execute("SELECT SeviyeNo FROM seviye_tanim WHERE SeviyeID=%s", (hn['SeviyeID'],))
        sev_row = cur.fetchone()
        if not sev_row:
            continue
        sev_no = sev_row['SeviyeNo']
        if sev_no not in plat_sev_map:
            continue  # Bu platformda bu seviye yok, atla
        yeni_seviye_id = plat_sev_map[sev_no]
        yeni_parent = id_map.get(hn['ParentID']) if hn['ParentID'] else None
        cur2.execute("""INSERT INTO ister_node (PlatformID,SeviyeID,ParentID,HavuzNodeID,KonfigID,NodeNumarasi,Icerik,TestYontemiID,OlusturanID)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                     (pid, yeni_seviye_id, yeni_parent, hn['NodeID'], hn['KonfigID'],
                      hn.get('NodeNumarasi',''), hn['Icerik'], hn['TestYontemiID'], session['kullanici_id']))
        mysql.connection.commit()
        id_map[hn['NodeID']] = cur2.lastrowid

    # TA dokümanlarını kopyala
    cur.execute("SELECT * FROM ta_dokuman WHERE PlatformID=%s", (havuz_pid,))
    havuz_talar = cur.fetchall()
    ta_id_map = {}
    for ta in havuz_talar:
        cur2.execute("""INSERT INTO ta_dokuman (PlatformID,SiraNo,HavuzTaID,SolSistemAdi,SagSistemAdi)
                       VALUES (%s,%s,%s,%s,%s)""",
                     (pid, ta['SiraNo'], ta['TaID'], ta['SolSistemAdi'], ta['SagSistemAdi']))
        mysql.connection.commit()
        ta_id_map[ta['TaID']] = cur2.lastrowid
        # TA verilerini kopyala
        cur.execute("SELECT * FROM ta_veri WHERE TaID=%s", (ta['TaID'],))
        for v in cur.fetchall():
            cur2.execute("INSERT INTO ta_veri (TaID,Sistem,Yon,Icerik,Sira) VALUES (%s,%s,%s,%s,%s)",
                        (ta_id_map[ta['TaID']], v['Sistem'], v['Yon'], v['Icerik'], v['Sira']))
        # TA-SGÖ bağlantılarını kopyala
        cur.execute("SELECT * FROM ta_sgo_baglanti WHERE TaID=%s", (ta['TaID'],))
        for b in cur.fetchall():
            yeni_node = id_map.get(b['NodeID'])
            if yeni_node:
                cur2.execute("INSERT IGNORE INTO ta_sgo_baglanti (TaID,NodeID) VALUES (%s,%s)",
                            (ta_id_map[ta['TaID']], yeni_node))
        mysql.connection.commit()

    cur.close(); cur2.close()
    return jsonify({'ok': True, 'mesaj': f'{len(id_map)} ister kopyalandı.'})

# ── TEST SONUÇ ────────────────────────────────────────────────────────────────
@app.route('/api/test_sonuc', methods=['GET'])
@login_gerekli
def test_sonuc_listesi():
    pid = request.args.get('platform_id')
    asama_id = request.args.get('asama_id')
    cur = cur_dict()
    q = """SELECT ts.*, n.Icerik AS NodeIcerik, ta.AsamaAdi,
                  s.SeviyeAdi, s.SeviyeNo,
                  pn.Icerik AS ParentIcerik
           FROM test_sonuc ts
           JOIN ister_node n ON ts.NodeID=n.NodeID
           JOIN test_asama ta ON ts.TestAsamaID=ta.TestAsamaID
           JOIN seviye_tanim s ON n.SeviyeID=s.SeviyeID
           LEFT JOIN ister_node pn ON n.ParentID=pn.NodeID
           WHERE ta.PlatformID=%s"""
    params = [pid]
    if asama_id:
        q += " AND ts.TestAsamaID=%s"
        params.append(asama_id)
    q += " ORDER BY ts.NodeID"
    cur.execute(q, params); d = cur.fetchall()
    for r in d:
        if r.get('Tarih'): r['Tarih'] = r['Tarih'].strftime('%d.%m.%Y %H:%M')
    cur.close(); return jsonify(d)

@app.route('/api/test_sonuc/girilmemis', methods=['GET'])
@login_gerekli
def test_sonuc_girilmemis():
    pid = request.args.get('platform_id')
    asama_id = request.args.get('asama_id')
    cur = cur_dict()
    # En alt seviye node'ları bul (çocuğu olmayanlar)
    q = """SELECT n.NodeID, n.Icerik, n.ParentID, s.SeviyeAdi, s.SeviyeNo,
                  pn.Icerik AS ParentIcerik, ppn.Icerik AS GrandParentIcerik
           FROM ister_node n
           JOIN seviye_tanim s ON n.SeviyeID=s.SeviyeID
           LEFT JOIN ister_node pn ON n.ParentID=pn.NodeID
           LEFT JOIN ister_node ppn ON pn.ParentID=ppn.NodeID
           WHERE n.PlatformID=%s
           AND n.NodeID NOT IN (SELECT DISTINCT ParentID FROM ister_node WHERE ParentID IS NOT NULL AND PlatformID=%s)"""
    params = [pid, pid]
    if asama_id:
        q += " AND n.NodeID NOT IN (SELECT NodeID FROM test_sonuc WHERE TestAsamaID=%s)"
        params.append(asama_id)
    cur.execute(q, params); d = cur.fetchall(); cur.close(); return jsonify(d)

@app.route('/api/test_sonuc', methods=['POST'])
@login_gerekli
def test_sonuc_kaydet():
    d = request.json; cur = cur_dict()
    cur.execute("SELECT * FROM test_sonuc WHERE NodeID=%s AND TestAsamaID=%s", (d['NodeID'], d['TestAsamaID']))
    eski = cur.fetchone()
    if eski:
        cur.execute("UPDATE test_sonuc SET Sonuc=%s, Aciklama=%s, KullaniciID=%s, Tarih=NOW() WHERE TestSonucID=%s",
                    (d['Sonuc'], d.get('Aciklama',''), session['kullanici_id'], eski['TestSonucID']))
        log_kaydet('test_sonuc', eski['TestSonucID'], 'Sonuc', eski['Sonuc'], d['Sonuc'],LogTur.UPDATE.value)
    else:
        cur.execute("INSERT INTO test_sonuc (NodeID,TestAsamaID,Sonuc,Aciklama,KullaniciID) VALUES (%s,%s,%s,%s,%s)",
                    (d['NodeID'], d['TestAsamaID'], d['Sonuc'], d.get('Aciklama',''), session['kullanici_id']))
    mysql.connection.commit(); cur.close(); return jsonify({'ok': True})

# ── TA DOKUMAN ────────────────────────────────────────────────────────────────
@app.route('/api/platform/<int:pid>/ta', methods=['GET'])
@login_gerekli
def ta_listesi(pid):
    cur = cur_dict()
    cur.execute("""SELECT t.*, p.PlatformAdi,
                   (SELECT COUNT(*) FROM ta_sgo_baglanti WHERE TaID=t.TaID) AS SgoBaglanti
                   FROM ta_dokuman t JOIN platform_list p ON t.PlatformID=p.PlatformID
                   WHERE t.PlatformID=%s ORDER BY t.SiraNo""", (pid,))
    talar = cur.fetchall()
    for ta in talar:
        ta['Adi'] = f"TA-{cur.execute('SELECT PlatformAdi FROM platform_list WHERE PlatformID=%s',(pid,)) or ''}"
        p = cur_dict(); p.execute("SELECT PlatformAdi FROM platform_list WHERE PlatformID=%s",(pid,))
        pa = p.fetchone(); p.close()
        ta['Adi'] = f"TA-{(pa['PlatformAdi'] if pa else 'X').replace(' ','')}-%03d" % ta['SiraNo']
    cur.close(); return jsonify(talar)

@app.route('/api/ta/<int:ta_id>', methods=['GET'])
@login_gerekli
def ta_detay(ta_id):
    cur = cur_dict()
    cur.execute("SELECT t.*, p.PlatformAdi FROM ta_dokuman t JOIN platform_list p ON t.PlatformID=p.PlatformID WHERE t.TaID=%s", (ta_id,))
    ta = cur.fetchone()
    if not ta: cur.close(); return jsonify({'hata': 'Bulunamadı'}), 404
    ta['Adi'] = f"TA-{ta['PlatformAdi'].replace(' ','')}-%03d" % ta['SiraNo']
    cur.execute("SELECT * FROM ta_veri WHERE TaID=%s ORDER BY Sistem, Yon, Sira", (ta_id,))
    ta['veriler'] = cur.fetchall()
    cur.execute("""SELECT n.NodeID, n.Icerik, s.SeviyeAdi FROM ta_sgo_baglanti b
                   JOIN ister_node n ON b.NodeID=n.NodeID
                   JOIN seviye_tanim s ON n.SeviyeID=s.SeviyeID
                   WHERE b.TaID=%s""", (ta_id,))
    ta['sgo_ler'] = cur.fetchall()
    cur.close(); return jsonify(ta)

@app.route('/api/platform/<int:pid>/ta', methods=['POST'])
@login_gerekli
def ta_ekle(pid):
    d = request.json; cur = cur_dict()
    cur.execute("SELECT COALESCE(MAX(SiraNo),0)+1 AS sira FROM ta_dokuman WHERE PlatformID=%s", (pid,))
    sira = cur.fetchone()['sira']
    cur.execute("INSERT INTO ta_dokuman (PlatformID,SiraNo,SolSistemAdi,SagSistemAdi) VALUES (%s,%s,%s,%s)",
                (pid, sira, d.get('SolSistemAdi',''), d.get('SagSistemAdi','')))
    mysql.connection.commit(); nid = cur.lastrowid; cur.close()
    log_kaydet('ta_dokuman', pid, 'Platform', '-', d.get('SolSistemAdi',''),LogTur.CREATE.value)
    return jsonify({'TaID': nid, 'SiraNo': sira})

@app.route('/api/ta/<int:ta_id>', methods=['PUT'])
@login_gerekli
def ta_guncelle(ta_id):
    d = request.json; cur = mysql.connection.cursor()
    cur.execute("SELECT SolSistemAdi FROM ta_dokuman WHERE TaID=%s", (ta_id,))
    eski = cur.fetchone(); eski_sol = eski[0] if eski else ''
    cur.execute("UPDATE ta_dokuman SET SolSistemAdi=%s, SagSistemAdi=%s WHERE TaID=%s",
                (d.get('SolSistemAdi'), d.get('SagSistemAdi'), ta_id))
    cur.execute("DELETE FROM ta_veri WHERE TaID=%s", (ta_id,))
    for v in d.get('veriler', []):
        cur.execute("INSERT INTO ta_veri (TaID,Sistem,Yon,Icerik,Sira) VALUES (%s,%s,%s,%s,%s)",
                    (ta_id, v['sistem'], v['yon'], v['icerik'], v.get('sira',0)))
    mysql.connection.commit(); cur.close(); log_kaydet('ta_dokuman', ta_id, 'Platform', eski_sol, d.get('SolSistemAdi',''), LogTur.UPDATE.value)
    return jsonify({'ok': True})

@app.route('/api/ta/<int:ta_id>/sgo_bagla', methods=['POST'])
@login_gerekli
def ta_sgo_bagla(ta_id):
    d = request.json
    cur = cur_dict()
    node_id = d['NodeID']
    cur.execute("""
        SELECT b.TaID
        FROM ta_sgo_baglanti b
        JOIN ta_dokuman t ON b.TaID = t.TaID
        WHERE b.NodeID = %s AND b.TaID != %s
    """, (node_id, ta_id))
    mevcut = cur.fetchone()
    if mevcut:
        cur.close()
        return jsonify({
            'hata': 'Bu SGÖ isterine zaten başka bir TA bağlı (TA#' + str(mevcut['TaID']) + ').'
        }), 400
    cur.execute(
        "INSERT IGNORE INTO ta_sgo_baglanti (TaID, NodeID) VALUES (%s, %s)",
        (ta_id, node_id)
    )
    mysql.connection.commit()
    cur.close()
    return jsonify({'ok': True})

@app.route('/api/ta/<int:ta_id>/sgo_bag_kaldir/<int:node_id>', methods=['DELETE'])
@login_gerekli
def ta_sgo_bag_kaldir(ta_id, node_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM ta_sgo_baglanti WHERE TaID=%s AND NodeID=%s", (ta_id, node_id))
    mysql.connection.commit(); cur.close(); return jsonify({'ok': True})

# ── TRACEABİLİTY ──────────────────────────────────────────────────────────────
@app.route('/api/platform/<int:pid>/traceability', methods=['GET'])
@login_gerekli
def traceability(pid):
    cur = cur_dict()
    # Tüm node'ları al
    cur.execute("""SELECT n.NodeID, n.Icerik, n.ParentID, s.SeviyeAdi, s.SeviyeNo, k.KonfigAdi,
                   ty.YontemAdi AS TestYontemiAdi
                   FROM ister_node n
                   JOIN seviye_tanim s ON n.SeviyeID=s.SeviyeID
                   LEFT JOIN konfig_list k ON n.KonfigID=k.KonfigID
                   LEFT JOIN test_yontemi ty ON n.TestYontemiID=ty.TestYontemiID
                   WHERE n.PlatformID=%s ORDER BY s.SeviyeNo, n.NodeID""", (pid,))
    nodes = cur.fetchall()
    # Test sonuçlarını al
    cur.execute("""SELECT ts.NodeID, ts.Sonuc, ta.AsamaAdi
                   FROM test_sonuc ts JOIN test_asama ta ON ts.TestAsamaID=ta.TestAsamaID
                   WHERE ta.PlatformID=%s""", (pid,))
    sonuclar = cur.fetchall()
    sonuc_map = {}
    for s in sonuclar:
        if s['NodeID'] not in sonuc_map:
            sonuc_map[s['NodeID']] = []
        sonuc_map[s['NodeID']].append(s)
    # Her node için metrik hesapla
    node_map = {n['NodeID']: n for n in nodes}
    def hesapla(node_id):
        children = [n for n in nodes if n['ParentID'] == node_id]
        if not children:  # En alt seviye
            sonuclar_list = sonuc_map.get(node_id, [])
            if not sonuclar_list:
                return {'toplam': 0, 'basarili': 0, 'hatali': 0, 'durum': 'test_yok'}
            basarili = sum(1 for s in sonuclar_list if s['Sonuc'] == 'Basarili')
            hatali = sum(1 for s in sonuclar_list if s['Sonuc'] == 'Hatali')
            durum = 'basarili' if hatali == 0 and basarili > 0 else 'hatali' if hatali > 0 else 'test_yok'
            return {'toplam': len(sonuclar_list), 'basarili': basarili, 'hatali': hatali, 'durum': durum}
        else:
            alt_metrikler = [hesapla(c['NodeID']) for c in children]
            toplam = sum(m['toplam'] for m in alt_metrikler)
            basarili = sum(m['basarili'] for m in alt_metrikler)
            hatali = sum(m['hatali'] for m in alt_metrikler)
            durum = 'test_yok' if toplam == 0 else 'basarili' if hatali == 0 else 'hatali' if basarili == 0 else 'kismi'
            return {'toplam': toplam, 'basarili': basarili, 'hatali': hatali, 'durum': durum}
    for n in nodes:
        n['metrik'] = hesapla(n['NodeID'])
        n['test_sonuclari'] = sonuc_map.get(n['NodeID'], [])
    cur.close(); return jsonify(nodes)

# ── DASHBOARD ─────────────────────────────────────────────────────────────────
@app.route('/api/dashboard', methods=['GET'])
@login_gerekli
def dashboard():
    cur = cur_dict()
    cur.execute("SELECT * FROM platform_list WHERE HavuzMu=0 ORDER BY PlatformAdi")
    platformlar = cur.fetchall()
    ozet = []
    for p in platformlar:
        pid = p['PlatformID']
        cur.execute("""SELECT COUNT(DISTINCT n.NodeID) AS toplam
                       FROM ister_node n JOIN seviye_tanim s ON n.SeviyeID=s.SeviyeID
                       WHERE n.PlatformID=%s AND s.SeviyeNo=1""", (pid,))
        tgd_say = (cur.fetchone() or {}).get('toplam', 0)
        cur.execute("""SELECT COUNT(DISTINCT n.NodeID) AS toplam
                       FROM ister_node n JOIN seviye_tanim s ON n.SeviyeID=s.SeviyeID
                       WHERE n.PlatformID=%s AND s.SeviyeNo=2""", (pid,))
        sgo_say = (cur.fetchone() or {}).get('toplam', 0)
        # Test metrikleri
        cur.execute("""SELECT ts.Sonuc, COUNT(*) AS sayi FROM test_sonuc ts
                       JOIN test_asama ta ON ts.TestAsamaID=ta.TestAsamaID
                       WHERE ta.PlatformID=%s GROUP BY ts.Sonuc""", (pid,))
        test_ozet = {r['Sonuc']: r['sayi'] for r in cur.fetchall()}
        basarili = test_ozet.get('Basarili', 0)
        hatali = test_ozet.get('Hatali', 0)
        toplam_test = basarili + hatali
        ozet.append({
            'PlatformID': pid, 'PlatformAdi': p['PlatformAdi'],
            'TgdSayisi': tgd_say, 'SgoSayisi': sgo_say,
            'BasariliTest': basarili, 'HataliTest': hatali,
            'ToplamTest': toplam_test,
            'BasariOrani': round(basarili / toplam_test * 100) if toplam_test else 0
        })
    # Genel istatistikler
    cur.execute("SELECT COUNT(*) AS s FROM platform_list WHERE HavuzMu=0")
    plat_say = cur.fetchone()['s']
    cur.execute("""SELECT COUNT(DISTINCT n.NodeID) AS s FROM ister_node n
                   JOIN seviye_tanim sv ON n.SeviyeID=sv.SeviyeID
                   JOIN platform_list p ON n.PlatformID=p.PlatformID
                   WHERE sv.SeviyeNo=1 AND p.HavuzMu=0""")
    tgd_toplam = cur.fetchone()['s']
    cur.execute("""SELECT Sonuc, COUNT(*) AS s FROM test_sonuc ts
                   JOIN test_asama ta ON ts.TestAsamaID=ta.TestAsamaID
                   JOIN platform_list p ON ta.PlatformID=p.PlatformID
                   WHERE p.HavuzMu=0 GROUP BY Sonuc""")
    gen_test = {r['Sonuc']: r['s'] for r in cur.fetchall()}
    gen_bas = gen_test.get('Basarili', 0); gen_hat = gen_test.get('Hatali', 0)
    gen_top = gen_bas + gen_hat
    cur.close()
    return jsonify({
        'platform_sayisi': plat_say, 'tgd_toplam': tgd_toplam,
        'basari_orani': round(gen_bas / gen_top * 100) if gen_top else 0,
        'hatali_test': gen_hat, 'platformlar': ozet
    })

# ── KULLANICI ─────────────────────────────────────────────────────────────────
@app.route('/api/kullanici', methods=['GET'])
@login_gerekli
def kullanici_listesi():
    cur = cur_dict()
    cur.execute("SELECT KullaniciID,KullaniciAdi,AdSoyad,AktifMi FROM kullanici ORDER BY KullaniciAdi")
    d = cur.fetchall(); cur.close(); return jsonify(d)

@app.route('/api/kullanici', methods=['POST'])
@login_gerekli
def kullanici_ekle():
    d = request.json; cur = cur_dict()
    cur.execute("SELECT KullaniciID FROM kullanici WHERE KullaniciAdi=%s", (d['KullaniciAdi'],))
    if cur.fetchone(): cur.close(); return jsonify({'hata': 'Bu kullanıcı adı mevcut.'}), 400
    cur.execute("INSERT INTO kullanici (KullaniciAdi,Sifre,AdSoyad,AktifMi) VALUES (%s,%s,%s,%s)",
                (d['KullaniciAdi'], d['Sifre'], d.get('AdSoyad',''), d.get('AktifMi',1)))
    mysql.connection.commit(); nid = cur.lastrowid; cur.close()
    log_kaydet('kullanici', nid, 'Kullanıcılar', '-', d.get('KullaniciAdi',''),LogTur.CREATE.value)
    return jsonify({'KullaniciID': nid})

@app.route('/api/kullanici/<int:uid>', methods=['PUT'])
@login_gerekli
def kullanici_guncelle(uid):
    d = request.json; cur = mysql.connection.cursor()
    cur.execute("SELECT KullaniciAdi FROM kullanici WHERE KullaniciID=%s", (uid,))
    eski = cur.fetchone(); eski_kadi = eski[0] if eski else ''
    if d.get('Sifre'):
        cur.execute("UPDATE kullanici SET KullaniciAdi=%s,AdSoyad=%s,AktifMi=%s,Sifre=%s WHERE KullaniciID=%s",
                    (d['KullaniciAdi'],d.get('AdSoyad',''),d.get('AktifMi',1),d['Sifre'],uid))
    else:
        cur.execute("UPDATE kullanici SET KullaniciAdi=%s,AdSoyad=%s,AktifMi=%s WHERE KullaniciID=%s",
                    (d['KullaniciAdi'],d.get('AdSoyad',''),d.get('AktifMi',1),uid))
    mysql.connection.commit(); cur.close(); log_kaydet('kullanici', uid, 'Kullanıcılar', eski_kadi, d.get('KullaniciAdi',''),LogTur.UPDATE.value)
    return jsonify({'ok': True})

@app.route('/api/kullanici/<int:uid>', methods=['DELETE'])
@login_gerekli
def kullanici_sil(uid):
    if uid == session.get('kullanici_id'):
        return jsonify({'hata': 'Kendi hesabınızı silemezsiniz.'}), 400
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM kullanici WHERE KullaniciID=%s", (uid,))
    log_kaydet('kullanici', uid, 'Kullanıcılar', 'Silindi', '-', LogTur.DELETE.value)
    mysql.connection.commit(); cur.close(); return jsonify({'ok': True})

# ── TEST YÖNTEMİ ──────────────────────────────────────────────────────────────
@app.route('/api/test_yontemi', methods=['GET'])
@login_gerekli
def test_yontemi_listesi():
    cur = cur_dict()
    cur.execute("SELECT * FROM test_yontemi ORDER BY YontemAdi")
    d = cur.fetchall(); cur.close(); return jsonify(d)

# ── LOG ───────────────────────────────────────────────────────────────────────
@app.route('/api/log', methods=['GET'])
@login_gerekli
def log_listesi():
    cur = cur_dict()
    cur.execute("SELECT * FROM degisiklik_log ORDER BY DegisimTarihi DESC LIMIT 500")
    d = cur.fetchall()
    for r in d:
        if r.get('DegisimTarihi'): r['DegisimTarihi'] = r['DegisimTarihi'].strftime('%d.%m.%Y %H:%M:%S')
    cur.close(); return jsonify(d)

# ── İSTER TABLO (kutucuk içi tablo) ──────────────────────────────────────────
@app.route('/api/ister_tablo/hepsi', methods=['GET'])
@login_gerekli
def ister_tablo_hepsi():
    cur = cur_dict()
    cur.execute("SELECT TabloID, NodeID FROM ister_tablo")
    d = cur.fetchall(); cur.close(); return jsonify(d)

@app.route('/api/ister_tablo/<int:node_id>', methods=['GET'])
@login_gerekli
def ister_tablo_listesi(node_id):
    cur = cur_dict()
    cur.execute("SELECT * FROM ister_tablo WHERE NodeID=%s ORDER BY TabloID", (node_id,))
    d = cur.fetchall(); cur.close(); return jsonify(d)

@app.route('/api/ister_tablo', methods=['POST'])
@login_gerekli
def ister_tablo_ekle():
    import json as json_mod
    d = request.json; cur = mysql.connection.cursor()
    cur.execute("INSERT INTO ister_tablo (NodeID,TabloAdi,SutunBasliklari,Satirlar,OlusturanID) VALUES (%s,%s,%s,%s,%s)",
                (d['NodeID'], d.get('TabloAdi',''), json_mod.dumps(d.get('SutunBasliklari',[])),
                 json_mod.dumps(d.get('Satirlar',[])), session['kullanici_id']))
    mysql.connection.commit(); nid = cur.lastrowid; cur.close()
    log_kaydet('ister_tablo', nid, 'Tablo', '-', d.get('TabloAdi',''),LogTur.CREATE.value)
    return jsonify({'TabloID': nid})

@app.route('/api/ister_tablo/<int:tid>', methods=['PUT'])
@login_gerekli
def ister_tablo_guncelle(tid):
    import json as json_mod
    d = request.json
    cur = mysql.connection.cursor()
    cur.execute("SELECT TabloAdi,Satirlar FROM ister_tablo WHERE TabloID=%s", (tid,))
    row = cur.fetchone()
    eski_ad = row[0] if row else "-" 
    eski_satirlar = row[1] if row else "-" 

    cur.execute("UPDATE ister_tablo SET TabloAdi=%s, SutunBasliklari=%s, Satirlar=%s WHERE TabloID=%s",
                (d.get('TabloAdi',''), 
                 json_mod.dumps(d.get('SutunBasliklari',[])),
                 json_mod.dumps(d.get('Satirlar',[])), 
                 tid))
    mysql.connection.commit()
    cur.close()
    yeni_ad = d.get('TabloAdi', '')
    if yeni_ad:
        log_kaydet('ister_tablo', tid, 'Tablo Adı', eski_ad, yeni_ad, LogTur.UPDATE.value)
    else:
        yeni_satirlar = d.get('Satirlar', [])
        log_kaydet(
            'ister_tablo', 
            tid, 
            'Tablo Satır Sütun', 
            eski_satirlar,
            yeni_satirlar,   
            LogTur.UPDATE.value
        )
            
    return jsonify({'ok': True})
    
@app.route('/api/ister_tablo/<int:tid>', methods=['DELETE'])
@login_gerekli
def ister_tablo_sil(tid):
    cur = mysql.connection.cursor()
    cur.execute("SELECT TabloAdi FROM ister_tablo WHERE TabloID=%s", (tid,))
    p = cur.fetchone()
    cur.execute("DELETE FROM ister_tablo WHERE TabloID=%s", (tid,))
    mysql.connection.commit()
    cur.close()
    if p:
        log_kaydet('ister_tablo', tid, 'Tablo', p[0], '-', LogTur.DELETE.value)
    return jsonify({'ok': True})
# ── FİRMA GÖRÜŞÜ ──────────────────────────────────────────────────────────────
@app.route('/api/firma_gorusu/<int:node_id>', methods=['GET'])
@login_gerekli
def firma_gorusu_listesi(node_id):
    pid = request.args.get('platform_id')
    cur = cur_dict()
    q = """SELECT g.*, k.AdSoyad AS OlusturanAdi FROM firma_gorusu g
           LEFT JOIN kullanici k ON g.OlusturanID=k.KullaniciID
           WHERE g.NodeID=%s"""
    params = [node_id]
    if pid:
        q += " AND g.PlatformID=%s"
        params.append(pid)
    q += " ORDER BY g.OlusturmaTarihi"
    cur.execute(q, params)
    gorus_list = cur.fetchall()
    for g in gorus_list:
        if g.get('OlusturmaTarihi'): g['OlusturmaTarihi'] = g['OlusturmaTarihi'].strftime('%d.%m.%Y %H:%M')
        cur.execute("""SELECT y.*, k.AdSoyad AS YazanAdi FROM firma_gorusu_yanit y
                       LEFT JOIN kullanici k ON y.YazanID=k.KullaniciID
                       WHERE y.GorusID=%s ORDER BY y.OlusturmaTarihi""", (g['GorusID'],))
        yanitlar = cur.fetchall()
        for y in yanitlar:
            if y.get('OlusturmaTarihi'): y['OlusturmaTarihi'] = y['OlusturmaTarihi'].strftime('%d.%m.%Y %H:%M')
        g['yanitlar'] = yanitlar
    cur.close(); return jsonify(gorus_list)

@app.route('/api/firma_gorusu', methods=['POST'])
@login_gerekli
def firma_gorusu_ekle():
    d = request.json; cur = mysql.connection.cursor()
    cur.execute("""INSERT INTO firma_gorusu (NodeID,PlatformID,FirmaAdi,GorusIcerik,GorusOzet,GorusKategori,OlusturanID)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (d['NodeID'], d['PlatformID'], d['FirmaAdi'], d.get('GorusIcerik',''),
                 d.get('GorusOzet',''), d.get('GorusKategori',''), session['kullanici_id']))
    mysql.connection.commit(); nid = cur.lastrowid; cur.close()
    log_kaydet('firma_gorusu', nid, 'Firma Görüşleri', '-', d['FirmaAdi'], LogTur.CREATE.value)
    return jsonify({'GorusID': nid})

@app.route('/api/firma_gorusu/<int:gid>', methods=['PUT'])
@login_gerekli
def firma_gorusu_guncelle(gid):
    d = request.json; cur = mysql.connection.cursor()
    cur.execute("SELECT FirmaAdi,GorusIcerik FROM firma_gorusu WHERE GorusID=%s", (gid,))
    fa = cur.fetchone()
    if not fa:
        cur.close(); return jsonify({'ok': False, 'error': 'Kayıt bulunamadı'}), 404
    eski_firma_adi, eski_gorus_icerik = fa[0], fa[1]
    yeni_firma_adi = d.get('FirmaAdi', eski_firma_adi); gorus_icerik = d.get('GorusIcerik', eski_gorus_icerik)
    gorus_ozet = d.get('GorusOzet', None); gorus_kategori = d.get('GorusKategori', None)
    cur.execute("UPDATE firma_gorusu SET FirmaAdi=%s,GorusIcerik=%s,GorusOzet=%s,GorusKategori=%s WHERE GorusID=%s",
                (yeni_firma_adi, gorus_icerik, gorus_ozet, gorus_kategori, gid))
    mysql.connection.commit(); cur.close()
    log_kaydet('firma_gorusu', gid, 'Firma Görüşleri', eski_firma_adi, yeni_firma_adi, LogTur.UPDATE.value)
    return jsonify({'ok': True})
# todo sil log bas
@app.route('/api/firma_gorusu/<int:gid>', methods=['DELETE'])
@login_gerekli
def firma_gorusu_sil(gid):
    cur = mysql.connection.cursor()
    cur.execute("SELECT FirmaAdi FROM firma_gorusu WHERE GorusID=%s", (gid,))
    fa = cur.fetchone()
    if fa:
        log_kaydet('firma_gorusu', gid, 'Firma Görüşleri', fa['FirmaAdi'], '-', LogTur.DELETE.value)
    cur.execute("DELETE FROM firma_gorusu WHERE GorusID=%s", (gid,))
    mysql.connection.commit(); cur.close(); log_kaydet('firma_gorusu', gid, 'Firma Görüşleri', 'Silindi', '-', LogTur.DELETE.value)
        
    return jsonify({'ok': True})

@app.route('/api/firma_gorusu/<int:gid>/yanit', methods=['POST'])
@login_gerekli
def firma_gorusu_yanit_ekle(gid):
    d = request.json; cur = mysql.connection.cursor()
    cur.execute("INSERT INTO firma_gorusu_yanit (GorusID,YanitIcerik,YazanID) VALUES (%s,%s,%s)",
                (gid, d.get('YanitIcerik',''), session['kullanici_id']))
    mysql.connection.commit(); nid = cur.lastrowid; cur.close()
    log_kaydet('firma_gorusu_yanit', nid, 'Firma Görüşü Yanıtları', '-', d.get('YanitIcerik',''), LogTur.CREATE.value)
    return jsonify({'YanitID': nid})
@app.route('/api/firma_gorusu_yanit/<int:yid>', methods=['DELETE'])
@login_gerekli
def firma_gorusu_yanit_sil(yid):
    cur=mysql.connection.cursor()
    cur.execute("SELECT YanitIcerik FROM firma_gorusu_yanit WHERE YanitID=%s AND YazanID=%s",(yid,session['kullanici_id']))
    eski=cur.fetchone()
    if not eski:
        cur.close()
        return jsonify({'mesaj':'Yanıt bulunamadı veya silme yetkiniz yok.','durum':False}),403
    eski_icerik=eski[0]
    cur.execute("DELETE FROM firma_gorusu_yanit WHERE YanitID=%s AND YazanID=%s",(yid,session['kullanici_id']))
    silinen_satir=cur.rowcount
    mysql.connection.commit()
    cur.close()
    log_kaydet('firma_gorusu_yanit',yid,'Firma Görüşü Yanıtları',eski_icerik,'-',LogTur.DELETE.value)
    if silinen_satir>0:
        return jsonify({'mesaj':'Yanıt başarıyla silindi.','durum':True}),200
    else:
        return jsonify({'mesaj':'Yanıt bulunamadı veya silme yetkiniz yok.','durum':False}),403
@app.route('/api/firma_gorusu_yanit/<int:yid>', methods=['PUT'])
@login_gerekli
def firma_gorusu_yanit_guncelle(yid):
    d = request.json
    yeni_icerik = d.get('YanitIcerik')
    if not yeni_icerik or not yeni_icerik.strip():
        return jsonify({'mesaj': 'Güncellenecek içerik boş olamaz.', 'durum': False}), 400
    cur = mysql.connection.cursor()
    cur.execute("SELECT YanitIcerik FROM firma_gorusu_yanit WHERE YanitID=%s AND YazanID=%s",
                (yid, session['kullanici_id']))
    eski = cur.fetchone()
    if not eski:
        cur.close()
        return jsonify({'mesaj': 'Yanıt bulunamadı veya yetkiniz yok.', 'durum': False}), 403
    eski_icerik = eski[0]
    cur.execute("UPDATE firma_gorusu_yanit SET YanitIcerik=%s WHERE YanitID=%s AND YazanID=%s",
                (yeni_icerik, yid, session['kullanici_id']))
    guncellenen_satir = cur.rowcount
    mysql.connection.commit()
    cur.close()
    log_kaydet('firma_gorusu_yanit', yid, 'Firma Görüşü Yanıtları',
               eski_icerik, yeni_icerik, LogTur.UPDATE.value)
    if guncellenen_satir > 0:
        return jsonify({'mesaj': 'Yanıt başarıyla güncellendi.', 'durum': True}), 200
    else:
        return jsonify({'mesaj': 'İçerik zaten aynı.', 'durum': False}), 200

# ── İSTER ONAY ────────────────────────────────────────────────────────────────
@app.route('/api/ister_onay/<int:node_id>', methods=['GET'])
@login_gerekli
def ister_onay_getir(node_id):
    pid = request.args.get('platform_id')
    cur = cur_dict()
    cur.execute("SELECT * FROM ister_onay WHERE NodeID=%s AND PlatformID=%s", (node_id, pid))
    d = cur.fetchone(); cur.close()
    return jsonify(d or {'NodeID': node_id, 'PlatformID': pid, 'OnayDurumu': 0})
# todo log bas
@app.route('/api/ister_onay', methods=['POST'])
@login_gerekli
def ister_onay_kaydet():
    d = request.json; cur = mysql.connection.cursor()
    if d.get('OnayDurumu'):
        cur.execute("""INSERT INTO ister_onay (NodeID,PlatformID,OnayDurumu,OnaylayanID,OnayTarihi)
                       VALUES (%s,%s,%s,%s,NOW()) ON DUPLICATE KEY UPDATE
                       OnayDurumu=%s, OnaylayanID=%s, OnayTarihi=NOW()""",
                    (d['NodeID'], d['PlatformID'], 1, session['kullanici_id'],
                     1, session['kullanici_id']))
    else:
        cur.execute("""INSERT INTO ister_onay (NodeID,PlatformID,OnayDurumu)
                       VALUES (%s,%s,0) ON DUPLICATE KEY UPDATE OnayDurumu=0""",
                    (d['NodeID'], d['PlatformID']))
    mysql.connection.commit(); cur.close(); log_kaydet('ister_onay', d['NodeID'], 'İster Onayları', '-', '-', LogTur.UPDATE.value)
    return jsonify({'ok': True})

# ── RAPOR API'LERİ ────────────────────────────────────────────────────────────
@app.route('/api/rapor/firma_gorusleri', methods=['GET'])
@login_gerekli
def rapor_firma_gorusleri():
    pid = request.args.get('platform_id')
    cur = cur_dict()
    q = """SELECT g.GorusID, g.FirmaAdi, g.GorusKategori, g.GorusOzet,
                  g.OlusturmaTarihi, g.PlatformID, n.Icerik AS NodeIcerik, n.NodeNumarasi, n.HavuzKodu,
                  p.PlatformAdi, s.SeviyeAdi, s.SeviyeNo
           FROM firma_gorusu g
           JOIN ister_node n ON g.NodeID=n.NodeID
           JOIN platform_list p ON g.PlatformID=p.PlatformID
           JOIN seviye_tanim s ON n.SeviyeID=s.SeviyeID"""
    params = []
    if pid:
        q += " WHERE g.PlatformID=%s"
        params.append(pid)
    q += " ORDER BY g.OlusturmaTarihi DESC"
    cur.execute(q, params)
    d = cur.fetchall()
    for r in d:
        if r.get('OlusturmaTarihi'): r['OlusturmaTarihi'] = r['OlusturmaTarihi'].strftime('%d.%m.%Y')
    cur.close(); return jsonify(d)

@app.route('/api/rapor/onay_durumu', methods=['GET'])
@login_gerekli
def rapor_onay_durumu():
    pid = request.args.get('platform_id')
    cur = cur_dict()
    q = """SELECT n.NodeID, n.Icerik, n.NodeNumarasi, n.IsterTipi, n.HavuzKodu,
                  s.SeviyeAdi, s.SeviyeNo, k.KonfigAdi, p.PlatformAdi, p.PlatformID,
                  COALESCE(o.OnayDurumu, 0) AS OnayDurumu,
                  COUNT(DISTINCT g.GorusID) AS GorusSayisi
           FROM ister_node n
           JOIN seviye_tanim s ON n.SeviyeID=s.SeviyeID
           JOIN platform_list p ON n.PlatformID=p.PlatformID
           LEFT JOIN konfig_list k ON n.KonfigID=k.KonfigID
           LEFT JOIN ister_onay o ON n.NodeID=o.NodeID AND o.PlatformID=n.PlatformID
           LEFT JOIN firma_gorusu g ON n.NodeID=g.NodeID AND g.PlatformID=n.PlatformID
           WHERE p.HavuzMu=0"""
    params = []
    if pid:
        q += " AND n.PlatformID=%s"
        params.append(pid)
    q += " GROUP BY n.NodeID, o.OnayDurumu ORDER BY p.PlatformAdi, s.SeviyeNo, n.NodeID"
    cur.execute(q, params)
    d = cur.fetchall(); cur.close(); return jsonify(d)

# ── GIGN OTOMATIK NUMARALAMA ──────────────────────────────────────────────────
@app.route('/api/gign/sonraki_numara', methods=['GET'])
@login_gerekli
def gign_sonraki_numara():
    parent_id = request.args.get('parent_id')
    platform_id = request.args.get('platform_id')
    cur = cur_dict()
    if parent_id:
        cur.execute("SELECT NodeNumarasi FROM ister_node WHERE NodeID=%s", (parent_id,))
        parent = cur.fetchone()
        parent_num = (parent['NodeNumarasi'] or '') if parent else ''
        # Alt isterler: parent_num-1, parent_num-2, ...
        cur.execute("""SELECT NodeNumarasi FROM ister_node
                       WHERE ParentID=%s AND NodeNumarasi IS NOT NULL AND NodeNumarasi!=''
                       ORDER BY LENGTH(NodeNumarasi) DESC, NodeNumarasi DESC LIMIT 1""", (parent_id,))
        son = cur.fetchone()
        if son and son['NodeNumarasi']:
            sn = son['NodeNumarasi']
            try:
                if '-' in sn:
                    bas, sayi = sn.rsplit('-', 1)
                    yeni = f"{bas}-{int(sayi)+1}"
                elif parent_num:
                    yeni = f"{parent_num}-1"
                else:
                    yeni = f"{sn}-1"
            except:
                yeni = f"{parent_num}-1" if parent_num else ''
        else:
            yeni = f"{parent_num}-1" if parent_num else ''
    else:
        cur.execute("""SELECT NodeNumarasi FROM ister_node
                       WHERE PlatformID=%s AND ParentID IS NULL AND NodeNumarasi IS NOT NULL AND NodeNumarasi!=''
                       ORDER BY NodeNumarasi DESC LIMIT 1""", (platform_id,))
        son = cur.fetchone()
        if son and son['NodeNumarasi']:
            try: yeni = str(int(son['NodeNumarasi']) + 100)
            except: yeni = ''
        else: yeni = '4100'
    cur.close(); return jsonify({'numara': yeni})

# ── HAVUZ KODU FİLTRE ─────────────────────────────────────────────────────────
@app.route('/api/rapor/karsilastirma', methods=['GET'])
@login_gerekli
def rapor_karsilastirma():
    """Havuz isterlerini tüm platformlardaki karşılıklarıyla birlikte döner"""
    cur = cur_dict()
    cur.execute("SELECT PlatformID FROM platform_list WHERE HavuzMu=1 LIMIT 1")
    havuz = cur.fetchone()
    if not havuz:
        cur.close(); return jsonify({'hata': 'Havuz platformu bulunamadı'}), 404
    havuz_pid = havuz['PlatformID']
    cur.execute("SELECT PlatformID, PlatformAdi FROM platform_list WHERE HavuzMu=0 ORDER BY PlatformAdi")
    platformlar = cur.fetchall()
    cur.execute("""SELECT n.NodeID, n.ParentID, n.HavuzKodu, n.NodeNumarasi,
                          n.IsterTipi, n.Icerik, n.SiraNo,
                          s.SeviyeAdi, s.SeviyeNo, k.KonfigAdi
                   FROM ister_node n
                   JOIN seviye_tanim s ON n.SeviyeID=s.SeviyeID
                   LEFT JOIN konfig_list k ON n.KonfigID=k.KonfigID
                   WHERE n.PlatformID=%s
                   ORDER BY COALESCE(n.SiraNo, n.NodeID)""", (havuz_pid,))
    havuz_isterler = cur.fetchall()
    if platformlar:
        pid_list = ','.join(str(p['PlatformID']) for p in platformlar)
        cur.execute(f"""SELECT n.PlatformID, n.HavuzKodu, n.Icerik, n.DegistirildiMi
                       FROM ister_node n
                       WHERE n.PlatformID IN ({pid_list})
                       AND n.HavuzKodu IS NOT NULL AND n.HavuzKodu!=''""")
        plat_isterler = cur.fetchall()
    else:
        plat_isterler = []
    cur.close()
    # plat_map: {havuz_kodu: {str(platform_id): {Icerik, DegistirildiMi}}}
    # String key kullan — JSON serialize/deserialize'da int key string'e dönüşür
    plat_map = {}
    for pi in plat_isterler:
        kod = pi['HavuzKodu']
        pid_str = str(pi['PlatformID'])
        if kod not in plat_map:
            plat_map[kod] = {}
        plat_map[kod][pid_str] = {
            'Icerik': pi['Icerik'],
            'DegistirildiMi': pi['DegistirildiMi']
        }
    return jsonify({
        'platformlar': platformlar,
        'havuz_isterler': havuz_isterler,
        'plat_map': plat_map
    })

@app.route('/api/havuz_kodu/karsilastir', methods=['GET'])
@login_gerekli
def havuz_kodu_karsilastir():
    """Bir havuz kodundaki isterin hangi platformlarda nasıl göründüğünü döner"""
    kod = request.args.get('kod')
    cur = cur_dict()
    # Havuzdaki orijinal ister
    cur.execute("""SELECT n.*, p.PlatformAdi, s.SeviyeAdi FROM ister_node n
                   JOIN platform_list p ON n.PlatformID=p.PlatformID
                   JOIN seviye_tanim s ON n.SeviyeID=s.SeviyeID
                   WHERE n.HavuzKodu=%s""", (kod,))
    sonuclar = cur.fetchall()
    cur.close()
    return jsonify(sonuclar)

@app.route('/api/ister_node/by_kod', methods=['GET'])
@login_gerekli
def ister_by_kod():
    """HavuzKodu'na göre tüm platformlardaki isterleri döner"""
    kod = request.args.get('kod')
    cur = cur_dict()
    cur.execute("""SELECT n.*, p.PlatformAdi, p.HavuzMu, s.SeviyeAdi, k.KonfigAdi
                   FROM ister_node n
                   JOIN platform_list p ON n.PlatformID=p.PlatformID
                   JOIN seviye_tanim s ON n.SeviyeID=s.SeviyeID
                   LEFT JOIN konfig_list k ON n.KonfigID=k.KonfigID
                   WHERE n.HavuzKodu=%s ORDER BY p.HavuzMu DESC, p.PlatformAdi""", (kod,))
    d = cur.fetchall(); cur.close()
    return jsonify(d)

@app.route('/api/tum_isterler', methods=['GET'])
@login_gerekli
def tum_isterler():
    """Tüm platformların isterlerini PlatformAdi ile birlikte döner"""
    pid = request.args.get('platform_id')  # opsiyonel — tek platform filtresi
    havuz_kodu = request.args.get('havuz_kodu')  # opsiyonel — kod filtresi
    cur = cur_dict()
    q = """SELECT n.NodeID, n.PlatformID, n.ParentID, n.NodeNumarasi,
                  n.IsterTipi, n.HavuzKodu, n.Icerik, n.DegistirildiMi,
                  COALESCE(n.SiraNo, n.NodeID) AS SiraNo,
                  p.PlatformAdi, p.HavuzMu,
                  s.SeviyeAdi, s.SeviyeNo, k.KonfigAdi
           FROM ister_node n
           JOIN platform_list p ON n.PlatformID=p.PlatformID
           JOIN seviye_tanim s ON n.SeviyeID=s.SeviyeID
           LEFT JOIN konfig_list k ON n.KonfigID=k.KonfigID
           WHERE p.HavuzMu=0"""
    params = []
    if pid:
        q += " AND n.PlatformID=%s"
        params.append(pid)
    if havuz_kodu:
        q += " AND n.HavuzKodu=%s"
        params.append(havuz_kodu)
    q += " ORDER BY p.PlatformAdi, n.SiraNo, n.NodeID"
    cur.execute(q, params)
    d = cur.fetchall(); cur.close()
    return jsonify(d)

# ── TOPLU UPLOAD ──────────────────────────────────────────────────────────────
@app.route('/api/ister_bullet/hepsi', methods=['GET'])
@login_gerekli
def bullet_hepsi():
    cur = cur_dict()
    cur.execute("SELECT BulletID, NodeID FROM ister_bullet")
    d = cur.fetchall(); cur.close(); return jsonify(d)
    
@app.route('/api/ister_bullet/<int:node_id>', methods=['GET'])
@login_gerekli
def bullet_listesi(node_id):
    cur = cur_dict()
    cur.execute("SELECT * FROM ister_bullet WHERE NodeID=%s ORDER BY SiraNo, BulletID", (node_id,))
    d = cur.fetchall(); cur.close(); return jsonify(d)

@app.route('/api/ister_bullet', methods=['POST'])
@login_gerekli
def bullet_ekle():
    d = request.json; cur = cur_dict()
    cur.execute("SELECT COALESCE(MAX(SiraNo),0)+1 AS sira FROM ister_bullet WHERE NodeID=%s", (d['NodeID'],))
    sira = cur.fetchone()['sira']
    cur.execute("INSERT INTO ister_bullet (NodeID,SiraNo,Icerik,OlusturanID) VALUES (%s,%s,%s,%s)",
                (d['NodeID'], sira, d['Icerik'], session['kullanici_id']))
    mysql.connection.commit(); bid = cur.lastrowid; cur.close()
    log_kaydet('ister_bullet', bid, 'Bullet', '-',  d['Icerik'],LogTur.CREATE.value)
    return jsonify({'BulletID': bid, 'SiraNo': sira})

@app.route('/api/ister_bullet/<int:bid>', methods=['PUT'])
@login_gerekli
def bullet_guncelle(bid):
    d = request.json; cur = cur_dict()
    cur.execute("SELECT Icerik FROM ister_bullet WHERE BulletID=%s", (bid,))
    icerik = cur.fetchone()['Icerik']
    log_kaydet('ister_bullet', bid, 'Bullet', icerik,  d['Icerik'],LogTur.UPDATE.value)
    cur.execute("UPDATE ister_bullet SET Icerik=%s WHERE BulletID=%s", (d['Icerik'], bid))
    mysql.connection.commit(); cur.close(); return jsonify({'ok': True})

@app.route('/api/ister_bullet/<int:bid>', methods=['DELETE'])
@login_gerekli
def bullet_sil(bid):
    cur = cur_dict()
    cur.execute("SELECT Icerik FROM ister_bullet WHERE BulletID=%s", (bid,))
    icerik = cur.fetchone()['Icerik']
    log_kaydet('ister_bullet', bid, 'Bullet', icerik, '-', LogTur.DELETE.value)
    cur.execute("DELETE FROM ister_bullet WHERE BulletID=%s", (bid,))
    mysql.connection.commit(); cur.close(); return jsonify({'ok': True})

@app.route('/api/ister_bullet/siralama', methods=['POST'])
@login_gerekli
def bullet_siralama():
    d = request.json; cur = cur_dict()
    cur.execute("SELECT NodeID, SiraNo FROM ister_bullet WHERE BulletID=%s", (d['BulletID'],))
    b = cur.fetchone()
    if not b: cur.close(); return jsonify({'ok': True})
    yon = d.get('Yon','asagi')
    cur.execute("SELECT BulletID, SiraNo FROM ister_bullet WHERE NodeID=%s ORDER BY SiraNo, BulletID", (b['NodeID'],))
    tum = cur.fetchall()
    idx = next((i for i,x in enumerate(tum) if x['BulletID']==d['BulletID']), -1)
    hedef = idx-1 if yon=='yukari' else idx+1
    if 0 <= hedef < len(tum):
        cur2 = mysql.connection.cursor()
        cur2.execute("UPDATE ister_bullet SET SiraNo=%s WHERE BulletID=%s", (tum[hedef]['SiraNo'], d['BulletID']))
        cur2.execute("UPDATE ister_bullet SET SiraNo=%s WHERE BulletID=%s", (tum[idx]['SiraNo'], tum[hedef]['BulletID']))
        mysql.connection.commit(); cur2.close()
    cur.close(); return jsonify({'ok': True})
@app.route('/api/toplu_upload', methods=['POST'])
@login_gerekli
def toplu_upload():
    """Toplu ister yükleme: liste halinde isterler"""
    d = request.json
    pid = d.get('platform_id')
    seviye_id = d.get('seviye_id')
    parent_id = d.get('parent_id')
    konfig_id = d.get('konfig_id')
    ister_tipi = d.get('ister_tipi', 'G')
    isterler = d.get('isterler', [])
    if not isterler or not pid or not seviye_id:
        return jsonify({'hata': 'Eksik parametre'}), 400
    cur = cur_dict()
    cur2 = mysql.connection.cursor()
    # Havuz kontrolü
    cur.execute("SELECT HavuzMu FROM platform_list WHERE PlatformID=%s", (pid,))
    p = cur.fetchone()
    is_havuz = p and p.get('HavuzMu')
    # Son numara bul
    if parent_id:
        cur.execute("SELECT NodeNumarasi FROM ister_node WHERE NodeID=%s", (parent_id,))
        parent_node = cur.fetchone()
        parent_num = parent_node['NodeNumarasi'] if parent_node and parent_node['NodeNumarasi'] else ''
    else:
        parent_num = ''
    # Son sıra numarasını bul
    if parent_id:
        cur.execute("""SELECT NodeNumarasi FROM ister_node WHERE ParentID=%s AND NodeNumarasi IS NOT NULL
                       ORDER BY NodeNumarasi DESC LIMIT 1""", (parent_id,))
    else:
        cur.execute("""SELECT NodeNumarasi FROM ister_node WHERE PlatformID=%s AND ParentID IS NULL
                       AND NodeNumarasi IS NOT NULL ORDER BY NodeNumarasi DESC LIMIT 1""", (pid,))
    son = cur.fetchone()
    if son and son['NodeNumarasi']:
        try:
            parts = son['NodeNumarasi'].rsplit('.', 1)
            son_sayi = int(parts[1]) if len(parts)==2 else int(son['NodeNumarasi'])
            prefix = parts[0]+'.' if len(parts)==2 else ''
        except: son_sayi=0; prefix=parent_num+'.' if parent_num else ''
    else:
        son_sayi = 0; prefix = parent_num+'.' if parent_num else ''
    # Havuz kodu sayacı
    prefix_kod = 'b' if ister_tipi=='B' else 'g'
    cur.execute("SELECT COUNT(*) as cnt FROM ister_node WHERE PlatformID=%s AND IsterTipi=%s", (pid, ister_tipi))
    kodSay = cur.fetchone()['cnt']
    eklenenler = []
    for i, icerik in enumerate(isterler):
        icerik = str(icerik).strip()
        if not icerik: continue
        son_sayi += 1
        numara = f"{prefix}{son_sayi}"
        havuz_kodu = f"{prefix_kod}{kodSay+i+1}" if is_havuz else ''
        cur2.execute("""INSERT INTO ister_node (PlatformID,SeviyeID,ParentID,KonfigID,NodeNumarasi,IsterTipi,HavuzKodu,Icerik,OlusturanID)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (pid, seviye_id, parent_id, konfig_id, numara, ister_tipi, havuz_kodu, icerik, session['kullanici_id']))
        mysql.connection.commit()
        eklenenler.append({'NodeID': cur2.lastrowid, 'NodeNumarasi': numara, 'Icerik': icerik})
    cur.close(); cur2.close()
    return jsonify({'eklenenler': eklenenler, 'toplam': len(eklenenler)})

# ── HAVUZ PLATFORM TEKİ DÜZELT ────────────────────────────────────────────────
@app.route('/api/admin/havuz_duzenle', methods=['POST'])
@login_gerekli
def havuz_duzenle():
    """Birden fazla havuz platformu varsa birini kaldır"""
    cur = cur_dict()
    cur.execute("SELECT PlatformID FROM platform_list WHERE HavuzMu=1 ORDER BY PlatformID")
    havuzlar = cur.fetchall()
    if len(havuzlar) > 1:
        # İlkini bırak, diğerlerini sil
        for h in havuzlar[1:]:
            cur.execute("UPDATE platform_list SET HavuzMu=0 WHERE PlatformID=%s", (h['PlatformID'],))
        mysql.connection.commit()
        cur.close()
        return jsonify({'ok': True, 'mesaj': f"{len(havuzlar)-1} fazla havuz düzeltildi"})
    cur.close(); return jsonify({'ok': True, 'mesaj': 'Havuz zaten tek'})

# ── SAYFALAR (YENİ) ───────────────────────────────────────────────────────────
@app.route('/raporlar')
@login_gerekli
def raporlar_sayfasi(): return render_template('raporlar.html')

if __name__ == '__main__':
    import sys
    if '--dev' in sys.argv:
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        from waitress import serve
        print("İster Yönetim Sistemi v2 başlatıldı.")
        print("Tarayıcıda açın: http://localhost:5000")
        serve(app, host='0.0.0.0', port=5000, threads=8)