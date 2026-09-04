Bu klasöre ffmpeg.exe ve ffprobe.exe dosyalarını koyun.

Nereden indireceğiniz:
  https://www.gyan.dev/ffmpeg/builds/  ->  "ffmpeg-release-essentials.zip"
  (veya https://github.com/BtbN/FFmpeg-Builds/releases)

Adımlar:
  1. Zip'i indirip açın.
  2. Zip içindeki bin/ klasöründen ffmpeg.exe ve ffprobe.exe dosyalarını
     kopyalayıp BU klasöre (ffmpeg/) yapıştırın.

Sonuç şöyle görünmeli:
  ffmpeg/ffmpeg.exe
  ffmpeg/ffprobe.exe

Not: Bu iki .exe dosyası .gitignore ile git'e dahil edilmez (boyutları büyük).
Derleme (PyInstaller) sırasında spec dosyası bunları uygulamanın içine gömer,
böylece son kullanıcının ffmpeg kurmasına gerek kalmaz.
