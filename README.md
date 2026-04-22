# Projet : ProCompta v0.1

## Vision

Logiciel **local** de gestion documentaire comptable, inspiré de Paperless-ngx mais **simplifié** et **personnalisé**. Objectif : organiser, tagger et retrouver facilement tous les documents comptables (factures, reçus, relevés, etc.) par année.

Approche **MVP itératif** : on démarre minimal et on enrichit progressivement. Il faut appliquer au niveau du code et de l'architecture des technos une rigeur exemplaire, avec toutes les bonnes pratiques.

---

## Stack technique

### Backend
- **Python 3.13**
- **uv** pour la gestion des dépendances (`uv add`, `uv sync`, `uv run`)
- **FastAPI**
- **PostgreSQL v18** (stockage métadonnées)
- **SQLAlchemy** + **Alembic** (ORM + migrations)
- **Pydantic v2** (validation)
- Stockage des fichiers : dossier local monté en volume Docker (pas de blob en BDD, juste le chemin)
- Génération des previews PDF : **pdf2image** + **Poppler** (première page en PNG)

### Frontend
**HTMX + Jinja2 + Tailwind CSS + Alpine.js**

- HTMX pour les interactions dynamiques (upload, filtres, modals) sans écrire de JS
- Alpine.js pour les petites interactions locales (dropdowns, sidebar pliable)
- Tailwind via CDN au départ, puis CLI quand on passera en prod
- Jinja2 pour le templating côté FastAPI

### Infrastructure
- **Docker Compose** avec 3 services : `api` (FastAPI), `db` (Postgres), `proxy` (Caddy ou Nginx, optionnel au MVP)
- Volume persistant pour les fichiers PDF
- Volume persistant pour Postgres
- `.env` pour la config

---

## Modèle de données

### Tables

**`documents`**
- `id` (UUID, PK)
- `title` (str)
- `file_path` (str, relatif au volume de stockage)
- `file_hash` (sha256, pour détecter les doublons)
- `mime_type` (str)
- `file_size` (int, bytes)
- `document_date` (date, date du document)
- `payment_date` (date, nullable)
- `amount_ht` (decimal, nullable) — montant hors taxes
- `vat_amount` (decimal, nullable) — montant de la TVA
- `vat_rate` (decimal, nullable) — taux de TVA (ex. 20.0, 10.0, 5.5, 0.0, defaut : 0%)
- `amount_ttc` (decimal, nullable) — montant toutes taxes comprises
- `currency` (str, défaut "EUR")
- `correspondent_id` (FK → correspondents)
- `document_type_id` (FK → document_types)
- `notes` (text, nullable)
- `created_at`, `updated_at` (timestamps)

**`correspondents`** (fournisseurs, clients, organismes)
- `id`, `name`, `slug`, `notes`, `created_at`

**`document_types`** (facture, reçu, relevé bancaire, contrat, URSSAF, TVA, etc.)
- `id`, `name`, `slug`, `color` (pour l'UI), `icon` (nullable)

**`tags`** (libres, multiples par document)
- `id`, `name`, `slug`, `color`

**`document_tags`** (table de liaison many-to-many)
- `document_id`, `tag_id`

> `document_type` est unique par document (structurant), `tags` sont multiples et libres, comme dans Paperless.

---

## Interface

### Layout global
- **Navbar supérieure**
  - Gauche : logo + "ProCompta"
  - Droite : cloche notifications (placeholder au MVP) + dropdown profil/paramètres
- **Sidebar gauche** (pliable, ne montre que les icônes une fois pliée)
  - Tableau de bord
  - Année courante (ex. 2026) — lien direct
  - Toutes les années
  - Configuration (tags, types, correspondants)
  - Footer sidebar : version de l'app (`v0.1`)
- **Zone centrale** : contenu de la page active

### Pages

**1. Tableau de bord (`/`)**
- Nombre total de documents
- Nombre de documents de l'année courante
- Répartition par type (petit chart)
- Derniers documents ajoutés (5 plus récents)
- Documents sans tags / sans correspondant (alertes)

**2. Vue d'une année (`/year/{year}`)**
- Grille de cards avec preview PDF (première page)
- Chaque card affiche : titre, date, correspondant, tags (badges colorés), type
- Actions par card : Télécharger, Ouvrir (nouvel onglet), menu "..." (Modifier / Supprimer)
- Suppression avec modal de confirmation
- **Barre de filtres** en haut : correspondant, type, tags (multi), recherche texte sur titre
- **Zone de drop** pour uploader un fichier → après upload, redirige vers la page de modification

**3. Liste des années (`/years`)**
- Cards pour chaque année ayant au moins un document (nb de documents, total TTC si renseigné)

**4. Modification d'un document (`/documents/{id}/edit`)**
- Split 50/50
- **Droite** : preview PDF (iframe ou PDF.js)
- **Gauche** : formulaire
    - Titre
    - Date du document
    - Date de paiement
    - Montant HT
    - Taux de TVA (select : 0%, 5.5%, 10%, 20%, Autre)
    - Montant TVA
    - Montant TTC
    - Devise 
    - Correspondant (select depuis la liste)
    - Type de document (select unique)
    - Tags (multi-select avec création à la volée)
    - Notes (textarea)
- Boutons : Enregistrer / Annuler / Supprimer

**5. Configuration (`/config`)**
- Onglets : Correspondants, Types de documents, Tags
- CRUD simple sur chaque (ajout, édition inline, suppression avec confirmation si utilisé)

---

## Scope MVP (v0.1)

Pour la **première itération**, on se concentre sur :
1. Setup Docker Compose (api + db) avec uv dans le Dockerfile
2. Modèles SQLAlchemy + migrations Alembic
3. CRUD API pour : documents, correspondants, types, tags
4. Upload de fichier PDF avec calcul de hash (détection doublons)
5. Génération de preview (première page PDF → PNG)
6. Pages : dashboard (simple), vue année, vue édition, config
7. Layout navbar + sidebar pliable
8. Filtres par tag/type/correspondant sur la vue année

**Hors scope v0.1** (pour plus tard) :
- Authentification (on assume local single-user au début)
- OCR / extraction auto des métadonnées
- Notifications réelles
- Export comptable (CSV)
- Recherche full-text
- Multi-utilisateurs
- Thème sombre

---

## Arborescence proposée

```
procompta/
├── docker-compose.yml
├── .env.example
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── alembic.ini
│   ├── alembic/
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── models/
│       ├── schemas/
│       ├── routers/
│       ├── services/          # upload, preview PDF, hash
│       ├── templates/         # Jinja2
│       │   ├── base.html
│       │   ├── partials/      # navbar, sidebar, cards
│       │   └── pages/
│       └── static/
│           ├── css/
│           └── js/            # alpine, htmx (CDN au départ)
└── storage/                   # volume docker pour les PDFs
    ├── documents/
    └── previews/
```

---

## Notes techniques

- **Python 3.13** dans le `Dockerfile` (image de base `python:3.13-slim`)
- **uv** installé dans le Dockerfile, utilisé pour installer les deps via `uv sync` (pas de `pip install`)
- **Poppler** à installer dans le Dockerfile : `apt-get install -y poppler-utils` (requis par `pdf2image`)
- Pas de `requirements.txt` : on utilise `pyproject.toml` + `uv.lock`
- Healthcheck Docker sur la route `/health`

---

## Pour démarrer

Merci de :
1. Me proposer un **plan de développement** en phases (ordre des tickets pour le MVP)
2. Démarrer par **l'initialisation du projet** :
   - `docker-compose.yml`
   - `Dockerfile` backend (Python 3.13 + uv + poppler)
   - `pyproject.toml` initialisé avec uv
   - Structure des dossiers
   - `main.py` FastAPI qui démarre avec une route `/health`
3. Me demander confirmation avant de passer à la phase suivante

On itère étape par étape, pas de big bang. Après chaque phase, je teste et on corrige si besoin avant d'avancer.
