# Gelişmiş Otomatik Tıklayıcı (Minecraft için)

Bu proje, özellikle Minecraft gibi oyunlarda çeşitli tıklama otomasyonu ihtiyaçlarını karşılamak üzere tasarlanmış gelişmiş bir otomatik tıklayıcı uygulamasıdır. Kullanıcılara sol ve sağ fare tıklamaları için ayrı ayrı yapılandırılabilir çeşitli tıklama modları ve ayarları sunar.

## İçindekiler

- [Giriş ve Amaç](#giriş-ve-amaç)
- [Ön Koşullar](#ön-koşullar)
- [Kurulum](#kurulum)
- [Uygulamayı Başlatma](#uygulamayı-başlatma)
- [Temel Kullanım Adımları](#temel-kullanım-adımları)
- [Ana Özellikler (Tıklama Modları)](#ana-özellikler-tıklama-modları)
- [Kodun Genel Yapısı](#kodun-genel-yapısı)
- [Gelecekte Eklenebilecek Özellikler](#gelecekte-eklenebilecek-özellikler-öneriler)
- [Düzeltilebilecek ve Geliştirilebilecek Alanlar](#düzeltilebilecek-ve-geliştirilebilecek-alanlar-analiz)
- [Minecraft Odaklı Notlar](#minecraft-odaklı-notlar)
- [Uyarı](#uyarı)

## Giriş ve Amaç

Bu otomatik tıklayıcı, fare tıklamalarını otomatikleştirmek için güçlü ve esnek bir araç sağlamayı amaçlamaktadır. Özellikle Minecraft oyuncuları düşünülerek geliştirilmiş olup, PvP (Oyuncuya Karşı Oyuncu) senaryolarında veya kaynak toplama (farm) gibi tekrarlayan görevlerde avantaj sağlayabilir. Uygulama, kullanıcıların tıklama hızlarını (CPS - Saniyedeki Tıklama Sayısı), tıklama zamanlamasındaki rastgeleliği ve fare imlecinin hareketlerindeki küçük sapmaları (jitter) hassas bir şekilde ayarlamalarına olanak tanır.

## Ön Koşullar

-   **Python:** Python 3.6 veya daha yeni bir sürümü. (Önerilen: Python 3.7+)
-   **İşletim Sistemi:**
    -   Windows
    -   macOS
    -   Linux
    (Uygulama `pyautogui` ve `pynput` kütüphanelerini kullandığı için bu platformlarda çalışması beklenir.)

## Kurulum

1.  **Projeyi Klonlayın veya İndirin:**
    ```bash
    git clone <proje-linki>
    cd <proje-dizini>
    ```
    (Eğer proje bir Git reposu değilse, dosyaları bir dizine kopyalayın.)

2.  **Gerekli Kütüphaneleri Kurun:**
    Proje dizininde bir `requirements.txt` dosyası oluşturmanız ve aşağıdaki içeriği eklemeniz önerilir:
    ```
    pyautogui
    pynput
    perlin-noise
    ```
    Ardından, bu kütüphaneleri yüklemek için terminal veya komut istemcisinde aşağıdaki komutu çalıştırın:
    ```bash
    pip install -r requirements.txt
    ```
    Alternatif olarak, kütüphaneleri tek tek de yükleyebilirsiniz:
    ```bash
    pip install pyautogui pynput perlin-noise
    ```

## Uygulamayı Başlatma

Kütüphaneler kurulduktan sonra, uygulamayı projenin ana dizininden aşağıdaki komutla başlatabilirsiniz:

```bash
python autoclicker_app.py
```

Bu komut, uygulamanın grafik kullanıcı arayüzünü (GUI) açacaktır.

## Temel Kullanım Adımları

Uygulama arayüzü aşağıdaki ana bölümlerden oluşur:

1.  **Durum Göstergesi:** Uygulamanın mevcut durumunu gösterir (Çalışıyor, Durduruldu, Beklemede, Hatalı Ayar).
2.  **Anlık CPS Göstergesi:** Aktif tıklama sırasında saniyedeki gerçek tıklama sayısını gösterir.
3.  **Sol Tık Ayarları / Sağ Tık Ayarları Sekmeleri:** Sol ve sağ fare tıklamaları için ayrı ayrı ayar yapmanızı sağlar. Her sekme şunları içerir:
    *   **Tıklama Modu:** Farklı tıklama davranışları arasından seçim yapmanızı sağlar (örn: Sabit, Dalgalı, Patlama).
    *   **Hedef Hız (CPS) / Ortalama Hız (CPS) / Zirve Hız (CPS):** Seçilen moda bağlı olarak tıklama hızını ayarlamanızı sağlar.
    *   **Moda Özel Ayarlar:** Bazı modlar ek ayarlar gerektirebilir (örn: Patlama süresi).
    *   **Zamanlama Rastgeleliği (± ms):** Tıklamalar arasındaki süreyi rastgeleleştirerek daha insan benzeri bir davranış sağlar.
    *   **Jitter Yoğunluğu (Piksel):** Tıklama konumuna küçük, rastgele sapmalar ekler.
4.  **Genel Kontroller ve Tuş Atama:**
    *   **Aktif Tıklama Yapılandırması:**
        *   `Use Left Click Settings`: Sadece sol tık ayarlarını kullanır.
        *   `Use Right Click Settings`: Sadece sağ tık ayarlarını kullanır.
        *   `Use Both Settings`: Hem sol hem de sağ tık ayarlarını sırayla kullanır.
    *   **Başlat / Durdur Butonu:** Otomatik tıklamayı başlatır veya durdurur.
    *   **Tetikleyici Ata Butonu:** Otomatik tıklamayı başlatmak/durdurmak için bir klavye tuşu veya fare düğmesi atamanızı sağlar.
        *   Atama modundayken, istediğiniz tuşa basın veya fare düğmesine tıklayın.
        *   İptal etmek için `ESC` tuşuna basın.
    *   **Atanan Tetikleyici Göstergesi:** Hangi tuşun veya düğmenin atandığını gösterir.
5.  **Toplam Tıklama Sayacı:** Başlatıldığından beri yapılan toplam tıklama sayısını gösterir.
6.  **Acil Kapatma:** `F12` tuşuna basmak uygulamayı anında kapatır.

**Ayarları Yapılandırma ve Kullanım:**

1.  **Tıklama Türünü Seçin:** Sol tık, sağ tık veya her ikisi için mi ayar yapmak istediğinize karar verin ve ilgili sekmeyi veya "Aktif Tıklama Yapılandırması"nı seçin.
2.  **Tıklama Modunu Seçin:** İstediğiniz tıklama davranışına uygun modu seçin.
3.  **Hızı Ayarlayın:** CPS kaydırıcısını kullanarak istediğiniz tıklama hızını ayarlayın.
4.  **Moda Özel Ayarları Yapın:** Seçtiğiniz modun ek ayarları varsa (örn: Patlama süresi), bunları yapılandırın.
5.  **Rastgelelik ve Jitter'ı Ayarlayın:** Zamanlama rastgeleliğini ve jitter yoğunluğunu isteğinize göre ayarlayın.
6.  **Tetikleyici Atayın:** "Tetikleyici Ata" butonuna tıklayın ve ardından otomatik tıklamayı başlatıp durdurmak için kullanmak istediğiniz klavye tuşuna veya fare düğmesine basın/tıklayın.
7.  **Başlatın:** "Başlat" butonuna tıklayın veya atadığınız tetikleyici tuşa/düğmeye basın. Tıklama işlemi başlayacaktır.
8.  **Durdurun:** "Durdur" butonuna tıklayın veya atadığınız tetikleyici tuşa/düğmeye tekrar basın.

## Ana Özellikler (Tıklama Modları)

Uygulama, farklı senaryolar için çeşitli tıklama modları sunar:

*   **Sabit:** Belirlenen CPS değerinde sabit hızla tıklar.
*   **Dalgalı (Sinüs):** Tıklama hızını bir sinüs dalgası şeklinde, belirlenen ortalama CPS etrafında dalgalandırır. Bu, daha doğal bir tıklama paterni oluşturur.
*   **Patlama (Burst):** Kısa bir süre için yüksek hızda tıklar, ardından durur veya yavaşlar. Özellikle hızlı saldırı veya etkileşim gerektiren durumlar için kullanışlıdır.
    *   **Özel Ayar:** `Patlama Süresi (sn)`: Patlamanın ne kadar süreceğini belirler.
*   **Gerçekçi (Perlin):** Perlin gürültü algoritmasını kullanarak tıklama hızı ve jitter üzerinde daha karmaşık ve doğal hissettiren değişimler oluşturur.
*   **Rastgele Aralık:** Belirlenen minimum ve maksimum CPS değerleri arasında rastgele bir hızda tıklar.
    *   **Özel Ayarlar:**
        *   `Min CPS (Rastgele)`: Minimum tıklama hızı.
        *   `Max CPS (Rastgele)`: Maksimum tıklama hızı.
*   **Pattern (Desen):** Kullanıcının milisaniye cinsinden tanımladığı bir gecikme desenine göre tıklar. Bu, çok özel tıklama ritimleri oluşturmak için kullanılabilir.
    *   **Özel Ayar:** `Pattern (gecikmeler ms, '-' ile ayrılmış)`: Örneğin, `100-80-120` deseni, ilk tıklamadan sonra 100ms, ikinciden sonra 80ms, üçüncüden sonra 120ms bekler ve sonra başa döner.

**Sol ve Sağ Tıklama için Ayrı Yapılandırma:**
Uygulama, sol fare tıklaması ve sağ fare tıklaması için tamamen bağımsız modlar ve ayarlar yapılandırmanıza olanak tanır. "Aktif Tıklama Yapılandırması" seçeneği ile hangisinin (veya her ikisinin birden) kullanılacağını seçebilirsiniz.

## Kodun Genel Yapısı

Proje aşağıdaki ana Python dosyalarından oluşur:

*   **`autoclicker_app.py`:** Uygulamanın ana giriş noktasıdır. `AppCore` sınıfını başlatır ve çalıştırır.
*   **`core.py`:** Uygulamanın çekirdek mantığını içerir. Tıklama döngüsü, tuş dinleyicileri, durum yönetimi ve UI ile etkileşimlerden sorumludur. `AppCore` sınıfını barındırır.
*   **`ui.py`:** Grafik kullanıcı arayüzünü (GUI) oluşturur ve yönetir. `tkinter` kütüphanesini kullanır. Kullanıcı etkileşimlerini alır ve `AppCore`'a iletir. `AutoClickerUI` sınıfını barındırır.
*   **`click_modes.py`:** Farklı tıklama modlarının (Sabit, Dalgalı, Patlama vb.) mantığını içerir. Her mod, `ClickMode` temel sınıfından türetilmiştir.

## Gelecekte Eklenebilecek Özellikler (Öneriler)

*   **Ayarları Kaydetme/Yükleme:** Kullanıcıların sık kullandıkları ayar profillerini kaydedip daha sonra kolayca yükleyebilmeleri.
*   **Belirli Pencereye/Uygulamaya Özel Tıklama:** Otomatik tıklayıcının sadece belirli bir pencere veya uygulama aktifken çalışması.
*   **Daha Gelişmiş Tıklama Desenleri/Script Desteği:** Kullanıcıların Lua gibi bir script diliyle kendi karmaşık tıklama senaryolarını yazabilmeleri.
*   **Klavye Tuşlarını Otomatik Basma:** Fare tıklamalarına ek olarak klavye tuşlarını da otomatikleştirebilme.
*   **Daha Fazla Tıklama Modu:** Örneğin, zamanla hızı artan/azalan modlar, belirli bir sayıda tıklama yapıp duran modlar.
*   **Arayüz İyileştirmeleri:** Daha modern bir görünüm ve his, tema seçenekleri.
*   **Çoklu Dil Desteği.**

## Düzeltilebilecek ve Geliştirilebilecek Alanlar (Analiz)

*   **"Use Both Settings" Zamanlaması:** `core.py` içindeki `_click_loop` metodunda, "Use Both Settings" (Hem Sol Hem Sağ Tık) aktifken sol ve sağ tıklamaların zamanlaması şu anki uygulamada basitleştirilmiştir. Her iki tıklama türünün de kendi CPS ayarlarına daha hassas bir şekilde uyması için bu mantık geliştirilebilir (örneğin, her tıklama türü için ayrı zamanlayıcılar veya daha karmaşık bir önceliklendirme sistemi ile).
*   **Hata Yönetimi:** Kullanıcı girdilerinin doğrulanması ve olası hataların kullanıcıya daha açıklayıcı bir şekilde bildirilmesi iyileştirilebilir.
*   **Kod İçi Dokümantasyon:** Fonksiyonlar ve sınıflar için docstring'ler daha kapsamlı hale getirilebilir.
*   **Test Kapsamı:** `tests/` klasörü mevcut olsa da, birim ve entegrasyon testlerinin sayısı ve kapsamı artırılarak kod kalitesi ve güvenilirliği artırılabilir.
*   **Kaynak Kullanımı:** Uzun süreli kullanımlarda uygulamanın kaynak (CPU, bellek) tüketimi optimize edilebilir.

## Minecraft Odaklı Notlar

Bu otomatik tıklayıcı, Minecraft oynarken çeşitli avantajlar sağlayabilir:

*   **PvP (Oyuncuya Karşı Oyuncu):** Yüksek ve tutarlı CPS (saniyedeki tıklama sayısı) elde etmek, özellikle "jitter clicking" veya "butterfly clicking" gibi teknikleri simüle ederek savaşlarda üstünlük sağlayabilir. "Gerçekçi (Perlin)" veya "Dalgalı (Sinüs)" modları, daha az tespit edilebilir tıklama desenleri sunabilir.
*   **Kaynak Toplama (Farming):** Uzun süre boyunca blok kırmak veya mob kesmek gibi tekrarlayan görevleri otomatikleştirebilir. Örneğin, bir cobblestone jeneratöründe sürekli sol tık yapmak veya bir mob farmında sürekli kılıç sallamak için kullanılabilir.
*   **Köprü Yapma (Bridging):** Bazı köprü yapma tekniklerinde hızlı ve ritmik tıklamalar gereklidir. "Pattern (Desen)" modu bu tür özel ritimler için ayarlanabilir.
*   **AFK (Klavye Başında Değil) Görevleri:** Basit AFK farm'larında otomatik tıklama sağlayarak karakterinizin çalışmaya devam etmesini sağlayabilir.

## Uyarı

Otomatik tıklayıcılar veya benzeri otomasyon araçları, birçok çevrimiçi oyunun (Minecraft sunucuları dahil) hizmet şartlarına veya kurallarına aykırı olabilir. Bu tür araçların kullanımı, hesabınızın geçici veya kalıcı olarak yasaklanmasıyla sonuçlanabilir. **Bu uygulamayı kullanırken tüm risk kullanıcıya aittir.** Lütfen oynadığınız sunucuların kurallarını kontrol edin ve adil oyun prensiplerine uyun. Geliştirici, uygulamanın kötüye kullanımından veya sonuçlarından sorumlu değildir.
