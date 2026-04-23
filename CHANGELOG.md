# Changelog

## [0.1.0] — 2026-04-23

Première version stable du MVP.

### Ajouté

#### Infrastructure
- `docker-compose.yml` avec services `api` (FastAPI) et `db` (PostgreSQL 16)
- `Dockerfile` Debian slim + uv + Poppler
- Healthchecks Docker sur `db` (`pg_isready`) et `api` (`/health`)
- `.env.example` avec toutes les variables nécessaires
- Volume persistant pour PostgreSQL et pour le stockage des fichiers

#### Base de données
- Modèles SQLAlchemy async : `documents`, `correspondents`, `document_types`, `tags`, `document_tags`
- Configuration Alembic pour migrations async
- Migration initiale complète

#### API
- `POST /api/documents/upload` — upload avec calcul SHA-256, détection de doublons (409)
- `GET/PATCH/DELETE /api/documents/{id}` — CRUD document
- `GET /api/documents` — liste avec filtres (année, correspondant, type, tags, recherche)
- `GET /api/documents/{id}/file` — service du fichier (PDF ou image) avec `Content-Disposition: inline`
- `GET /api/documents/years` — liste des années ayant des documents
- CRUD complet pour `correspondents`, `document_types`, `tags` (avec PATCH pour édition)
- Extraction automatique de la date depuis les métadonnées PDF (`pdfinfo -isodates`)
- Génération de preview PNG (première page PDF via pdf2image, images via Pillow)

#### Formats supportés
- PDF — upload, preview, visualisation inline
- JPEG / PNG — upload, preview redimensionnée, visualisation inline

#### Interface
- Layout global : navbar + sidebar pliable (état persisté en `localStorage`)
- Clic sur le logo / nom de l'app → tableau de bord
- **Tableau de bord** — stats (total, année courante, mois), alertes documents sans tags / sans correspondant, 5 documents récents
- **Vue année** (`/year/{year}`) — tableau complet, filtres (correspondant, type, recherche texte), totaux TTC, upload drag-and-drop + bouton fichier
- **Édition document** (`/documents/{id}/edit`) — split 50/50, viewer PDF/image avec fond #7F7F7F, formulaire complet (titre, dates, montants HT/TVA/TTC, devise, correspondant, type, tags, notes), création rapide de correspondant / type / tag à la volée, affichage du type de fichier et du poids en bas de formulaire
- **Liste des années** (`/years`) — cards par année avec nombre de documents et total TTC
- **Configuration** (`/config`) — onglets correspondants / types / tags, édition inline avec annulation, suppression HTMX sans rechargement
- **Tous les documents** (`/documents`) — vue transversale avec filtres `sans tags` / `sans correspondant`, pills actif/inactif

#### Navigation
- Retour contextuel depuis l'édition : renvoie vers la vue filtrée d'origine (`/documents?no_tags=1`, etc.) si l'accès venait de là, sinon vers la vue année
- Clic sur toute la ligne d'un tableau → ouvre le document

#### Robustesse
- Page d'erreur HTML personnalisée (404, 403, 500) — les routes `/api/*` conservent des réponses JSON
- Validation de l'année dans `/year/{year}` : 404 si aucun document n'existe pour cette année
- Paramètre `back` validé (doit commencer par `/`) pour éviter les redirections externes

### Technique
- Routing FastAPI avec préfixe `/api` séparé des routes de pages
- Alpine.js : logique d'upload extraite en fonction `yearData()` dans un bloc `<script>` (évite les conflits d'échappement dans les attributs HTML)
- Sécurité anti-doublon upload par hash SHA-256
- `Content-Disposition: inline` pour la visualisation dans l'iframe / balise `<img>`
