---
title: Book SEO Data — Product Card
doc_id: CARD-book-seo-data
doc_type: product-card
verdict: showcase
version: 0.1
date: 2026-10-08
status: ร่างเพื่อพิจารณา
owner: Product owner (Book Dev)
---

# Book SEO Data — Product Card

## 1. สรุปคุณค่าในหนึ่งประโยค

ช่วยเจ้าของติดตามสถานะหน้าเว็บของโดเมนตัวเองและเก็บข้อมูลอันดับค้นหาที่ตรวจย้อนได้

## 2. ปัญหาและผู้ใช้เป้าหมาย

- เจ้าของมีหลายโดเมนและต้องรู้ว่าหน้าเว็บยังทำงานและติดอันดับอย่างไร
- ผู้ใช้: เจ้าของและระบบภายใน; ถูกใช้โดย `book-opportunity-intelligence` (synthesis) และ `solo-empire-insights` (หน้าเว็บ)

## 3. สิ่งที่ทำได้จริงตอนนี้

- `ingest.py` เก็บ response ต่อ keyword/query แยกตาม provider → landing → Bronze (`seo_rankings`, `seo_rankings_history`)
- cron รายวัน 08:00 ตรวจหน้าแรกของโดเมนที่เป็นเจ้าของ (README ระบุว่า cron นี้ไม่เก็บ SERP rank)
- `api.py` อ่านอย่างเดียว (port 8106); test 11 ไฟล์

## 4. หลักฐานสถานะ

- Stack: Python
- Commits: 19 (แรก 2026-08-11 → ล่าสุด 2026-10-01), branch `main`; working tree สะอาด
- Source: 23 ไฟล์ / 3,481 บรรทัด; test 11 ไฟล์
- CI: 1 workflow
- Deploy config: ไม่มี
- Live URL: ไม่พบใน repo
- โครงสร้างไฟล์เหมือนกับ repo อื่นอีก 2 ตัวในตระกูลเดียวกัน (structure signature เดียวกัน)

## 5. คุณค่าและจุดต่าง

- การตรวจหน้าแรกของโดเมนตัวเองมีประโยชน์จริงต่อเจ้าของ
- เครื่องมือ SEO (Search Console, Ahrefs) ดีกว่ามากสำหรับอันดับ; ไม่มีมุมรายได้

## 6. ช่องว่างสำคัญ

- ไม่มี deploy config หรือ public endpoint; ใช้งานผ่าน API ในเครื่องเท่านั้น (ค่าเริ่มต้น bind 127.0.0.1)
- การเก็บ SERP จาก Google HTML ขัดเงื่อนไขผู้ให้บริการ ควรใช้ Search Console API แทน **[ต้องยืนยัน]**

## 7. คำตัดสิน

**showcase** — ทำงานจริงบางส่วน (health check ของโดเมน) แต่ส่วน ranking ยังไม่ใช่แหล่งที่เชื่อถือได้ จึงเป็นงาน portfolio

จะเป็น `invest` ถ้าเปลี่ยนไปใช้ Search Console API และกลายเป็นรายงาน SEO ที่เจ้าของใช้จริงทุกสัปดาห์

## 8. ขั้นต่อไป

1. ย้ายแหล่ง ranking ไป Search Console API
2. ตัดสินใจรวม 6 repo ข้อมูลตลาด

## การอนุมัติ

| บทบาท | สถานะ | วันที่ | ลงนาม |
|---|---|---|---|
| Product owner (Book Dev) | รอพิจารณา | — | ________ |

## แหล่งข้อมูล

- `README.md`
- `src/book_seo/ingest.py`
- `src/book_seo/api.py`
- `tests/`
