# ProCompta — Suivi des tâches & Changelog

## Version courante : `v0.1.0-dev`

---

## Kanban

### 🔄 En cours
_(rien — Phase 4 terminée, en attente de validation avant Phase 5)_

### ✅ Terminé

#### Phase 1 — Fondations ✅
- [x] **[P1-1]** `docker-compose.yml` (services `api` + `db`)
- [x] **[P1-2]** `Dockerfile` backend (Python 3.13 + uv + Poppler)
- [x] **[P1-3]** `pyproject.toml` + `uv.lock` générés
- [x] **[P1-4]** Structure des dossiers complète
- [x] **[P1-5]** `main.py` FastAPI + route `/health` (testé)
- [x] **[P1-6]** `.env.example` + `.env` local

### 📋 Backlog

#### Phase 2 — Modèles & base de données ✅
- [x] **[P2-1]** `database.py` (engine async, session, base)
- [x] **[P2-2]** Modèle `correspondents`
- [x] **[P2-3]** Modèle `document_types`
- [x] **[P2-4]** Modèle `tags`
- [x] **[P2-5]** Modèle `documents` + table liaison `document_tags`
- [x] **[P2-6]** Configuration Alembic (`alembic.ini` + `env.py` async)
- [x] **[P2-7]** Migration initiale (`20260422_0001_init.py`)

#### Phase 3 — API CRUD ✅
- [x] **[P3-1]** Schémas Pydantic v2 (correspondents, types, tags, documents)
- [x] **[P3-2]** Router correspondants (CRUD)
- [x] **[P3-3]** Router types de documents (CRUD)
- [x] **[P3-4]** Router tags (CRUD)
- [x] **[P3-5]** Router documents (CRUD + liste + filtres year/correspondent/type/tag/search)
- [x] **[P3-6]** Endpoint `POST /api/documents/upload` (hash SHA256, détection doublons 409)
- [x] **[P3-7]** Service génération preview (pdf2image → PNG, async thread pool)
- [x] **[P3-8]** `GET /api/documents/years` — liste des années avec documents

#### Phase 4 — Layout & templates de base ✅
- [x] **[P4-1]** `base.html` (Tailwind CDN, HTMX, Alpine.js, Inter font)
- [x] **[P4-2]** Partial `navbar.html`
- [x] **[P4-3]** Partial `sidebar.html` pliable (Alpine.js + localStorage)
- [x] **[P4-4]** Partial `macros.html` (stat_card, alert_card, badge, empty_state)
- [x] **[P4-5]** `app/templating.py` — singleton Jinja2 + globals (current_year, app_version)
- [x] **[P4-6]** `routers/pages.py` + dashboard `/` avec stats DB

#### Phase 5 — Pages frontend
- [ ] **[P5-1]** Dashboard `/` — stats + derniers documents
- [ ] **[P5-2]** Vue année `/year/{year}` — grille cards + filtres
- [ ] **[P5-3]** Upload drag-and-drop sur la vue année (HTMX)
- [ ] **[P5-4]** Vue édition `/documents/{id}/edit` — split 50/50
- [ ] **[P5-5]** Liste des années `/years`
- [ ] **[P5-6]** Configuration `/config` — onglets Correspondants / Types / Tags

#### Phase 6 — Polish MVP
- [ ] **[P6-1]** Gestion des erreurs (404, doublons, fichier invalide)
- [ ] **[P6-2]** Healthcheck Docker
- [ ] **[P6-3]** Confirmation de suppression (modal HTMX)
- [ ] **[P6-4]** `README.md` instructions de lancement

---

## Changelog

### [0.1.0-dev] — 2026-04-22 — Phase 2 terminée
#### Ajouté
- Structure initiale du projet (arborescence complète)
- `docker-compose.yml` avec services `api` (FastAPI) et `db` (Postgres 16) + healthchecks
- `Dockerfile` Python 3.13-slim + uv + Poppler
- `pyproject.toml` + `uv.lock` (31 packages)
- `app/main.py` FastAPI avec route `GET /health`
- `app/config.py` avec `pydantic-settings`
- `.env.example` + `.env` local
- Dossiers `storage/documents/` et `storage/previews/`

---

## Roadmap post-MVP (hors scope v0.1)

- `v0.2` — OCR / extraction automatique des métadonnées
- `v0.3` — Export comptable CSV
- `v0.4` — Recherche full-text
- `v0.5` — Authentification (multi-utilisateurs)
- `v1.0` — Thème sombre + notifications réelles
