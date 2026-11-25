# 🏫 Maktab SMS — Multi-tenant Maktab Boshqaruv Tizimi & CSP Dars Jadvali Generatori

**Maktab SMS** — bu ko'p maktabli (multi-tenant) SaaS platformasi bo'lib, umumta'lim maktablarining o'qituvchilari, sinflari, xonalari, o'quv rejalari va choraklik fan yuklamalarini markazlashtirilgan tarzda boshqarish hamda **CSP (Constraint Satisfaction Problem) Backtracking** algoritmi yordamida to'liq ziddiyatsiz dars jadvallarini avtomatik generatsiya qilish uchun mo'ljallangan.

---

## 🚀 Texnologik Stek

- **Frontend:** Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Lucide Icons, TanStack Query, React Hook Form + Zod, jsPDF & html2canvas.
- **Backend:** Python 3.11+ / FastAPI, SQLAlchemy 2.0 (Async), Pydantic v2, SlowAPI (Rate Limiting), PyJWT & Bcrypt.
- **Ma'lumotlar Bazasi:** PostgreSQL (Neon Cloud / Docker) — Row-Level Security (RLS) orqali maktablararo to'liq ma'lumotlar izolyatsiyasi.
- **Migratsiya Tizimi:** Alembic (Asyncpg drayveri bilan).
- **Algoritm:** CSP Backtracking Solver — Smena normalizatsiyasi, o'qituvchi kunlik/haftalik soat cheklovlari, xonalar mosligi, timeout, random restart va progress callback.
- **Konteynerlashtirish:** Multi-stage Dockerfile va Docker Compose.

---

## 🔒 Xavfsizlik & Arxitektura Yaxshilanishlari

1. **SQL Injection Himoyasi:** `get_tenant_db` sessiyasida `SELECT set_config('app.current_school_id', :sid, true)` orqali xavfsiz parametrlangan so'rov joriy etildi.
2. **Haqiqiy Ma'murlar Bazasida Saqlanadi:** Hardcoded `admin123` demo fallbacklari olib tashlandi. `init_db.py` orqali xavfsiz bcrypt-xeshli admin yaratiladi.
3. **Frontend Autentifikatsiya:**
   - Yangi to'liq `/login` sahifasi (React Hook Form + Zod validatsiyasi).
   - `ProtectedRoute` yo'l himoyachisi.
   - 7 kunlik **Refresh Token** va avtomatik interceptor yangilanishi.
4. **Rate Limiting:** SlowAPI orqali `/auth/login` ga 5 ta urinish/daqiqa, boshqa endpointlarga 100 ta so'rov/daqiqa limiti qo'yildi.
5. **Parol Siyosati:** Kamida 8 belgi, 1 ta katta harf va 1 ta raqam majburiy.
6. **SECRET_KEY:** Majburiy `.env` tekshiruvi.

---

## 📁 Loyiha Strukturasi

```text
maktab/
├── backend/
│   ├── alembic/                  # Alembic async migratsiyalari
│   │   ├── versions/             # Migratsiya fayllari
│   │   └── env.py                # Asyncpg orqali ishlovchi env sozlamasi
│   ├── core/
│   │   ├── config.py             # Pydantic Settings & DB URL validator
│   │   ├── limiter.py            # SlowAPI rate limiter
│   │   ├── logging.py            # Structured logging tizimi
│   │   ├── rbac.py               # Rollarga asoslangan kirish huquqi (RBAC)
│   │   └── security.py           # Bcrypt & JWT Access/Refresh tokenlar
│   ├── database/
│   │   ├── connection.py         # Async engine, sessionmaker, RLS get_tenant_db
│   │   └── models.py             # Barcha SQLAlchemy jadvallari, indekslar, modellar
│   ├── routers/                  # REST API Routerlar
│   │   ├── auth.py               # Login, refresh token, profil
│   │   ├── classes.py            # Sinflar CRUD, qidiruv va filtrlar
│   │   ├── curriculum.py         # O'quv rejasi va choraklik yuklama
│   │   ├── rooms.py              # Xonalar CRUD
│   │   ├── subjects.py           # Fanlar katalogi
│   │   ├── teachers.py           # O'qituvchilar CRUD va sahifalash
│   │   └── timetable.py          # Jadval generatsiyasi va olish
│   ├── schemas/                  # Pydantic so'rov/javob sxemalari
│   ├── services/
│   │   ├── generator.py          # CSP Backtracking dars jadvali generatori
│   │   └── timetable_service.py  # Bazadan yuklash va saqlash xizmati
│   ├── tests/                    # Pytest testlar to'plami
│   ├── utils/
│   │   └── crud_factory.py       # Standartlashtirilgan response va pagination
│   ├── Dockerfile                # Multi-stage Python runner
│   ├── init_db.py                # Baza va admin foydalanuvchini initsializatsiya qilish
│   └── main.py                   # FastAPI kirish nuqtasi
├── src/
│   ├── app/                      # Next.js 14 App Router
│   │   ├── login/page.tsx        # Tizimga kirish sahifasi
│   │   ├── dashboard/
│   │   │   ├── layout.tsx        # Sidebar + Header umumiy layout
│   │   │   ├── page.tsx          # Boshqaruv markazi overview
│   │   │   ├── teachers/page.tsx # O'qituvchilar sahifasi
│   │   │   ├── classes/page.tsx  # Sinflar sahifasi
│   │   │   ├── rooms/page.tsx    # Xonalar sahifasi
│   │   │   ├── subjects/page.tsx # Fanlar sahifasi
│   │   │   ├── curriculum/page.tsx # O'quv rejasi sahifasi
│   │   │   ├── timetable/page.tsx  # Dars jadvali sahifasi
│   │   │   └── settings/page.tsx   # Sozlamalar sahifasi
│   │   ├── layout.tsx            # Root layout & provayderlar
│   │   └── providers.tsx         # TanStack Query, Auth, SchoolData, Toast
│   ├── components/               # Modullar va UI komponentlar
│   │   ├── common/               # ErrorBoundary, Skeleton, Toast
│   │   ├── layout/               # Responsive Sidebar, Header (Global Search)
│   │   └── timetable/            # TimetableGrid (PDF va Excel eksport)
│   ├── context/                  # AuthContext, SchoolDataContext, ToastContext
│   ├── lib/
│   │   └── api.ts                # Avtomatik refresh bilan API klient
│   └── types/
│       └── index.ts              # TypeScript interfeyslari
├── docker-compose.yml            # Frontend, Backend va Postgres kompozitsiyasi
├── Dockerfile                    # Next.js standalone multi-stage build
└── README.md
```

---

## 🗄️ Alembic Migratsiyalar Qo'llanmasi

Ma'lumotlar bazasi sxemasining yagona manbai **Alembic** hisoblanadi (`backend/database/models.py` asosida).

1. **Toza bazani initsializatsiya qilish:**
   ```bash
   cd backend
   alembic upgrade head
   python init_db.py
   ```

2. **Modellardagi o'zgarishlardan yangi migratsiya yaratish:**
   ```bash
   cd backend
   alembic revision --autogenerate -m "yangi_ozgarishlar_nomi"
   ```

3. **Oxirgi migratsiyani bekor qilish (Rollback):**
   ```bash
   cd backend
   alembic downgrade -1
   # Yoki barcha jadvallarni tozalash:
   alembic downgrade base
   ```

---

## 🧠 CSP Backtracking Algoritmi Xususiyatlari

- **Smena Standartlashtirish:** `1-smena`, `2-smena`, `MORNING`, `AFTERNOON` avtomatik normalashtiriladi.
- **O'qituvchi Ish Yuklamasi Nazorati:** Har bir o'qituvchining kunlik (`max_daily_hours`) va haftalik (`max_weekly_hours`) limitlari tekshiriladi.
- **Ziddiyatsizlik Kafolati (Hard Constraints):**
  - Bir vaqtda bitta sinf faqat 1 ta fanga kiradi.
  - O'qituvchi ayni vaqtda 2 xil sinfda dars o'ta olmaydi.
  - Xona bir vaqtda 2 ta darsga berilmaydi.
  - Laboratoriya va sport zallariga moslik qat'iy tekshiriladi.
- **Yumshoq Cheklovlar (Soft Constraints):** O'qituvchi jadvalidagi "oynalar" (bo'sh soatlar) jarimalar orqali minimallashtiriladi.
- **Tezlik va Xavfsizlik:** `timeout_seconds` va `max_candidates` cheklovlari bilan qat'iy ziddiyatsiz qidiruv (to'qnashuvli joylashtirishga yo'l qo'yilmaydi).

---

## 🧪 Testlarni Ishga Tushirish

### Backend Testlar (Pytest):
```bash
cd backend
pytest -v
```
Testlar quyidagilarni o'z ichiga oladi:
- `test_auth.py` — Parol siyosati, login, 7-kunlik refresh token, va profil tekshiruvi.
- `test_teachers.py` — O'qituvchilar CRUD operatsiyalari, sahifalash, qidiruv va 404 tekshiruvi.
- `test_timetable.py` — Jadvalni olish va CSP generator API integratsiyasi.
- `test_generator.py` — CSP algoritm qat'iy va yumshoq cheklovlari, smena va xona normalizatsiyasi.

---

## 🐳 Docker Orqali Ishga Tushirish

Tizimni (Frontend, Backend va PostgreSQL) bitta buyruq bilan konteynerlarda ko'tarish:

```bash
docker-compose up --build -d
```

- **Frontend:** `http://localhost:3000`
- **Backend API:** `http://localhost:8000`
- **Swagger Docs:** `http://localhost:8000/docs`

---

## 💻 Mahalliy Dasturlash Rejimida Ishga Tushirish

### 1. Backend:
```bash
cd backend
pip install -r requirements.txt
python init_db.py  # Bazani va boshlang'ich adminni sozlash
uvicorn main:app --reload --port 8000
```

### 2. Frontend:
```bash
npm install
npm run dev
```
Brauzerda oching: `http://localhost:3000`  
Boshlang'ich admin foydalanuvchini yaratish uchun `backend/.env` faylida `DEFAULT_ADMIN_EMAIL` va `DEFAULT_ADMIN_PASSWORD` o'zgaruvchilarini sozlab, `python init_db.py` buyrug'ini ishga tushiring.
