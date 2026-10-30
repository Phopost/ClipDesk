<div align="center">

# 🌊 ClipDesk

> **โปรเจกต์นี้พัฒนาโดย Gemini 4 Argon, Claude 5.5 Opus, Claude 5.5 Sonnet, DeepSeek 4.1 Flash และ Gemini 3.8 Flash**

โปรแกรมขนาดเล็กสำหรับช่วยดาวน์โหลดวิดีโอ (MP4) และเสียง (MP3) จาก YouTube และ TikTok บนระบบปฏิบัติการ Windows 10 / 11 (64-bit)

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011%20x64-0078D6?style=flat-square&logo=windows)](https://github.com/Phopost/ClipDesk)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python)](https://www.python.org/)
[![UI](https://img.shields.io/badge/UI-PySide6%20%2F%20Qt6-41CD52?style=flat-square&logo=qt)](https://www.qt.io/)
[![Release](https://img.shields.io/badge/Release-v1.2.1-blue?style=flat-square)](https://github.com/Phopost/ClipDesk/releases)

</div>

---

## เกี่ยวกับโปรเจกต์

**ClipDesk** เป็นโปรแกรมเดสก์ท็อปที่จัดทำขึ้นเพื่ออำนวยความสะดวกในการบันทึกคลิปวิดีโอหรือไฟล์เสียงจาก YouTube และ TikTok มาเก็บไว้ใช้งานส่วนตัว โดยครอบการทำงานของเครื่องมือโอเพนซอร์สอย่าง `yt-dlp` และ `FFmpeg` ให้สามารถใช้งานผ่านหน้าต่างกราฟิกที่เข้าใจง่าย ไม่ต้องพิมพ์คำสั่งเอง และไม่ต้องติดตั้งโปรแกรมเสริมแยกต่างหากครับ

ตัวโปรแกรมยังเป็นโปรเจกต์เล็กๆ ที่อาจมีจุดบกพร่องหรือข้อจำกัดอยู่บ้าง หากท่านใช้งานแล้วพบปัญหา หรือมีคำแนะนำใดๆ สามารถกดปุ่ม **"รายงานปัญหา"** ในตัวโปรแกรมเพื่อส่งข้อความถึงผู้พัฒนาได้โดยตรง ทางเรายินดีน้อมรับทุกข้อเสนอแนะเพื่อนำไปปรับปรุงให้ดีขึ้นต่อไปครับ

---

## ความสามารถหลัก

- **ตรวจสอบลิงก์อัตโนมัติ:** เมื่อวางลิงก์ YouTube หรือ TikTok โปรแกรมจะดึงชื่อคลิป ภาพปก และความยาวให้อัตโนมัติ
- **เลือกรูปแบบไฟล์ได้ตามต้องการ:** รองรับการบันทึกวิดีโอ `MP4` (360p – 4K ตามต้นฉบับ) และแยกเฉพาะเสียง `MP3` (128 – 320 kbps)
- **ระบบคิวและประวัติ:** จัดคิวดาวน์โหลดได้หลายรายการพร้อมกัน สั่งยกเลิกกลางคันได้โดยไม่ทิ้งไฟล์ค้าง และมีหน้าประวัติย้อนหลัง
- **ตรวจสอบไฟล์หลังดาวน์โหลด:** ตรวจเช็กความสมบูรณ์ของไฟล์ด้วย `FFprobe` และเปลี่ยนชื่ออัตโนมัติ (`(1)`, `(2)`) เพื่อไม่ให้บันทึกทับไฟล์เดิม
- **หน้ารายงานปัญหาในตัวแอป:** แจ้งปัญหาการใช้งานหรือส่งข้อเสนอแนะได้ทันทีจากแถบเมนูด้านซ้าย

---

## ข้อจำกัดในปัจจุบัน

- รองรับเฉพาะลิงก์สาธารณะ (Public) ของ **YouTube** และ **TikTok** แบบรายการเดี่ยว (ยังไม่รองรับเพลย์ลิสต์หรือคลิปส่วนตัวที่ต้องล็อกอิน)
- รองรับเฉพาะระบบปฏิบัติการ **Windows 10 และ Windows 11 (64-bit)** เท่านั้น

---

## วิธีติดตั้งและใช้งาน

### สำหรับผู้ใช้งานทั่วไป
1. ไปที่หน้า [**Releases**](https://github.com/Phopost/ClipDesk/releases) แล้วดาวน์โหลดไฟล์ **`ClipDesk-Setup.exe`**
2. ดับเบิลคลิกไฟล์ `ClipDesk-Setup.exe` ตัวติดตั้งจะสร้างทางลัดบนหน้าจอ Desktop และเปิดโปรแกรมให้พร้อมใช้งานทันที

### สำหรับนักพัฒนา (รันจาก Source Code)
```powershell
git clone https://github.com/Phopost/ClipDesk.git
cd ClipDesk
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python tools/prepare_vendor.py
python -m app.main
```
- รันชุดทดสอบอัตโนมัติ: `pytest`
- สร้างไฟล์ติดตั้ง `.exe`: `python packaging/build_windows.py` ตามด้วย `python packaging/build_installer.py`

---

## ลิขสิทธิ์และซอฟต์แวร์โอเพนซอร์สที่ใช้ร่วม

โปรเจกต์นี้พัฒนาขึ้นเพื่อการศึกษาและการใช้งานส่วนบุคคล โดยอาศัยซอฟต์แวร์โอเพนซอร์ส ได้แก่ `yt-dlp` (Unlicense), `FFmpeg / FFprobe` (GPLv3), `QuickJS-NG` (MIT) และ `PySide6 / Qt6` (LGPLv3) สามารถดูรายละเอียดเพิ่มเติมได้ที่ [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) ครับ
