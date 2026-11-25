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

## 🔒 Xavfsizlik & Arxitektura

1. **PostgreSQL Row-Level Security (RLS):** `school_id` ga ega barcha tenant jadvallarda `ENABLE`/`FORCE ROW LEVEL SECURITY` yoqilgan; ilova `maktab_app` (`NOBYPASSRLS`) roli bilan ishlaydi va `after_begin` event listener har bir tranzaksiyada `app.current_school_id` ni o'rnatadi.
2. **HttpOnly Cookie + Refresh Token Rotatsiyasi:** `refresh_token` `jti` bilan bazada saqlanadi, `HttpOnly; SameSite=Lax` cookie sifatida beriladi va reuse detection bilan rotatsiya qilinadi; `access_token` (15 daqiqa) frontendda faqat xotirada saqlanadi.
3. **Rate Limiting & Parol Siyosati:** SlowAPI orqali `/auth/login` ga 5 urinish/daqiqa cheklovi, UTF-8 da 8..72 bayt oralig'ida parol tekshiruvi va timing-attack himoyasi.
4. **Asinxron Jadval Generatsiyasi:** `POST /api/v1/timetable/generate` `202 Accepted` qaytaradi; OR-Tools CP-SAT yechuvchi alohida jarayonda (`ProcessPoolExecutor` / `worker`) ishlaydi.

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

### Backend va Frontend Testlar:
```bash
# Backend (pytest)
cd backend
pip install -r requirements-dev.txt
pytest -v

# Frontend (Vitest)
npm test
```

---

## 🐳 Docker Orqali Ishga Tushirish

1. `.env.example` dan `.env` faylini yarating va barcha majburiy o'zgaruvchilarni (`POSTGRES_PASSWORD`, `SECRET_KEY`, `DATABASE_URL`, `ALEMBIC_DATABASE_URL`, `DEFAULT_ADMIN_EMAIL`, `DEFAULT_ADMIN_PASSWORD`) to'ldiring:
   ```bash
   cp .env.example .env
   ```
2. Barcha xizmatlarni (`postgres`, `backend`, `worker`, `frontend`) ishga tushiring:
   ```bash
   docker compose up --build -d
   ```

---

## 💻 Mahalliy Dasturlash Rejimida Ishga Tushirish

### 1. Backend & Worker:
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
python init_db.py
uvicorn main:app --reload --port 8000
# Alohida worker (agar PROCESS_JOBS_EXTERNALLY=true bo'lsa):
python -m services.worker
```

### 2. Frontend:
```bash
npm install
npm run dev
```
Brauzerda oching: `http://localhost:3000`  
Boshlang'ich admin foydalanuvchini yaratish uchun `backend/.env` faylida `DEFAULT_ADMIN_EMAIL` va `DEFAULT_ADMIN_PASSWORD` o'zgaruvchilarini sozlab, `python init_db.py` buyrug'ini ishga tushiring.
