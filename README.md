# ProCompta

Gestionnaire de documents comptables — local, sans abonnement, sans cloud.

Organisez vos factures, relevés et reçus par année, correspondant et catégorie. Suivez vos dépenses et recettes, exportez vos bilans, gérez vos devises étrangères.

---

## Prérequis

- [Docker Desktop](https://docs.docker.com/get-docker/) (inclut Docker Compose v2)
- macOS (testé) · Linux compatible

---

## Installation

```bash
git clone <url-du-repo>
cd ProCompta
./setup.sh
```

Le script s'occupe de tout :

- demande ton prénom, e-mail et mot de passe
- génère automatiquement `SECRET_KEY` et le mot de passe PostgreSQL
- crée les dossiers `storage/` et `backups/`
- configure le domaine local `http://procompta.local` (optionnel, nécessite sudo)
- build les images Docker et applique les migrations

À la fin, l'URL et tes identifiants s'affichent dans le terminal.

---

## Utilisation quotidienne

```bash
# Démarrer
docker compose up -d

# Arrêter
docker compose down

# Logs en temps réel
docker compose logs -f api

# Reset complet (supprime la base de données)
docker compose down -v
```

---

## Fonctionnalités

| Catégorie | Détail |
|-----------|--------|
| **Documents** | Upload PDF / JPEG / PNG, preview intégrée, détection de doublons |
| **Organisation** | Catégories (dépense / recette / autre), types, correspondants, tags colorés |
| **Finances** | Montants HT / TVA / TTC, multi-devises (6 devises, conversion BCE automatique) |
| **Vues** | Tableau de bord, vue par année, tous les documents, rapports trimestriels |
| **Recherche** | Recherche globale, filtres date / montant / correspondant, tri des colonnes |
| **Exports** | CSV bilan comptable, CSV liste des documents |
| **Workflow** | Archivage, log d'activité par document, notifications documents incomplets |
| **Sécurité** | Authentification par e-mail + mot de passe, session 30 jours (HMAC) |
| **Backup** | Téléchargement zip (dump SQL + fichiers), restauration avec confirmation |
| **Ergonomie** | Raccourcis clavier (`/` recherche · `N` nouveau · `?` aide), tooltips |

---

## Raccourcis clavier

| Touche | Action |
|--------|--------|
| `/` | Focus la barre de recherche |
| `N` | Nouveau document (import fichier) |
| `?` | Afficher l'aide des raccourcis |
| `Esc` | Fermer les modales |

---

## Stack

| Couche | Technologie |
|--------|-------------|
| Backend | Python 3.13, FastAPI, SQLAlchemy async |
| Base de données | PostgreSQL 16 |
| Migrations | Alembic |
| Frontend | Jinja2, Tailwind CSS 3 (build CLI), Alpine.js, HTMX |
| Previews | pdf2image + Poppler, Pillow |
| Packaging | uv |
| Reverse proxy | Caddy |
| Infrastructure | Docker Compose |

---

## Structure

```
ProCompta/
├── setup.sh                  # Installation en une commande
├── docker-compose.yml
├── Caddyfile
├── .env.example
├── storage/                  # Fichiers uploadés (bind mount Docker)
│   └── previews/
├── backups/                  # Backups téléchargés depuis le profil
└── backend/
    ├── Dockerfile
    ├── entrypoint.sh         # Build Tailwind CSS + démarrage uvicorn
    ├── tailwind.config.js
    ├── pyproject.toml
    └── app/
        ├── models/
        ├── routers/
        ├── services/
        └── templates/
```

---

## Commandes utiles

```bash
# Appliquer de nouvelles migrations après modification des modèles
docker compose exec api uv run alembic upgrade head

# Créer une migration
docker compose exec api uv run alembic revision --autogenerate -m "description"

# Reconstruire après changement de dépendances
docker compose up --build -d
```
