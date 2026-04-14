# PLCtracker

A lightweight web app for tracking product lifecycle status across a fleet of
SAP material masters. Upload a SAP extract, see every `(material, plant)` on a
kanban-style board, flag MRP-profile mismatches and factory-vs-warehouse
inconsistencies, and keep comments + actions against each SKU.

## Features

- Per-user login (sessions via signed cookies; bcrypt-hashed passwords).
- **CSV / XLSX upload** with column auto-detection (accepts `MATNR`, `WERKS`,
  `Plant-sp.matl status`, `MRP profile`, plus common aliases).
- Immutable **snapshot** per upload + upsert into the live product table.
- **Stage-transition detection** between uploads (powers the "recent changes"
  view and per-product history).
- **MRP validation**: every row is checked against a configurable
  `(plant, status) → expected MRP profile` rule table. Mismatches are shown
  as red badges on the board, on product detail, and as a dashboard tile
  with drill-through.
- **Family-status mismatch**: every `material_no` is compared across plants.
  If the **factory** plant is at a different status from one of its
  **warehouses**, the warehouse row is flagged (e.g. "factory QF00 is O2;
  this warehouse is still A1 — review data"). Powerful for catching SAP
  data-hygiene problems.
- **Kanban board**, sortable **table**, and **dashboard** (counts per stage,
  aging histogram, recent transitions, mismatch tiles). All three share a
  filter bar (plant / material-contains / status / owner).
- **CSV export** of the current filtered view.
- **Admin**: manage users, reclassify plants (factory/warehouse/other),
  rename/reorder lifecycle stages, and edit the MRP rule matrix cell-by-cell.
- **Per-product comments and actions** (title + due date + assignee).

## Tech stack

Python 3.11+, FastAPI, SQLAlchemy 2, SQLite (WAL mode), Jinja2, Chart.js,
pandas / openpyxl for uploads, passlib+bcrypt for auth.

## Data model highlights

- `product(material_no, plant_code, stage_code, mrp_profile, owner_id,
  mrp_mismatch, family_mismatch, ...)` — unique on `(material_no, plant_code)`.
- `plant(plant_code, plant_type, description)` — `plant_type` in
  `factory|warehouse|other`.
- `lifecycle_stage(code, label, family, display_order, color, is_terminal)` —
  seeded from `seed/stages.csv`.
- `mrp_rule(plant_code NULLABLE, stage_code, expected_mrp_profile)` —
  plant-specific rule wins over plant-agnostic (`plant_code IS NULL`).
- `snapshot` + `snapshot_row`: immutable record of every upload.
- `stage_transition`: per-product history of stage changes.

## Lifecycle statuses (seeded)

| Code | Label                                    |
| ---- | ---------------------------------------- |
| N1   | New Product – not planned yet            |
| N2   | New Product – planning active            |
| A1   | Active Product                           |
| O1   | Intent to obsolete / flagged with demand |
| O2   | Obsoletion in progress                   |
| O3   | Obsolete                                 |

## MRP rules (seeded)

Only the obsoletion stages have a required MRP profile. **N1, N2, and A1
accept any MRP profile without warning** — the field is tracked and shown,
but it isn't validated.

| Status | Plant | Expected MRP |
| ------ | ----- | ------------ |
| N1     | any   | *not validated* |
| N2     | any   | *not validated* |
| A1     | any   | *not validated* |
| O1     | any   | NOPL         |
| O2     | any   | NOPL         |
| O3     | any   | OBSO         |

All rules are editable per-plant (or "All plants") in Admin → MRP rules.
Leaving a cell blank removes the rule, which means rows with that status
at that plant won't be flagged.

## Running locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export PLCT_ADMIN_EMAIL=you@example.com
export PLCT_ADMIN_PASSWORD=your-initial-password
./run.sh              # http://localhost:8000
```

On first start the app creates `data/app.db`, seeds stages/plants/MRP rules
from `seed/*.csv`, and creates an admin user with the credentials above.

### Running the tests

```bash
pytest -q
```

## Deploying to Render (recommended)

1. Push this repository to GitHub.
2. In Render, click *New → Blueprint* and point it at the repo. Render will
   pick up `render.yaml`.
3. Set the `PLCT_ADMIN_EMAIL` and `PLCT_ADMIN_PASSWORD` env vars in the
   dashboard. `PLCT_SECRET_KEY` is generated automatically.
4. Deploy. The container mounts `/data` as a persistent disk (the SQLite
   file lives there, so it survives redeploys).

For other platforms: the app is a plain FastAPI + SQLite service. Any PaaS
that runs a Dockerfile with a persistent volume mount will work. A nightly
backup of `/data/app.db` to object storage is strongly recommended.

## Upload format

The uploader accepts any CSV or XLSX with the four columns below. Column
order doesn't matter; header names are matched case-insensitively with
several aliases.

| Canonical      | Accepted headers                                            |
| -------------- | ----------------------------------------------------------- |
| `material_no`  | `Material`, `MATNR`, `Material Number`                      |
| `plant_code`   | `Plant`, `WERKS`                                            |
| `stage_code`   | `Plant-sp.matl status`, `Plant-specific material status`, `MSTAE`, `Status` |
| `mrp_profile`  | `MRP profile`, `MRP`                                        |

Rows with blank material/plant/status are silently dropped. Uppercasing is
applied to `plant_code`, `stage_code`, and `mrp_profile`.

See `samples/sap_extract_sample.csv` for a minimal valid file.

## Environment variables

| Variable               | Purpose                                          | Default                     |
| ---------------------- | ------------------------------------------------ | --------------------------- |
| `PLCT_DB_PATH`         | Where the SQLite file lives                      | `./data/app.db`             |
| `PLCT_SECRET_KEY`      | Session-cookie signing key (set in prod!)        | `dev-insecure-change-me`    |
| `PLCT_ADMIN_EMAIL`     | Bootstrap admin email                            | `admin@example.com`         |
| `PLCT_ADMIN_PASSWORD`  | Bootstrap admin password                         | `changeme`                  |
| `PLCT_ADMIN_NAME`      | Bootstrap admin display name                     | `Admin`                     |

## License

Internal use.
