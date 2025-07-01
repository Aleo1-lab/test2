# Gerçekçi Jitter Simülatörü v4.0

Bu uygulama, fare tıklamalarını otomatikleştirmek için gelişmiş ve özelleştirilebilir bir araçtır. Çeşitli tıklama modları ve ayarları ile kullanıcıların ihtiyaçlarına göre gerçekçi fare davranışları simüle etmelerini sağlar.

## Özellikler

*   **Çoklu Tıklama Modları:**
    *   **Sabit:** Belirlediğiniz sabit bir hızda (CPS - Saniyedeki Tıklama Sayısı) sürekli tıklama yapar.
    *   **Dalgalı (Sinüs):** Tıklama hızını bir sinüs dalgası formunda periyodik olarak artırır ve azaltır.
    *   **Patlama:** Kısa bir süre için tanımlanan zirve hıza ulaşır, ardından durur veya normale döner.
    *   **Gerçekçi (Perlin):** Perlin gürültü algoritmalarını kullanarak hem tıklama hızında hem de fare imlecinin küçük hareketlerinde (jitter) doğal ve daha az tespit edilebilir bir rastgelelik sunar.
*   **Detaylı Ayarlar:**
    *   **Hedef/Ortalama Hız (CPS):** Tıklama moduna bağlı olarak saniyedeki tıklama sayısını ayarlayın.
    *   **Zamanlama Rastgeleliği:** Tıklamalar arasındaki süreye milisaniye cinsinden rastgelelik ekleyerek insan benzeri bir ritim oluşturun.
    *   **Jitter Yoğunluğu:** Tıklama sırasında fare imlecinin kaç piksellik bir alanda rastgele hareket edeceğini belirleyin.
    *   **Fare Tuşu:** Otomatik tıklamalar için Sol veya Sağ fare tuşunu seçin.
    *   **Patlama Süresi:** "Patlama" modu için aktif kalma süresini saniye cinsinden ayarlayın.
*   **Kullanıcı Dostu Arayüz:**
    *   Anlaşılır ve kolay kullanımlı grafiksel kullanıcı arayüzü (GUI).
    *   Anlık CPS ve toplam tıklama sayısı göstergeleri.
    *   Durum bilgisi (Çalışıyor, Beklemede, Durduruldu).
    *   Ayarlar için fare üzerine gelince açıklayıcı ipuçları.
*   **Esnek Kontroller:**
    *   Uygulama içinden Başlat/Durdur butonu.
    *   Özelleştirilebilir bir klavye tuşu ile tıklamayı başlatma/durdurma.
    *   **F12 Tuşu ile Acil Kapatma:** Herhangi bir durumda uygulamayı anında sonlandırmak için.

## Ön Koşullar

*   **Python:** Python 3.6 veya daha yeni bir sürümü. (Uygulama Python 3.x ile geliştirilmiştir).
*   **İşletim Sistemi:** Windows, macOS veya Linux. Temel kütüphaneler platformlar arası uyumludur.
*   **PIP:** Python paket yükleyicisi. Genellikle Python ile birlikte gelir.

## Kurulum

1.  **Proje Dosyalarını İndirin:**
    Bu repoyu klonlayın veya ZIP olarak indirin ve dosyaları bir klasöre çıkarın.

2.  **Gerekli Kütüphaneleri Yükleyin:**
    Uygulamanın çalışması için bazı Python kütüphanelerine ihtiyacı vardır. Bir terminal veya komut istemi açın ve proje klasörüne giderek aşağıdaki komutları çalıştırın:

    ```bash
    pip install pyautogui pynput perlin-noise
    ```
    *   `pyautogui`: Fare ve klavye otomasyonu için.
    *   `pynput`: Klavye olaylarını dinlemek için (tetikleyici tuş, acil kapatma).
    *   `perlin-noise`: "Gerçekçi (Perlin)" modu için gürültü üretimi.
    *   `tkinter` genellikle Python standart kütüphanesiyle birlikte gelir, bu yüzden ayrı bir kurulum gerektirmeyebilir. Eğer `tkinter` bulunamadı hatası alırsanız, işletim sisteminize özel `python3-tk` (Linux için) veya benzeri bir paketi yüklemeniz gerekebilir.

## Kullanım

1.  **Uygulamayı Başlatma:**
    Proje dosyalarının bulunduğu klasörde bir terminal veya komut istemi açın ve aşağıdaki komutu çalıştırın:

    ```bash
    python autoclicker_app.py
    ```
    Bu komut, uygulamanın grafiksel arayüzünü başlatacaktır.

2.  **Ayarları Yapılandırma:**
    *   **Tıklama Modu:** Açılır menüden istediğiniz tıklama modunu seçin (Sabit, Dalgalı, Patlama, Gerçekçi).
    *   **Hız (CPS):** Kaydırıcıyı kullanarak veya doğrudan giriş yaparak saniyedeki tıklama sayısını ayarlayın.
    *   **Zamanlama Rastgeleliği:** Tıklamalar arasındaki gecikmeye eklenecek maksimum rastgele süreyi milisaniye cinsinden girin.
    *   **Jitter Yoğunluğu:** Fare imlecinin tıklama sırasında ne kadar hareket edeceğini piksel cinsinden belirleyin. 0 girerseniz jitter olmaz.
    *   **Fare Tuşu:** "Sol Tık" veya "Sağ Tık" seçeneğini belirleyin.
    *   Eğer "Patlama" modunu seçtiyseniz, "Patlama Süresi (sn)" ayarını yapın.

3.  **Tetikleyici Tuş Atama:**
    *   "Tetikleyici Tuş Ata" butonuna tıklayın. Butonun altındaki etiket "TUŞA BASIN..." olarak değişecektir.
    *   Otomatik tıklamayı başlatmak/durdurmak için kullanmak istediğiniz klavye tuşuna basın. Atadığınız tuş etikette görünecektir.
    *   Atamayı iptal etmek için `ESC` tuşuna basabilirsiniz.
    *   **ÖNEMLİ:** Bir tetikleyici tuş atamadan tıklamayı başlatamazsınız.

4.  **Tıklamayı Başlatma/Durdurma:**
    *   **GUI Butonu:** "Başlat" butonuna tıklayarak otomatik tıklamayı başlatın. Tıklama aktifken buton "Durdur" olarak değişir ve tekrar basıldığında tıklamayı durdurur.
    *   **Tetikleyici Tuş:** Ayarladığınız tetikleyici tuşa basarak tıklamayı başlatabilir veya durdurabilirsiniz. Bu, uygulama penceresi aktif olmasa bile çalışır (arka planda).

5.  **Acil Kapatma:**
    Herhangi bir sorunla karşılaşırsanız veya uygulamayı hızla kapatmanız gerekirse, klavyenizdeki **F12** tuşuna basın. Uygulama hemen sonlanacaktır.

## Notlar

*   Uygulama çalışırken fare ve klavye kontrolünü ele alabilir. Özellikle yüksek CPS ayarlarında veya tetikleyici tuş kullanırken dikkatli olun.
*   "Gerçekçi (Perlin)" modu, tıklama hızında ve fare hareketlerinde daha insan benzeri bir davranış sağlamak için tasarlanmıştır, bu da otomasyonun tespit edilmesini zorlaştırabilir.
*   Herhangi bir hata veya beklenmedik davranışla karşılaşırsanız, lütfen ayarlarınızı kontrol edin. Özellikle sayısal giriş alanlarına geçerli değerler girdiğinizden emin olun.
