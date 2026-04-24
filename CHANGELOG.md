# Changelog

## [0.4.0] - 2026-04-25

### Ajouté
- **Dashboard enrichi** - 5 stats : dépenses, recettes, solde (avec variation N vs N-1 colorée), TVA déductible, TVA collectée
- **Graphique évolution mensuelle** - barres groupées dépenses/recettes sur 12 mois (Chart.js)
- **Doughnut dépenses par type** - répartition des dépenses de l'année par type de document
- **Top 5 correspondants** - barres horizontales par volume de dépenses
- **Page Rapports** (`/reports`) - nouvelle page accessible depuis la sidebar et depuis la vue année
  - Sélecteur d'année + filtre trimestriel (T1 / T2 / T3 / T4)
  - Bilan annuel : tableau HT / TVA / TTC par catégorie × type, totaux par section, solde global
  - Bilan par correspondant : dépenses TTC, TVA déductible, recettes TTC, TVA collectée, solde
  - Export CSV bilan (agrégé par catégorie × type × correspondant)
  - Export CSV documents (liste complète avec toutes les métadonnées)
- **Navigation croisée** - bouton "Bilan" dans la vue année → rapports ; bouton "Vue YYYY" dans les rapports → vue année

### Corrigé
- `_variation` : division par `abs(prev)` pour éviter un signe inversé quand le solde N-1 est négatif
- `amount_ttc_eur` forcé à `None` côté serveur quand `currency == "EUR"` (évite les données orphelines)

### Technique
- `Chart.js 4.4` via CDN, chargé uniquement sur le dashboard
- Filtre `extract("quarter", ...)` PostgreSQL via SQLAlchemy pour la granularité trimestrielle
- Exports CSV UTF-8 avec BOM (compatible Excel), séparateur `;`, nommage `procompta_{year}[_T{q}]_{type}.csv`
- Macro `stat_card` étendue avec paramètres optionnels `variation` et `variation_color`

---

## [0.3.0] - 2026-04-24

### Ajouté
- **Sélecteur de devise** - `<select>` avec 6 devises principales (EUR, USD, GBP, CHF, JPY, CAD) à la place du champ texte libre
- **Champ équivalent EUR** (`amount_ttc_eur`) - visible uniquement si la devise n'est pas EUR ; pré-rempli automatiquement via l'API BCE (taux historique à la date de paiement ou du jour si absente) ; bouton de recalcul manuel ; se vide automatiquement si la devise change ou si la catégorie passe en "Autre"
- **Totaux EUR uniquement** - les totaux du dashboard, de la vue année et de la liste des années n'agrègent que les équivalents EUR (`amount_ttc_eur` pour les devises étrangères, `amount_ttc` pour EUR)
- **Alerte devise étrangère** - bandeau ambre dans la vue année si des documents non-EUR sont présents sans équivalent EUR renseigné (exclus des totaux)
- **Affichage EUR dans les tableaux** - dashboard, vue année et tous les documents affichent le montant EUR ; la valeur originale dans la devise d'origine apparaît en sous-titre grisé

### Technique
- Champ `amount_ttc_eur` (`Numeric(12,2)`, nullable) sur le modèle `documents`, migration Alembic `20260424_0004`
- `POST /api/documents/{id}/convert-currency` - endpoint de calcul pur (pas d'écriture en base) ; appel à l'API SDMX de la BCE (`data-api.ecb.europa.eu`) avec fenêtre 10 jours puis 30 jours en fallback
- Expression SQLAlchemy `CASE` dans `pages.py` pour agréger `amount_ttc_eur` ou `amount_ttc` selon la devise dans toutes les requêtes de totaux
- `pyproject.toml` - ajout de `httpx`

---

## [0.2.5] - 2026-04-24

### Ajouté
- Boutons **Télécharger**, **Envoyer** (ouvre le client mail avec sujet pré-rempli) et **Imprimer** (ouvre le fichier dans un nouvel onglet) dans le header de la page d'édition, séparés du bouton Supprimer par un diviseur

### Modifié
- **Alertes dashboard** - les warnings portent désormais sur les documents sans **type** et sans **correspondant** (les tags ne sont plus requis)
- **Vue `/documents`** - filtre `no_tags` remplacé par `no_type` ; pill et sous-titre mis à jour en conséquence
- **Colonnes badges** - Catégorie, Type et Tags sont centrées dans tous les tableaux (tableau de bord, vues année, tous les documents)
- **Correction effet de bord catégorie** - passer en "Autre" vide immédiatement les champs financiers et la date de paiement via `$watch` Alpine.js ; `payDate` remonté dans `docEditData()` pour être accessible depuis le watcher
- **Vue "Toutes les années"** - affiche le solde net TTC (recettes − dépenses) coloré vert/rouge au lieu de la somme brute
- **Titre vue année** - affiché "Année 2026" au lieu de "2026" (page, `<h1>` et lien sidebar)

---

## [0.2.0] - 2026-04-24

Structuration des documents autour de trois catégories métier fixes.

### Ajouté

- **Champ `category`** sur les documents - enum `depense | recette | autre`, migration Alembic avec `server_default = autre` pour les documents existants
- **Sélecteur de catégorie** en haut du formulaire d'édition - 3 boutons radio stylisés (rouge / vert / gris), sélection obligatoire
- **Masquage conditionnel** des champs financiers (HT, TVA, TTC) et de la date de paiement via Alpine.js `x-show` quand la catégorie est "Autre"
- **Vue année restructurée** - 3 sections distinctes (Dépenses / Recettes / Autres), chacune avec son propre total TTC et un compteur de documents ; sections masquées si vides
- **Largeurs de colonnes fixes** dans les tableaux via `<colgroup>` + `table-fixed` ; scroll horizontal sur petit écran
- **Dashboard** - nouvelles stats : total dépenses TTC, total recettes TTC, solde net (coloré rouge/vert selon signe) ; badge de catégorie sur les documents récents
- **Header de la vue année** - affichage inline des totaux dépenses (-X €) et recettes (+X €) en rouge/vert

### Modifié

- Schémas Pydantic `DocumentCreate`, `DocumentUpdate`, `DocumentResponse` - ajout du champ `category`
- Filtre `list_documents` de l'API - accepte désormais un paramètre `category`
- `document_update_form` - les champs financiers sont mis à `None` côté serveur quand `category = autre`

---

## [0.1.0] - 2026-04-23

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
- `POST /api/documents/upload` - upload avec calcul SHA-256, détection de doublons (409)
- `GET/PATCH/DELETE /api/documents/{id}` - CRUD document
- `GET /api/documents` - liste avec filtres (année, correspondant, type, tags, recherche)
- `GET /api/documents/{id}/file` - service du fichier (PDF ou image) avec `Content-Disposition: inline`
- `GET /api/documents/years` - liste des années ayant des documents
- CRUD complet pour `correspondents`, `document_types`, `tags` (avec PATCH pour édition)
- Extraction automatique de la date depuis les métadonnées PDF (`pdfinfo -isodates`)
- Génération de preview PNG (première page PDF via pdf2image, images via Pillow)

#### Formats supportés
- PDF - upload, preview, visualisation inline
- JPEG / PNG - upload, preview redimensionnée, visualisation inline

#### Interface
- Layout global : navbar + sidebar pliable (état persisté en `localStorage`)
- Clic sur le logo / nom de l'app → tableau de bord
- **Tableau de bord** - stats (total, année courante, mois), alertes documents sans tags / sans correspondant, 5 documents récents
- **Vue année** (`/year/{year}`) - tableau complet, filtres (correspondant, type, recherche texte), totaux TTC, upload drag-and-drop + bouton fichier
- **Édition document** (`/documents/{id}/edit`) - split 50/50, viewer PDF/image avec fond #7F7F7F, formulaire complet (titre, dates, montants HT/TVA/TTC, devise, correspondant, type, tags, notes), création rapide de correspondant / type / tag à la volée, affichage du type de fichier et du poids en bas de formulaire
- **Liste des années** (`/years`) - cards par année avec nombre de documents et total TTC
- **Configuration** (`/config`) - onglets correspondants / types / tags, édition inline avec annulation, suppression HTMX sans rechargement
- **Tous les documents** (`/documents`) - vue transversale avec filtres `sans tags` / `sans correspondant`, pills actif/inactif

#### Navigation
- Retour contextuel depuis l'édition : renvoie vers la vue filtrée d'origine (`/documents?no_tags=1`, etc.) si l'accès venait de là, sinon vers la vue année
- Clic sur toute la ligne d'un tableau → ouvre le document

#### Robustesse
- Page d'erreur HTML personnalisée (404, 403, 500) - les routes `/api/*` conservent des réponses JSON
- Validation de l'année dans `/year/{year}` : 404 si aucun document n'existe pour cette année
- Paramètre `back` validé (doit commencer par `/`) pour éviter les redirections externes

### Technique
- Routing FastAPI avec préfixe `/api` séparé des routes de pages
- Alpine.js : logique d'upload extraite en fonction `yearData()` dans un bloc `<script>` (évite les conflits d'échappement dans les attributs HTML)
- Sécurité anti-doublon upload par hash SHA-256
- `Content-Disposition: inline` pour la visualisation dans l'iframe / balise `<img>`
