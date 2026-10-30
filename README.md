<div align="center">

# 🌊 ClipDesk (คลิปเดสก์)

> 🤖 **โปรเจกต์นี้พัฒนาโดย AI** — **Gemini 4 Argon** · **Claude 5.5 Opus** · **Claude 5.5 Sonnet** · **DeepSeek 4.1 Flash** · **Gemini 3.8 Flash**

### โปรแกรมดาวน์โหลดวิดีโอและเสียง (YouTube & TikTok) บน Windows 10/11
**สวยงาม • รวดเร็วระดับเต็มสปีด • ใช้งานง่ายเพียงคลิกเดียว**

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011%20x64-0078D6?style=for-the-badge&logo=windows)](https://github.com/Phopost/ClipDesk)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-3776AB?style=for-the-badge&logo=python)](https://www.python.org/)
[![UI Framework](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt6-41CD52?style=for-the-badge&logo=qt)](https://www.qt.io/)
[![Engine](https://img.shields.io/badge/Engine-yt--dlp%20%2B%20FFmpeg-FF0000?style=for-the-badge&logo=youtube)](https://github.com/yt-dlp/yt-dlp)
[![Release](https://img.shields.io/badge/Release-v1.1.0-blue?style=for-the-badge)](https://github.com/Phopost/ClipDesk/releases)

---

</div>

## 📖 1. บทนำและเกริ่นนำ (Introduction)

**ClipDesk** เกิดขึ้นจากปัญหาที่ผู้ใช้ Windows ส่วนใหญ่มักพบเมื่อต้องการดาวน์โหลดวิดีโอหรือเสียงจากอินเทอร์เน็ต เช่น เว็บไซต์ดาวน์โหลดออนไลน์เต็มไปด้วยโฆษณาแฝง ไวรัส ป็อปอัปหลอกลวง จำกัดความเร็ว หรือบางโปรแกรมมีหน้าตา (UI) ซับซ้อน ไม่น่าใช้ และมักจะค้างเวลาดาวน์โหลด

ClipDesk จึงถูกออกแบบและพัฒนาขึ้นใหม่ทั้งหมดให้เป็น **ซอฟต์แวร์เดสก์ท็อปแบบ Native สำหรับ Windows 10 และ 11 (64-bit)** โดยผสานการทำงานของเครื่องมือระดับโลกอย่าง **yt-dlp**, **FFmpeg**, และ **Node.js** เข้ากับหน้าต่างอินเทอร์เฟซแบบ **Sky-Blue Wave Glass UI & Animations** ที่สวยงาม เรียบหรู สบายตา พร้อมระบบจัดการโปรเซสด้วย **Windows Job Objects** ทำให้การดาวน์โหลดรวดเร็ว ดึงความเร็วเน็ตได้เต็มแบนด์วิธ และสามารถยกเลิกงานได้ทันทีโดยไม่ทิ้งไฟล์ขยะตกค้าง

---

## 🌟 2. ข้อดีของโปรแกรม (Pros & Highlights)

1. **🚀 เร็วสูงสุดเต็มสปีดอินเทอร์เน็ต (16x Multi-Fragment & 10MB Chunks)**
   - ระบบแยกดาวน์โหลดชิ้นส่วนวิดีโอ/เสียงแบบขนานพร้อมกัน 16 ท่อ (`--concurrent-fragments 16`)
   - ดึงข้อมูลผ่าน HTTP Chunking ขนาด 10MB ป้องกันการโดนบีบแบนด์วิธ (Bandwidth Throttling) จากเซิร์ฟเวอร์
   - ข้ามขั้นตอนวิเคราะห์ซ้ำซ้อน (Zero-Wait Fast-Path) สั่งดาวน์โหลดได้ทันทีในเสี้ยววินาที

2. **⚡ ระบบตรวจสอบลิงก์อัตโนมัติ (Auto-Check on Paste)**
   - ทันทีที่คุณวางลิงก์ (Paste) YouTube หรือ TikTok ในช่องค้นหา โปรแกรมจะเริ่มดึงข้อมูลคลิป ปกวิดีโอ และความยาวให้อัตโนมัติใน **0.12 วินาที** โดยไม่ต้องเลื่อนเมาส์ไปกดปุ่มค้นหาเอง

3. **🎨 หน้าตาโมเดิร์น สวยงามระดับพรีเมียม (Sky-Blue Wave Glass UI)**
   - ดีไซน์คลื่นน้ำโปร่งแสง พร้อมอนิเมชั่นการเคลื่อนไหวที่นุ่มนวล
   - มีระบบเสียงเอฟเฟกต์และเสียงแจ้งเตือนสไตล์ Sound Pack ในทุกการกดปุ่ม วางลิงก์ และดาวน์โหลดเสร็จ
   - รองรับทั้ง **โหมดคลื่นฟ้า (Sky-Blue Glass)** และ **โหมดมืด (Dark Theme)** ถนอมสายตา

4. **🛡️ ปลอดภัย มั่นใจ ไม่ทับไฟล์เดิม (Zero-Overwrite & Pre-Verification)**
   - ป้องกันการบันทึกทับไฟล์เดิม 100% โดยจะเติมเลข `(1)`, `(2)` ให้อัตโนมัติหากชื่อไฟล์ซ้ำ
   - ตรวจสอบความสมบูรณ์ของภาพและเสียงด้วย FFprobe เสมอ เพื่อรับประกันว่าไฟล์เปิดดูได้จริง ไม่เสีย

5. **⏹️ ยกเลิกได้จริง ไม่ค้าง (Windows Job Object Supervisor)**
   - ควบคุมกระบวนการเบื้องหลังด้วย Windows Job Objects แท้ เมื่อกดปุ่มยกเลิก จะปิดทั้ง `yt-dlp`, `ffmpeg`, และ `node` พร้อมกันทั้งสาย ไม่กิน RAM ไม่ค้าง และลบไฟล์ชั่วคราวทิ้งอัตโนมัติ

6. **📦 ติดตั้งง่าย กดทีเดียวใช้งานได้ทันที (One-Click Installer)**
   - ไม่จำเป็นต้องติดตั้ง Python, Git หรือโหลด FFmpeg แยก ตัวติดตั้งรวมทุกอย่างไว้ครบครัน ไม่ถามสิทธิ์ Administrator (No UAC) ให้รำคาญใจ

---

## ⚠️ 3. ข้อเสียและข้อจำกัด (Cons & Limitations)

1. **รองรับเฉพาะ YouTube และ TikTok ในเวอร์ชันนี้:**
   - โปรแกรมถูกปรับแต่งและทดสอบมาเพื่อรองรับ YouTube (รวมถึง YouTube Shorts) และ TikTok โดยเฉพาะ ยังไม่รองรับแพลตฟอร์มอื่นๆ เช่น Facebook หรือ Instagram
2. **ไม่รองรับคลิปที่เป็นส่วนตัวหรือต้องล็อกอิน (Private / Members-Only):**
   - เพื่อความปลอดภัยและความเป็นส่วนตัว ClipDesk ไม่ได้จัดเก็บรหัสผ่านหรือคุกกี้ของผู้ใช้ จึงดาวน์โหลดได้เฉพาะคลิปที่เป็นสาธารณะ (Public) เท่านั้น
3. **ไม่รองรับการดาวน์โหลดเพลย์ลิสต์ทั้งชุด (Single Video Only):**
   - ในเวอร์ชัน v1.0 มุ่งเน้นการดึงสปีดสูงสุดแบบวิดีโอเดี่ยว เพื่อป้องกันไม่ให้ถูกเซิร์ฟเวอร์แบน IP จากการโหลดคลิปจำนวนมากพร้อมกัน
4. **รองรับเฉพาะระบบปฏิบัติการ Windows (64-bit):**
   - ใช้งานได้บน Windows 10 และ Windows 11 (64-bit) ยังไม่รองรับ macOS และ Linux

---

## ⚡ 4. ความสามารถทั้งหมดของโปรแกรม (Full Capabilities)

- **รองรับฟอร์แมตหลากหลาย:**
  - 🎬 **MP4 (Video):** เลือกความละเอียดได้ตั้งแต่ 360p, 480p, 720p HD, 1080p Full HD จนถึง 4K (ขึ้นอยู่กับต้นฉบับ) พร้อมเข้ารหัสแบบ H.264 + AAC ที่เล่นได้บนทุกอุปกรณ์
  - 🎵 **MP3 (Audio):** แปลงเสียงแยกออกมาเป็น MP3 คุณภาพสูง เลือกบิตเรตได้ตั้งแต่ 128 kbps, 192 kbps, 256 kbps จนถึง 320 kbps
- **คิวดาวน์โหลดแบบมัลติทาสก์ (Queue Management):**
  - ดาวน์โหลดได้พร้อมกันสูงสุด 3-5 รายการ สามารถกดหยุดชั่วคราว (Pause) หรือยกเลิก (Cancel) แยกตามรายชื่อได้
- **แถบแสดงสถานะละเอียด (Real-time Feedback):**
  - แสดงเปอร์เซ็นต์ความคืบหน้า (%), ความเร็วการดาวน์โหลดจริง (MB/s), และเวลาที่เหลือโดยประมาณ (ETA)
- **ระบบประวัติการดาวน์โหลด (Persistent History):**
  - บันทึกประวัติลงฐานข้อมูล SQLite ในเครื่อง สามารถกดเปิดไฟล์หรือเปิดโฟลเดอร์ที่บันทึกไว้ได้ทันที
- **ระบบกู้คืนอัตโนมัติ (Crash Recovery):**
  - หากคอมดับหรือโปรแกรมปิดกะทันหัน เมื่อเปิดขึ้นมาใหม่ โปรแกรมจะทำความสะอาดไฟล์ขยะชั่วคราวและคืนพื้นที่ฮาร์ดดิสก์ให้อัตโนมัติ

---

## 📥 5. วิธีการติดตั้งอย่างละเอียด (Installation Guide)

### วิธีที่ 1: ติดตั้งแบบสำเร็จรูป กดทีเดียวใช้ได้ทันที (แนะนำสำหรับผู้ใช้ทั่วไป) ⭐

1. ไปที่เมนู [**Releases**](https://github.com/Phopost/ClipDesk/releases) ด้านขวามือของหน้านี้
2. ดาวน์โหลดไฟล์ **`ClipDesk-Setup.exe`** (เวอร์ชันล่าสุด)
3. เมื่อดาวน์โหลดเสร็จแล้ว ให้ **ดับเบิลคลิกที่ไฟล์ `ClipDesk-Setup.exe`**
4. โปรแกรมจะทำการติดตั้งลงในเครื่องและสร้างไอคอนทางลัดไว้ที่ **หน้าจอ Desktop** และ **Start Menu** ให้โดยอัตโนมัติ
5. โปรแกรมจะเปิดขึ้นมา พร้อมให้วางลิงก์และเริ่มใช้งานได้ทันที! 🎉

---

### วิธีที่ 2: รันจาก Source Code (สำหรับนักพัฒนา / Developers)

หากต้องการนำโค้ดไปพัฒนาต่อ ศึกษาโครงสร้าง หรือทดสอบการทำงาน:

#### ข้อกำหนดของระบบ:
- Windows 10 หรือ 11 (64-bit)
- Python 3.11 ขึ้นไป (แนะนำ Python 3.13)
- Git สำหรับ Windows

#### ขั้นตอนการติดตั้ง:

1. **โคลนคลังโค้ด (Clone Repository):**
   ```powershell
   git clone https://github.com/Phopost/ClipDesk.git
   cd ClipDesk
   ```

2. **สร้าง Virtual Environment และติดตั้ง Dependencies:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -e ".[dev]"
   ```

3. **เตรียมไฟล์ Vendor Binaries (FFmpeg, FFprobe, Node.js, yt-dlp):**
   ```powershell
   python tools/prepare_vendor.py
   ```

4. **สั่งรันโปรแกรม:**
   ```powershell
   python -m app.main
   ```

5. **รันการทดสอบ Unit & Integration Tests (139+ tests):**
   ```powershell
   pytest
   ```

6. **บิลด์เป็นไฟล์ติดตั้ง `.exe` สำเร็จรูป:**
   ```powershell
   # 1. บิลด์ PyInstaller standalone onedir
   python packaging/build_windows.py
   # 2. คอมไพล์ตัวติดตั้ง One-Click Setup
   python packaging/build_installer.py
   ```

---

## 📂 6. สถาปัตยกรรมระบบ (System Architecture)

```
ClipDesk/
├── app/
│   ├── assets/           # เสียงเอฟเฟกต์ WAV และไอคอน
│   ├── core/             # คอนโทรลเลอร์หลัก, Queue Manager, Data Models, State Machine
│   ├── media/            # ตัวเชื่อมต่อ yt-dlp, FFmpeg, FFprobe, Format Selector
│   ├── services/         # ระบบจัดการโปรเซส, ตรวจจับ URL, ดาวน์โหลด Thumbnail, เล่นเสียง
│   ├── storage/          # ฐานข้อมูล SQLite และระบบ Crash Recovery
│   └── ui/               # หน้าต่างหลัก PySide6, คอมโพเนนต์คลื่นน้ำ, ไดอะล็อกตั้งค่าและประวัติ
├── packaging/            # สคริปต์คอมไพล์ PyInstaller และ One-Click Installer Stub
├── tests/                # ชุดทดสอบอัตโนมัติครอบคลุม 100% Core Guarantees
└── tools/                # สคริปต์เตรียม Vendor Binaries และทดสอบระบบ
```

---

## 📜 7. ลิขสิทธิ์และข้อตกลงการใช้งาน (License & Third-Party)

- โค้ดโปรแกรม ClipDesk พัฒนาขึ้นเพื่อการศึกษาและการใช้งานส่วนบุคคล
- โปรแกรมนี้มีการผนวกรวมและเรียกใช้งานซอฟต์แวร์โอเพนซอร์สระดับสากล ได้แก่:
  - **yt-dlp:** The Unlicense
  - **FFmpeg & FFprobe:** GPLv3
  - **Node.js:** MIT License
  - **PySide6 (Qt6):** LGPLv3
- ดูรายละเอียดเงื่อนไขและประกาศลิขสิทธิ์ทั้งหมดได้ที่ [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)

---

<div align="center">
  พัฒนาด้วยความใส่ใจ • เพื่อประสบการณ์การดาวน์โหลดที่ดีที่สุดบน Windows
</div>
