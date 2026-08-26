# Nozanin — Telegram Mini App do'koni

Ayollar kiyim-kechak va parfyumeriya sotiladigan, Telegram bot ichida ishlaydigan to'liq loyiha:
kategoriya → o'lcham/hajm/rang tanlash → savat → buyurtma (yetkazish sanasi bilan) → sotuvchi paneli
(mahsulot/zaxira/narx boshqaruvi, buyurtmalar, kunlik statistika avtomatik Telegramga yuboriladi).

Bu kod **sinovdan o'tkazilgan va ishlaydi** (backend API to'liq test qilindi: autentifikatsiya,
mahsulot CRUD, buyurtma yaratish, zaxira kamayishi, holat o'zgarishi, statistika — barchasi ishlayapti).

---

## 1. Loyiha tarkibi

```
nozanin-shop/
├── backend/
│   ├── app/           — FastAPI backend (mahsulot, buyurtma, statistika API)
│   ├── bot/            — Telegram bot (aiogram) — /start komandasi
│   ├── requirements.txt
│   └── .env.example    — bu faylni .env qilib nusxalab, o'z ma'lumotlaringizni kiriting
├── frontend/
│   └── index.html      — Mini App (bitta HTML fayl, build kerak emas)
├── docker-compose.yml
└── nginx/nozanin.conf  — namuna Nginx konfiguratsiyasi (HTTPS)
```

---

## 2. Talab qilinadigan narsalar (siz tayyorlashingiz kerak)

1. **Telegram bot** — [@BotFather](https://t.me/BotFather) orqali yangi bot yarating, tokenni oling.
2. **HTTPS domen** — Telegram Mini App faqat `https://` orqali ishlaydi. Arzon variant:
   - VPS (Timeweb, Beget, Contabo, Hetzner va h.k.) + domen + Let's Encrypt sertifikat, **yoki**
   - Railway / Render kabi tayyor hosting (bepul/arzon tarif ham yetadi).
3. **Server** — backend (Python) va bot doim ishlab turishi kerak (24/7).

---

## 3. Lokal ishga tushirish (test uchun)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# .env faylni oching va BOT_TOKEN, ADMIN_TELEGRAM_IDS ni to'ldiring

# 1-terminal: backend API
uvicorn app.main:app --reload --port 8000

# 2-terminal: Telegram bot
python -m bot.bot
```

Frontend (`frontend/index.html`) ichidagi `API_BASE` o'zgaruvchisini backend manzilingizga moslang:
```js
const API_BASE = "https://your-backend-domain.com";
```
Keyin `frontend/` papkasini istalgan statik hostingga (yoki Nginx orqali) joylang.

---

## 4. Docker orqali ishga tushirish

```bash
cd backend && cp .env.example .env   # va to'ldiring
cd ..
docker compose up -d --build
```
Bu backend API (`:8000`), bot va frontend (`:8080`) ni birga ishga tushiradi.
Productionda `docker-compose.yml` dagi portlarni Nginx orqali HTTPS bilan oching (`nginx/nozanin.conf` namuna sifatida berilgan).

## 4.1 PythonAnywhere'ga joylash

PythonAnywhere'da **Web app** oching va Python 3.11 virtual environment yarating:

```bash
cd ~
git clone <repository-url> nozanin-shop
cd nozanin-shop/backend
python3.11 -m venv ~/.virtualenvs/nozanin
source ~/.virtualenvs/nozanin/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
nano .env
```

`.env` ichida `BOT_TOKEN`, `ADMIN_TELEGRAM_IDS`, `WEBAPP_URL` va `WEBHOOK_SECRET`ni to'ldiring.
Web app sozlamasidagi **WSGI configuration file** ichiga `backend/wsgi.py` mazmunini qo'ying.
Virtualenv sifatida `/home/USERNAME/.virtualenvs/nozanin`ni tanlang.

Agar logda `ModuleNotFoundError: No module named 'a2wsgi'` chiqsa, Web App'da tanlangan
virtualenv'ni Bash Console'da faollashtirib dependency'larni qayta o'rnating:

```bash
source ~/.virtualenvs/nozanin/bin/activate
cd ~/nozanin-shop/backend
python -m pip install -r requirements.txt
python -c "import a2wsgi; print('a2wsgi OK')"
```

Telegram webhook'ini PythonAnywhere Console'dan o'rnating:

```bash
source ~/.virtualenvs/nozanin/bin/activate
cd ~/nozanin-shop/backend
python -m bot.set_webhook https://USERNAME.pythonanywhere.com/telegram/webhook
```

Frontend'ni HTTPS static hostingga joylab, `frontend/index.html` ichidagi `API_BASE`ni
`https://USERNAME.pythonanywhere.com` manziliga o'zgartiring. BotFather'dagi Menu Button URL sifatida
frontend HTTPS manzilini kiriting. Web app'ni Reload qilgandan so'ng botga `/start` yuborib tekshiring.

## 4.2 Hugging Face Spaces'ga joylash

Repository root'ida Hugging Face uchun tayyor `Dockerfile` bor. Hugging Face'da yangi **Docker Space**
oching va repository'ni ulang yoki kodni push qiling. Space sozlamalaridagi **Settings → Variables and secrets**
bo'limiga quyidagi qiymatlarni kiriting:

```text
BOT_TOKEN=BotFather tokeni
DATABASE_URL=sqlite:///./nozanin.db
WEBAPP_URL=https://USERNAME-SPACE.hf.space
ADMIN_TELEGRAM_IDS=5019578020
PRODUCT_CHAT_IDS=
DAILY_REPORT_HOUR=21
DAILY_REPORT_MINUTE=0
TIMEZONE=Asia/Tashkent
CORS_ORIGINS=https://USERNAME-SPACE.hf.space
WEBHOOK_SECRET=uzun-tasodifiy-maxfiy-kalit
```

Space ishga tushgach, webhook'ni lokal terminaldan yoki Hugging Face Space terminalidan o'rnating:

```bash
python -m bot.set_webhook https://USERNAME-SPACE.hf.space/telegram/webhook
```

Bu buyruq ishlashi uchun `BOT_TOKEN` va `WEBHOOK_SECRET` muhit o'zgaruvchilari mavjud bo'lishi kerak.
Keyin BotFather → **Bot Settings → Menu Button** bo'limida URL sifatida
`https://USERNAME-SPACE.hf.space` manzilini kiriting. Tekshirish uchun
`https://USERNAME-SPACE.hf.space/api/health` manzili `{"status":"ok"}` qaytarishi kerak.

Hugging Face bepul Space'ni uzoq vaqt ishlatilmaganda uxlatishi mumkin. Doimiy Telegram bot uchun
Space'ni hardware sozlamasida sleep'ni o'chirish yoki pullik/Always-on rejimdan foydalanish kerak.

---

## 5. Botni Mini App bilan bog'lash

1. [@BotFather](https://t.me/BotFather) da botingizni tanlang → **Bot Settings → Menu Button** →
   URL sifatida frontend domeningizni kiriting (masalan `https://shop.your-domain.com`).
2. Shu bilan bot menyusidagi tugma orqali ham Mini App ochiladi (bot.py dagi `/start` tugmasi bilan bir xil ishlaydi).

### Render Blueprint orqali deploy

Repository rootidagi `render.yaml` bitta Docker web service yaratadi. Bu service frontendni `/` orqali,
API'ni `/api/*` orqali va Telegram webhook'ni `/telegram/webhook` orqali beradi. Render'da quyidagi secret/env
qiymatlarni kiriting:

```text
BOT_TOKEN=BotFather tokeni
WEBAPP_URL=https://nozanin-web.onrender.com
CORS_ORIGINS=https://nozanin-web.onrender.com
ADMIN_TELEGRAM_IDS=5019578020
PRODUCT_CHAT_IDS=5019578020
```

`WEBAPP_URL` va `CORS_ORIGINS` qiymatlarida Render dashboard ko'rsatgan haqiqiy service URL ishlatiladi.
Deploy tugagach, webhook'ni bir marta o'rnating:

```bash
cd backend
python -m bot.set_webhook https://nozanin-web.onrender.com/telegram/webhook
```

Webhook secret Render'dagi `WEBHOOK_SECRET` bilan bir xil bo'lishi kerak. Tekshiruv:
`https://nozanin-web.onrender.com/api/health` manzili `{"status":"ok"}` qaytaradi.

---

## 6. Sotuvchi/admin qilib belgilash

`.env` faylida:
```
ADMIN_TELEGRAM_IDS=111111111,222222222
```
Bu yerga sotuvchi(lar)ning Telegram foydalanuvchi ID sini yozing (raqamli ID, username emas).
ID ni bilish uchun [@userinfobot](https://t.me/userinfobot) ga yozish kifoya.
Server birinchi marta ishga tushganda bu ID lar avtomatik `admins` jadvaliga qo'shiladi.
Admin sifatida botni ochganingizda Mini App yuqorisida **"🔑 Sotuvchi"** tugmasi avtomatik ko'rinadi
(PIN kod kerak emas — Telegram orqali kim ekanligingiz avtomatik tasdiqlanadi).

---

## 7. Kunlik statistika

Har kuni `.env` dagi `DAILY_REPORT_HOUR:DAILY_REPORT_MINUTE` da (standart 21:00, `Asia/Tashkent`)
barcha adminlarga quyidagi ko'rinishdagi xabar avtomatik yuboriladi:

```
📊 Kunlik hisobot — 2026-08-23

Buyurtmalar soni: 5 ta
Umumiy tushum: 1 245 000 so'm
Sotilgan mahsulotlar: 9 dona

Top mahsulotlar:
1. Ipak ko'ylak — 4 dona
2. Nozanin Rose parfyumi — 3 dona
3. Kashemir sviter — 2 dona
```

Admin panelning **Statistika** bo'limida "📨 Hozir Telegramga yuborish" tugmasi orqali istalgan vaqtda
qo'lda ham yuborish mumkin.

---

## 8. Ma'lumotlar bazasi

Standart holatda **SQLite** (`nozanin.db`) ishlatiladi — qo'shimcha sozlash kerak emas.
Ko'proq yuklama kutilsa, `.env` dagi `DATABASE_URL` ni Postgresga o'zgartiring:
```
DATABASE_URL=postgresql://user:password@localhost:5432/nozanin
```
va `docker-compose.yml` ga `postgres` servisini qo'shing (rasmiy `postgres:16` image yetarli).

---

## 9. Xavfsizlik

- Har bir so'rov Telegram `initData` bilan tekshiriladi (HMAC-SHA256, bot tokeni orqali) — `app/telegram_verify.py`.
- Admin amallari faqat `admins` jadvalidagi Telegram ID lar uchun ochiq.
- `.env` fayl hech qachon repository'ga (git) qo'shilmasin — `.gitignore` da allaqachon istisno qilingan.

---

## 10. Keyingi qadamlar / kengaytirish mumkin bo'lgan joylar

- To'lov tizimi (Click/Payme) integratsiyasi
- Mahsulot rasmlarini serverga yuklash (hozircha URL orqali kiritiladi)
- Xaridor uchun "Buyurtmalarim" bo'limi (backend endpoint `GET /api/orders/my` allaqachon tayyor,
  frontendga shu bo'limni qo'shish kifoya)
- Bir nechta til (o'zbek/rus/ingliz)
