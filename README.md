# Geospatial Logistics API Monorepo

Production-style starter for a geospatial telemetry engine:

- `apps/edge-api`: FastAPI + MongoDB Motor async driver
- `apps/command-center`: Next.js dispatcher UI with live map and nearest-driver panel
- `infra/mongodb`: MongoDB schema and index setup scripts

## Monorepo Structure

```text
.
├─ apps/
│  ├─ edge-api/
│  │  ├─ app/
│  │  │  ├─ main.py
│  │  │  ├─ models.py
│  │  │  ├─ routes.py
│  │  │  ├─ settings.py
│  │  │  └─ services/
│  │  │     └─ database.py
│  │  ├─ seed.py
│  │  ├─ pyproject.toml
│  │  └─ .env.example
│  └─ command-center/
│     ├─ app/
│     ├─ components/
│     ├─ hooks/
│     ├─ lib/
│     └─ package.json
└─ infra/
   └─ mongodb/
      ├─ create_indexes.js
      ├─ driver.schema.json
      └─ seed.drivers.json
```

## 1) MongoDB Atlas Setup

1. Create an Atlas M0 cluster.
2. Create database `logistics` and collection `drivers`.
3. Add index using `infra/mongodb/create_indexes.js`.

`create_indexes.js` command in Atlas shell:

```javascript
use("logistics");
db.drivers.createIndex({ location: "2dsphere" });
db.drivers.createIndex({ status: 1, updatedAt: -1 });
```

## 2) Edge API

From `apps/edge-api`:

```bash
python -m pip install -e .
python -m fastapi dev app/main.py
```

Seed dummy Karachi drivers:

```bash
python seed.py
```

## 3) Command Center

From `apps/command-center`:

```bash
npm install
npm run dev
```

App defaults to Karachi map center and polls nearest drivers every 5 seconds.

## 4) Environment

Set these values in `apps/edge-api/.env`:

```env
MONGODB_URI=mongodb+srv://<user>:<password>@cluster0.example.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE_NAME=logistics
ALLOWED_ORIGIN=http://localhost:3000
```
