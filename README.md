# Geospatial Logistics API Monorepo

Production-style starter for a serverless geospatial telemetry engine:

- `apps/edge-api`: Cloudflare Workers (Python) + FastAPI + MongoDB Atlas Data API
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
│  │  │     └─ atlas_data_api.py
│  │  ├─ worker.py
│  │  ├─ pyproject.toml
│  │  └─ wrangler.toml
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
2. Create database `fleet_ops` and collection `drivers`.
3. Enable Atlas Data API for this project.
4. Add index using `infra/mongodb/create_indexes.js`.

`create_indexes.js` command in Atlas shell:

```javascript
use("fleet_ops");
db.drivers.createIndex({ location: "2dsphere" });
db.drivers.createIndex({ status: 1, updatedAt: -1 });
```

## 2) Edge API

From `apps/edge-api`:

```bash
uv sync
uv run fastapi dev app/main.py
```

Cloudflare local run:

```bash
uv run pywrangler dev
```

## 3) Command Center

From `apps/command-center`:

```bash
npm install
npm run dev
```

App defaults to Karachi map center and polls nearest drivers every 5 seconds.

## 4) Secrets & Deploy

Edge API secrets in Cloudflare:

```bash
uv run pywrangler secret put ATLAS_DATA_API_KEY
uv run pywrangler secret put ATLAS_DATA_API_URL
uv run pywrangler secret put ATLAS_DATA_SOURCE
uv run pywrangler secret put ATLAS_DATABASE
uv run pywrangler secret put ATLAS_COLLECTION
uv run pywrangler secret put ALLOWED_ORIGIN
```

Deploy:

```bash
uv run pywrangler deploy
```
