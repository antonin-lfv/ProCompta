# ProCompta

Gestionnaire de documents comptables — local, simple, sans abonnement.
Organisez vos factures, reçus et relevés par année, correspondant et tags.

---

## Prérequis

- [Docker](https://docs.docker.com/get-docker/) + [Docker Compose](https://docs.docker.com/compose/) (v2)
- Git

---

## Lancer le projet

### 1. Cloner le dépôt

```bash
git clone <url-du-repo>
cd ProCompta
```

### 2. Configurer l'environnement

```bash
cp .env.example .env
```

Éditer `.env` et adapter si besoin :

```env
POSTGRES_USER=procompta
POSTGRES_PASSWORD=changeme          # à changer en production
POSTGRES_DB=procompta
DATABASE_URL=postgresql+asyncpg://procompta:changeme@db:5432/procompta
STORAGE_PATH=/absolute/path/to/ProCompta/storage   # chemin local vers le dossier storage
API_PORT=8000
```

### 3. Démarrer les services

```bash
docker compose up --build -d
```

Les services démarrent dans cet ordre : `db` → `api` (grâce aux healthchecks).

### 4. Appliquer les migrations

```bash
docker compose exec api uv run alembic upgrade head
```

### 5. Ouvrir l'application

```
http://localhost:8000
```

---

## Commandes utiles

```bash
# Voir les logs en temps réel
docker compose logs -f api

# Arrêter les services
docker compose down

# Arrêter et supprimer les volumes (reset complet de la base)
docker compose down -v

# Créer une nouvelle migration après modification des modèles
docker compose exec api uv run alembic revision --autogenerate -m "description"

# Appliquer les migrations
docker compose exec api uv run alembic upgrade head
```

---

## Structure du projet

```
ProCompta/
├── docker-compose.yml
├── .env.example
├── storage/                  # Fichiers et previews (volume Docker)
│   ├── documents/
│   └── previews/
└── backend/
    ├── Dockerfile
    ├── pyproject.toml
    ├── alembic.ini
    ├── alembic/
    └── app/
        ├── main.py
        ├── config.py
        ├── database.py
        ├── models/
        ├── schemas/
        ├── routers/
        ├── services/
        └── templates/
```

---

## Stack

| Couche | Technologie |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy (async) |
| Base de données | PostgreSQL 16 |
| Migrations | Alembic |
| Frontend | Jinja2, Tailwind CSS, Alpine.js, HTMX |
| Previews | pdf2image + Poppler, Pillow |
| Packaging | uv |
| Infrastructure | Docker Compose |

---

## Formats supportés

| Format | Upload | Preview |
|---|---|---|
| PDF | ✓ | ✓ |
| JPEG | ✓ | ✓ |
| PNG | ✓ | ✓ |

---

## Roadmap

| Version | Fonctionnalité |
|---|---|
| v0.2 | OCR / extraction automatique des métadonnées |
| v0.3 | Export comptable CSV |
| v0.4 | Recherche full-text |
| v0.5 | Authentification multi-utilisateurs |
| v1.0 | Thème sombre |
