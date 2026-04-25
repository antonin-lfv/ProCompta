# ProCompta - Suivi des tâches

## Version courante : `v0.6.0` ✅

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

### ✅ Terminé - v0.4.0

> Objectif : transformer les données saisies en insights comptables utiles.

#### Dashboard enrichi
- [x] **[V4-1]** Graphique évolution mensuelle dépenses vs recettes (Chart.js, barres groupées)
- [x] **[V4-2]** Répartition des dépenses par type de document (doughnut)
- [x] **[V4-3]** Top 5 correspondants par volume facturé (barres horizontales)
- [x] **[V4-4]** Comparaison année N vs N-1 (variation en %) sur dépenses, recettes et solde
- [x] **[V4-5]** Indicateurs TVA : total TVA déductible (dépenses) / TVA collectée (recettes)

#### Page Rapports (`/reports`)
- [x] **[V4-6]** Bilan annuel - tableau HT / TVA / TTC par catégorie et par type, avec totaux par section et solde global
- [x] **[V4-7]** Bilan par correspondant - dépenses TTC / TVA déductible, recettes TTC / TVA collectée, solde
- [x] **[V4-9]** Export CSV - liste des documents avec toutes les métadonnées
- [x] **[V4-10]** Export CSV - bilan comptable agrégé (HT/TVA/TTC par catégorie × type × correspondant)

---

### ✅ Terminé - v0.5.0

> Objectif : retrouver n'importe quel document en quelques secondes.

- [x] **[V5-2]** Barre de recherche globale dans la navbar (toutes années, toutes catégories)
- [x] **[V5-3]** Highlight des termes trouvés dans les résultats
- [x] **[V5-4]** Recherche par montant (entre X et Y €) - vue année + tous les documents
- [x] **[V5-5]** Recherche par plage de dates - vue année + tous les documents
- [x] **[V5-6]** Archivage de documents (soft delete) - bouton dans l'édition, section dédiée dans la vue année, exclus de tous les totaux
- [x] **[V5-10]** Pagination sur la liste de tous les documents (50 par page)
- [x] **[V5-11]** Tri personnalisable sur les colonnes des tableaux (date, montant, correspondant, titre)
- [x] **[Bonus]** Aperçu modal sur chaque ligne de tableau (œil → fond flouté, infos + preview)
- [x] **[Bonus]** Limite 250 caractères sur les notes (compteur en temps réel)

---

### ✅ Terminé - v0.6.0

> Objectif : ne plus rater un document à traiter.

#### Notifications
- [x] **[V6-1]** Centre de notifications in-app (cloche navbar, badge rouge, dropdown 5 dernières)
- [x] **[V6-3]** Alerte documents importés non complétés - créée à l'upload, réactivée si le doc redevient incomplet, résolue automatiquement quand complété
- [x] **[V6-4]** Historique des notifications (`/notifications`) - lu/non lu, marquer non lu, supprimer, sync bidirectionnelle navbar ↔ page
- ~~**[V6-2]**~~ Rappel de paiement - écarté (non pertinent)

#### Workflow
- ~~**[V6-5]**~~ Statut de document - écarté (non pertinent pour usage solo)
- ~~**[V6-6]**~~ Page "À traiter" - écartée (non pertinent pour usage solo)
- ~~**[V6-7]**~~ Mode révision rapide - écarté (non pertinent pour usage solo)
- ~~**[V6-8]**~~ Commentaires internes - écarté (redondant avec le champ notes)
- [x] **[V6-9]** Log d'activité par document - timeline dans un drawer latéral (upload, titre, correspondant, type, catégorie, montant, date, notes, archivage)

---

### ✅ Terminé - v0.7.0

> Objectif : sécuriser l'accès et personnaliser l'expérience.

#### Authentification
- [x] **[V7-1]** Page de login (email + mot de passe, local)
- [x] **[V7-2]** Session avec cookie sécurisé (httpOnly, 30 jours, signé HMAC)
- [x] **[V7-3]** Page de changement de mot de passe (ancien / nouveau / confirmation)
- [x] **[V7-4]** Protection de toutes les routes (middleware — pages → redirect /login, API → 401 JSON)

#### Profil utilisateur
- [x] **[V7-5]** Page profil (`/profile`) — nom, email, déconnexion
- [x] **[V7-6]** Préférences : devise par défaut, premier mois de l'exercice fiscal
- ~~**[V7-7]**~~ Multi-utilisateurs — écarté (usage solo)

#### Backup
- [x] **[V7-8]** Bouton "Télécharger un backup" dans la page profil — `GET /api/backup/download`, téléchargement direct du zip dans le navigateur
- [x] **[V7-9]** Import backup — mot de passe requis, avertissement irréversible, restaure DB + storage, redirige vers /login

#### Infrastructure
- [x] **[V7-10]** Reverse proxy Caddy — domaine local `http://procompta.local` (port 80), entrée `/etc/hosts` one-shot

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
