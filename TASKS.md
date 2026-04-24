# ProCompta - Suivi des tâches

## Version courante : `v0.4.0` 🚧

---

## Kanban

### ✅ Terminé - v0.1.0

#### Phase 1 - Fondations ✅
- [x] **[P1-1]** `docker-compose.yml` (services `api` + `db`)
- [x] **[P1-2]** `Dockerfile` backend (Python 3.13 + uv + Poppler)
- [x] **[P1-3]** `pyproject.toml` + `uv.lock` générés
- [x] **[P1-4]** Structure des dossiers complète
- [x] **[P1-5]** `main.py` FastAPI + route `/health` (testé)
- [x] **[P1-6]** `.env.example` + `.env` local

#### Phase 2 - Modèles & base de données ✅
- [x] **[P2-1]** `database.py` (engine async, session, base)
- [x] **[P2-2]** Modèle `correspondents`
- [x] **[P2-3]** Modèle `document_types`
- [x] **[P2-4]** Modèle `tags`
- [x] **[P2-5]** Modèle `documents` + table liaison `document_tags`
- [x] **[P2-6]** Configuration Alembic (`alembic.ini` + `env.py` async)
- [x] **[P2-7]** Migration initiale

#### Phase 3 - API CRUD ✅
- [x] **[P3-1]** Schémas Pydantic v2 (correspondents, types, tags, documents)
- [x] **[P3-2]** Router correspondants (CRUD)
- [x] **[P3-3]** Router types de documents (CRUD)
- [x] **[P3-4]** Router tags (CRUD)
- [x] **[P3-5]** Router documents (CRUD + liste + filtres)
- [x] **[P3-6]** Upload PDF/JPEG/PNG (hash SHA256, détection doublons 409)
- [x] **[P3-7]** Génération preview (pdf2image + Pillow, async)
- [x] **[P3-8]** Extraction date depuis métadonnées PDF (`pdfinfo`)

#### Phase 4 - Layout & templates de base ✅
- [x] **[P4-1]** `base.html` (Tailwind CDN, HTMX, Alpine.js)
- [x] **[P4-2]** Navbar + lien logo → dashboard
- [x] **[P4-3]** Sidebar pliable (Alpine.js + localStorage)
- [x] **[P4-4]** Macros Jinja2 (stat_card, alert_card, badge, empty_state)
- [x] **[P4-5]** Globals Jinja2 (current_year, app_version)

#### Phase 5 - Pages frontend ✅
- [x] **[P5-1]** Dashboard - stats + alertes + documents récents
- [x] **[P5-2]** Vue année - tableau + filtres + totaux TTC
- [x] **[P5-3]** Upload drag-and-drop + bouton fichier
- [x] **[P5-4]** Édition document - viewer + formulaire complet + tags à la volée
- [x] **[P5-5]** Liste des années
- [x] **[P5-6]** Configuration - onglets + édition inline

#### Phase 6 - Polish MVP ✅
- [x] **[P6-1]** Pages d'erreur HTML (404, 403, 500) - API conserve du JSON
- [x] **[P6-2]** Healthchecks Docker (`api` + `db`)
- [x] **[P6-3]** Validation année : 404 si aucun document
- [x] **[P6-4]** Retour contextuel depuis l'édition (`?back=`)
- [x] **[P6-5]** Vue `/documents` - filtre sans tags / sans correspondant
- [x] **[P6-6]** `README.md` + `CHANGELOG.md`

---

## Roadmap

---

### ✅ Terminé - v0.2.0

#### Modèle de données
- [x] **[V2-1]** Ajout du champ `category` enum (`depense | recette | autre`) sur `documents`
- [x] **[V2-2]** Migration Alembic - valeur par défaut `autre` pour les documents existants
- [x] **[V2-3]** Mise à jour des schémas Pydantic (`DocumentCreate`, `DocumentUpdate`, `DocumentResponse`)
- [x] **[V2-4]** Mise à jour du filtre `list_documents` pour accepter `category`

#### Formulaire d'édition
- [x] **[V2-5]** Sélecteur de catégorie en haut du formulaire - 3 boutons radio stylisés (Dépense / Recette / Autre)
- [x] **[V2-6]** Masquage de la section montants (HT / TVA / TTC) quand `category = autre` via Alpine.js `x-show`
- [x] **[V2-7]** Masquage de la date de paiement quand `category = autre`

#### Vue année
- [x] **[V2-9]** Remplacement du tableau unique par 3 sections distinctes : Dépenses / Recettes / Autres
- [x] **[V2-10]** Chaque section n'est affichée que si elle contient au moins un document
- [x] **[V2-11]** Chaque section affiche son propre total TTC
- [x] **[V2-12]** Header de section avec compteur de documents et total TTC
- [x] **[V2-15b]** Largeurs de colonnes fixes (`<colgroup>` + `table-fixed`) + scroll horizontal

#### Dashboard
- [x] **[V2-14]** Stats dépenses TTC / recettes TTC / solde net de l'année
- [x] **[V2-15]** Indicateur solde net coloré (vert / rouge)
- [x] **[V2-16]** Documents récents : badge de catégorie sur chaque ligne

---

### ✅ Terminé - v0.3.0

> Objectif : gestion multi-devises complète avec équivalents EUR.

- [x] **[V3-11]** Sélecteur de devise (`<select>`) - 6 devises principales (EUR/USD/GBP/CHF/JPY/CAD)
- [x] **[V3-12]** Champ `amount_ttc_eur` - équivalent TTC en EUR saisi par l'utilisateur, pré-rempli automatiquement via l'API BCE (taux historique à la date de paiement, sinon date du jour) ; se vide si la devise change ou si la catégorie passe en "Autre"
- [x] **[V3-13]** Totaux EUR uniquement - dashboard, vue année et liste des années n'agrègent que les équivalents EUR (champ `amount_ttc_eur` pour les devises étrangères, `amount_ttc` pour EUR)
- [x] **[V3-14]** Alerte bandeau ambre dans la vue année si des documents en devise étrangère sont sans équivalent EUR renseigné (exclus des totaux)
- [x] **[V3-15]** Affichage EUR dans les tableaux - dashboard, vue année et tous les documents affichent le montant EUR avec la valeur originale en sous-titre grisé

---

### v0.4 - Analytics & Export

> Objectif : transformer les données saisies en insights comptables utiles.

#### Dashboard enrichi
- [ ] **[V4-1]** Graphique évolution mensuelle dépenses vs recettes (Chart.js, barres groupées)
- [ ] **[V4-2]** Répartition des dépenses par type de document (camembert)
- [ ] **[V4-3]** Top 5 correspondants par volume facturé (barres horizontales)
- [ ] **[V4-4]** Comparaison année N vs N-1 (variation en %)
- [ ] **[V4-5]** Indicateurs TVA : total TVA déductible (dépenses) / TVA collectée (recettes)

#### Page Rapports (`/reports`)
- [ ] **[V4-6]** Bilan annuel - tableau HT / TVA / TTC par catégorie et par type
- [ ] **[V4-7]** Bilan par correspondant - total facturé sur une période
- [ ] **[V4-8]** Filtre par période (mois, trimestre, année fiscale personnalisée)
- [ ] **[V4-9]** Export CSV - liste des documents avec toutes les métadonnées
- [ ] **[V4-10]** Export CSV - bilan comptable agrégé (HT/TVA/TTC par catégorie)
- [ ] **[V4-11]** Export PDF du rapport (WeasyPrint)

---

### v0.5 - Recherche & Organisation avancée

> Objectif : retrouver n'importe quel document en quelques secondes.

#### Recherche
- [ ] **[V5-1]** Recherche full-text dans le contenu OCR (PostgreSQL `tsvector`)
- [ ] **[V5-2]** Barre de recherche globale dans la navbar (toutes années, toutes catégories)
- [ ] **[V5-3]** Highlight des termes trouvés dans les résultats
- [ ] **[V5-4]** Recherche par montant (ex : "entre 100 et 500 €")
- [ ] **[V5-5]** Recherche par plage de dates

#### Organisation
- [ ] **[V5-6]** Archivage de documents (soft delete - masqués mais conservés)
- [ ] **[V5-7]** Documents liés (ex : facture → avoir, facture → paiement)
- [ ] **[V5-8]** Notes en Markdown avec preview
- [ ] **[V5-9]** Pièces jointes multiples par document
- [ ] **[V5-10]** Pagination sur les listes (au-delà de 100 documents)
- [ ] **[V5-11]** Tri personnalisable sur les colonnes des tableaux (date, montant, correspondant)

---

### v0.6 - Notifications & Workflow

> Objectif : ne plus rater une échéance ou un document à traiter.

#### Notifications
- [ ] **[V6-1]** Centre de notifications in-app (cloche navbar, badge rouge)
- [ ] **[V6-2]** Rappel de paiement - alerte J-3 avant `payment_date` sur les dépenses
- [ ] **[V6-3]** Alerte documents importés non complétés (sans catégorie, sans correspondant, sans montant)
- [ ] **[V6-4]** Historique des notifications (lu / non lu)

#### Workflow
- [ ] **[V6-5]** Statut de document : `brouillon → à valider → validé`
- [ ] **[V6-6]** Page "À traiter" - file des documents importés sans métadonnées complètes
- [ ] **[V6-7]** Mode révision rapide : navigation clavier entre documents à traiter (J/K + S pour sauvegarder)
- [ ] **[V6-8]** Commentaires internes sur un document
- [ ] **[V6-9]** Log d'activité par document (qui a modifié quoi et quand)

---

### v0.7 - Profil & Authentification

> Objectif : sécuriser l'accès et personnaliser l'expérience.

#### Authentification
- [ ] **[V7-1]** Page de login (email + mot de passe, local)
- [ ] **[V7-2]** Session avec cookie sécurisé (httpOnly)
- [ ] **[V7-3]** Page de changement de mot de passe
- [ ] **[V7-4]** Protection de toutes les routes (middleware auth)

#### Profil utilisateur
- [ ] **[V7-5]** Page profil (`/profile`) - nom, email, avatar
- [ ] **[V7-6]** Préférences : devise par défaut, début d'exercice fiscal
- [ ] **[V7-7]** Option multi-utilisateurs avec rôles (admin / lecteur)

---

### v1.0 - Production Ready

> Objectif : une application polie, rapide et agréable au quotidien.

#### UI / UX
- [ ] **[V8-1]** Thème sombre (toggle navbar, préférence persistée)
- [ ] **[V8-2]** Interface entièrement responsive (mobile + tablette)
- [ ] **[V8-3]** Raccourcis clavier globaux (`N` = nouveau document, `/` = recherche, `?` = aide)
- [ ] **[V8-4]** Onboarding - wizard au premier lancement
- [ ] **[V8-5]** Aide contextuelle inline (tooltips)

#### Performance
- [ ] **[V8-6]** Remplacement du CDN Tailwind par build CLI (purgé, <10 KB)
- [ ] **[V8-7]** Mise en cache des previews (ETags, Cache-Control)
- [ ] **[V8-8]** Scroll infini sur les listes longues
- [ ] **[V8-9]** Lazy loading des previews

#### Données
- [ ] **[V8-10]** Export complet backup (ZIP : documents + métadonnées JSON)
- [ ] **[V8-11]** Import depuis un backup
- [ ] **[V8-12]** Purge des previews orphelines

---

## Changelog

Voir [`CHANGELOG.md`](./CHANGELOG.md) pour le détail des versions publiées.
