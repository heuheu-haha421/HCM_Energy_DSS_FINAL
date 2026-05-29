# HCM Energy DSS

Decision Support System for Ho Chi Minh City electricity demand forecasting, ward-level allocation, and grid stress prioritization.

The project has two main parts:

- `backend/`: FastAPI, SQLite, XGBoost prediction, allocation, scenarios, auth, WebSocket live prediction.
- `frontend/`: React + Vite dashboard.

## 1. Requirements

- macOS terminal
- Python 3.12 recommended
- Node.js 18+ recommended
- npm

Check versions:

```bash
python3 --version
node --version
npm --version
```

## 2. Project Structure

```text
HCM_Energy_DSS/
├── backend/
│   ├── app/
│   ├── config/.env
│   ├── app/config/.env
│   ├── energy_dss.db
│   ├── init_db.py
│   ├── main.py
│   └── model/
├── frontend/
│   ├── public/
│   ├── src/
│   ├── .env
│   ├── package.json
│   └── vite.config.ts
├── data_use_to_demo/
│   ├── hcm_new_168_units.csv
│   ├── total_load_2025.csv
│   ├── total_load_2026.csv
│   └── holiday.csv
└── debug_dynamic_ward_allocation.py
```

## 3. Backend Setup

The backend currently reads environment values from:

```text
backend/app/config/.env
```

The file should contain at least:

```env
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
IS_DEMO_MODE=true
SLEEP_SECONDS=5
ENABLE_DEV_DELETE=false
```

If `JWT_SECRET_KEY` is missing, generate one:

```bash
cd backend
python3 dev_generate_jwt_secret.py
```

### Option A: Use Existing Virtual Environment

If `backend/venv` already exists:

```bash
cd backend
source venv/bin/activate
python main.py
```

Backend runs at:

```text
http://localhost:8000
```

### Option B: Create a Fresh Virtual Environment

If the virtual environment is missing or broken:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn pandas numpy xgboost scikit-learn meteostat requests bcrypt PyJWT python-multipart websockets
python main.py
```

The SQLite database is initialized automatically at startup:

```text
backend/energy_dss.db
```

Seed accounts are created automatically:

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Dev | `dev` | `dev123` |

You can register normal `user` accounts from the app. Public registration should only create `user` role accounts.

## 4. Frontend Setup

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at:

```text
http://localhost:3000
```

`frontend/.env` should stay proxy-based for local development:

```env
VITE_API_URL=
VITE_WS_URL=
```

Vite proxies API and WebSocket calls to backend:

```text
/api -> http://localhost:8000
/ws  -> ws://localhost:8000
```

This avoids local CORS problems.

## 5. Run The Full Project

Use two terminals.

Terminal 1, backend:

```bash
cd backend
source venv/bin/activate
python main.py
```

Terminal 2, frontend:

```bash
cd frontend
npm run dev
```

Then open:

```text
http://localhost:3000
```

Login as:

```text
dev / dev123
```

or:

```text
admin / admin123
```

## 6. Demo Data Upload Flow

Use an admin/dev account.

Go to **Data Management** and upload:

| File | Upload Purpose | Backend Endpoint |
|---|---|---|
| `data_use_to_demo/hcm_new_168_units.csv` | Ward infrastructure / ward stats | `POST /api/v1/data/upload-ward-stats` |
| `data_use_to_demo/total_load_2025.csv` | Weekly energy load 2025 | `POST /api/v1/data/upload-energy` |
| `data_use_to_demo/total_load_2026.csv` | Weekly energy load 2026 | `POST /api/v1/data/upload-energy` |
| `data_use_to_demo/holiday.csv` | Holiday calendar | `POST /api/v1/data/upload-holiday` |

Weather CSV upload is not part of the current main flow. The backend fetches weather during prediction.

## 7. Model Demo Flow

Go to **AI Monitor**.

The project expects XGBoost JSON models, not `.pkl`.

Available demo model files:

```text
data_use_to_demo/xgboost_direct_forecast_models/*/xgboost.json
```

Recommended best demo model:

```text
data_use_to_demo/xgboost_direct_forecast_models/run_20260519_060214_best/xgboost.json
```

Matching metrics:

```text
data_use_to_demo/xgboost_direct_forecast_models/run_20260519_060214_best/run_20260519_060214.csv
```

Upload fields:

- `max_depth`
- `min_child_weight`
- `mae`
- `mape`
- `rmse`
- `r2`
- `model_file`

After upload:

1. Confirm the model appears in **MODEL RUNS**.
2. Click **SET** to make it active.
3. Click **RESTART PREDICTION**.

To rollback, click **SET** on the previous active model and restart prediction again.

## 8. Dashboard Demo Flow

After data/model setup:

1. Go to **AI Monitor**.
2. Click **START PREDICTION** or **RESTART PREDICTION**.
3. Go to **Dashboard**.
4. Select data year, usually `2026`.
5. Adjust allocation weights if needed:
   - Residential
   - Industrial
   - Commercial
   - Services
6. Click **Generate Allocation** as admin/dev.
7. Check:
   - Weekly forecast load
   - Live forecast stream
   - HeatMap allocation
   - Grid Stress Priorities
   - Ward tooltip explainability

Normal `user` accounts are read-only:

- can view current load, map, live stream, grid stress results
- cannot upload data/model
- cannot start/restart prediction
- cannot generate allocation
- cannot mutate scenarios

## 9. Main API Endpoints

Auth:

```text
POST /api/v1/auth/login
GET  /api/v1/auth/me
POST /api/v1/auth/register
PUT  /api/v1/auth/{user_id}/change-password
DELETE /api/v1/auth/{user_id}/delete-account
```

Data:

```text
POST /api/v1/data/upload-energy
POST /api/v1/data/upload-ward-stats
POST /api/v1/data/upload-holiday
POST /api/v1/data/energy-data
GET  /api/v1/data/status
```

Models:

```text
GET  /api/v1/models/
POST /api/v1/models/
GET  /api/v1/models/active
GET  /api/v1/models/{model_id}/metrics
GET  /api/v1/models/{model_id}/acceptance-graph
POST /api/v1/models/{model_id}/set-active
GET  /api/v1/models/compare?ids=1,2
```

Prediction:

```text
POST /api/v1/prediction/start
POST /api/v1/prediction/stop
POST /api/v1/prediction/restart
```

Simulation:

```text
GET  /api/v1/simulation/current-load
POST /api/v1/simulation/allocate
GET  /api/v1/simulation/grid-stress-priorities?year=2026&limit=10
```

GeoJSON:

```text
GET /api/v1/geojson/wards
```

WebSocket:

```text
ws://localhost:8000/ws/v1/live-predict?token=<JWT_ACCESS_TOKEN>
```

Demo toggle:

```text
POST /api/v1/demo/toggle
```

Demo Mode changes backend prediction update speed. It does not switch the app to frontend mock data.

## 10. API Tester

The frontend exposes a local tester page:

```text
http://localhost:3000/tester.html
```

Open it through the Vite dev server, not with `file://`, so requests can use the Vite proxy.

## 11. Useful Debug Script

The repo includes:

```text
debug_dynamic_ward_allocation.py
```

Run it from the project root with the backend virtual environment:

```bash
backend/venv/bin/python debug_dynamic_ward_allocation.py
```

It is read-only and prints a Markdown breakdown for Ward An Khanh allocation.

## 12. Troubleshooting

### Frontend cannot call backend

Check both servers are running:

```text
Backend:  http://localhost:8000
Frontend: http://localhost:3000
```

Keep `frontend/.env` as:

```env
VITE_API_URL=
VITE_WS_URL=
```

### Login works but `/auth/me` returns 401

Check `JWT_SECRET_KEY` and `JWT_ALGORITHM` in:

```text
backend/app/config/.env
```

Restart backend after changing env values.

### Current load is empty

Start or restart prediction:

```text
AI Monitor -> RESTART PREDICTION
```

If there is still no record, upload energy, ward stats, holiday, and activate a model first.

### HeatMap is empty

Check:

1. `GET /api/v1/geojson/wards` works.
2. Ward stats were uploaded.
3. Allocation was generated for the selected year.
4. Browser console logs for `[MAP]`, `[ALLOC]`, and `[STORE]`.

### WebSocket does not connect

Make sure you are logged in. The WebSocket requires the same JWT access token as REST APIs.

### Invalid model upload

Only XGBoost `.json` models are accepted by filename. The backend does not deeply validate feature names during upload, so use models trained by this project pipeline.

## 13. Build Checks

Frontend production build:

```bash
cd frontend
npm run build
```

Backend import/compile smoke check:

```bash
cd backend
source venv/bin/activate
python -m py_compile main.py init_db.py
```

