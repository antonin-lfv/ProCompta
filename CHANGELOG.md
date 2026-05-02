# Changelog

## [1.5.1] - 2026-05-02

### Corrigé - Gmail OAuth & import

- **Erreur 422 sur `/api/gmail/sync`** — le paramètre `request` n'était pas typé `Request`, FastAPI le traitait comme un body requis ; annotation corrigée
- **PKCE manquant au callback OAuth** — `requests-oauthlib` ≥ 2.0 ajoute automatiquement le `code_challenge` à l'URL d'autorisation ; le `code_verifier` est maintenant généré dans `oauth_start`, stocké en base (`gmail_code_verifier`) et transmis à `flow.fetch_token()` dans `oauth_callback`
- **URI de redirection invalide** — Google refuse les TLD `.local` ; l'URI est maintenant codée en dur en `http://localhost:{api_port}/api/gmail/oauth/callback`
- **"0 importé" après suppression d'un document** — la requête `already_imported` rejoignait la table `Document` : un message dont le document a été supprimé n'est plus considéré comme déjà importé
- **`UniqueViolationError` lors du ré-import** — la contrainte UNIQUE sur `gmail_import_log.gmail_message_id` a été supprimée (migration `0015`) pour autoriser plusieurs logs par message
- **Credentials Gmail persistants après déconnexion** — suppression du fallback `.env` dans `resolve_credentials()` ; les identifiants ne proviennent plus que de la base de données

### Corrigé - Expérience wizard

- **"Identifiants déjà enregistrés" après enregistrement** — `saveCreds()` ne recharge plus la page ; il avance directement à l'étape 3
- **Instructions étape 1 mises à jour** — détail des 7 étapes Google Cloud Console correspondant au flux réel (projet, activation API, écran de consentement, utilisateurs test, identifiants OAuth)

### Ajouté

- **Déconnexion Gmail automatique** si l'utilisateur change son adresse e-mail dans le profil (tous les tokens et credentials Gmail sont remis à `NULL`)
- **Modales d'ajout** pour les sources Gmail et les rappels (remplacent les formulaires inline)
- **Modales d'édition** (bouton crayon) pour modifier une source Gmail ou un rappel existant
- **Bouton "Réinitialiser"** dans l'en-tête de la section Gmail pour déconnecter le compte en un clic

### Technique

- Modèle `User` : nouveau champ `gmail_code_verifier` (String 200, nullable) — migration `0014`
- `config.py` : suppression des champs `gmail_client_id/secret/refresh_token` et de la propriété `gmail_configured`
- `.env` / `.env.example` : suppression des variables Gmail OAuth (configuration exclusivement via l'assistant)

---

## [1.5.0] - 2026-05-02

### Ajouté - Import automatique Gmail
- **Sources Gmail configurables** (`gmail_sources`) - nom, expéditeur, filtre sujet, filtre pièce jointe, correspondant et type de document pré-assignés
- **Import de factures PDF** - récupération via l'API Gmail OAuth2 (lecture seule), déduplication par hash SHA-256 et par `gmail_message_id`
- **Log d'import** (`gmail_import_log`) - traçabilité de chaque message traité (importé / ignoré / erreur)
- **Boutons Sync** dans la page Configuration → onglet Gmail : synchroniser une source individuelle ou toutes les sources actives en un clic
- **Alerte "jamais synchronisé"** affichée pour chaque source sans `last_synced_at`

### Ajouté - Système de rappels
- **Table `reminders`** - nom, description, fréquence (en jours), prochaine échéance, notifications email et in-app, actif/inactif
- **Boucle asyncio quotidienne** déclenchant automatiquement les rappels échus au démarrage et toutes les 24h
- **Notification in-app** via le système existant (nouveau type `reminder_due`)
- **Email de rappel** via SMTP (gmail app password) envoyé à l'adresse admin
- **Bouton "Déclencher maintenant"** pour tester un rappel manuellement
- **Badges visuels** "En retard" (rouge) et "Bientôt" (orange) sur les rappels à échéance dans les 7 jours

### Technique
- Nouveaux modèles : `GmailSource`, `GmailImportLog`, `Reminder`
- Nouveaux services : `gmail_service.py` (Google API), `smtp_service.py` (envoi email)
- Nouveaux routers : `gmail.py`, `reminders.py`
- `config.py` étendu avec `gmail_client_id`, `gmail_client_secret`, `gmail_refresh_token`, `smtp_host/port/user/password`
- Dépendances ajoutées : `google-api-python-client`, `google-auth-httplib2`, `google-auth-oauthlib`
- Migration `20260502_0011` : tables `gmail_sources`, `gmail_import_log`, `reminders` + valeur `reminder_due` dans `notificationtypeenum`

---

## [1.4.0] - 2026-05-01

### Corrigé - Bugs comptables
- **`vat_rate=0` écrasé à 20 à la sauvegarde** - le champ Taux TVA affichait 20 même quand la valeur stockée était 0, causant une corruption silencieuse des données à chaque sauvegarde sans modification du champ ; la condition `!= 0` a été supprimée de la logique d'affichage. Le modèle `vat_rate` n'a plus de valeur Python par défaut (était `Decimal("0.00")`) : les nouveaux documents ont `vat_rate=NULL` et affichent 20 comme suggestion, les documents existants avec 0% TVA affichent 0.
- **Faux positif alerte devise étrangère** - `has_foreign_currency` utilisait `not d.amount_ttc_eur` au lieu de `d.amount_ttc_eur is None`, déclenchant le bandeau "montant EUR manquant" pour les documents avec un équivalent EUR égal à zéro
- **`prorata_pct` non borné** - aucune validation n'empêchait de stocker un prorata > 100% ou < 0% ; validation ajoutée côté Pydantic (schémas `DocumentCreate` et `DocumentUpdate`) et côté form POST (clamp 0–100)

### Corrigé - Bugs fonctionnels
- **Suppression groupée sans confirmation** - `bulkDelete()` supprimait les documents sélectionnés sans demander de confirmation ; `confirm()` ajouté avec le nombre de documents concernés
- **`tag_uuids` UUID malformé → HTTP 500** - le formulaire d'édition levait `ValueError` non capturé sur un UUID invalide dans `tag_ids` ; remplacé par `_uuid()` qui retourne `None` silencieusement
- **Erreurs silencieuses dans la configuration** - la création d'un correspondant, type ou tag en doublon (slug/nom) redirige désormais avec `?error=duplicate` et affiche un message d'erreur visible
- **`createTag()` sans feedback** - la création rapide d'un tag depuis le formulaire d'édition n'affichait rien en cas d'erreur (doublon, réseau) ; un `alert()` est maintenant déclenché

### Corrigé - Bugs visuels
- **`has_filters` incomplet** - les filtres `no_type`, `no_correspondent` et `show_archived` n'activaient pas l'indicateur visuel de filtre sur la vue "Tous les documents"
- **`data-amount` avec `amount_ttc_eur=0`** - les stats de section recalculées après suppression DOM utilisaient `not doc.amount_ttc_eur` (falsy pour 0), entraînant un total affiché incorrect pour les documents multi-devises avec un équivalent EUR de zéro

### Sécurité
- **Zip Slip dans la restauration backup** - une archive malveillante contenant des chemins avec `../` pouvait écraser des fichiers hors du répertoire de stockage ; `target.resolve().relative_to(storage.resolve())` valide maintenant le chemin avant extraction
- **Fuite mémoire `_LOGIN_ATTEMPTS`** - le dictionnaire de rate limiting utilisait `defaultdict(list)` et créait une entrée pour chaque IP accédant au login ; migré vers un `dict` standard avec nettoyage paresseux des entrées expirées

### Technique
- `@app.on_event("startup")` déprécié → migré vers `@asynccontextmanager lifespan`
- `_is_complete`, `_missing_body`, `_sync_notification` dupliqués dans `documents.py` et `pages.py` → centralisés dans `app/document_utils.py`
- `file_path` supprimé de `DocumentResponse` (chemin interne du système de fichiers inutile côté client)

---

## [1.3.8] - 2026-05-01

### Ajouté
- **Prorata déductible** - champ `prorata_pct` (%) sur les dépenses uniquement : saisie dans le formulaire d'édition (section "Prorata déductible", visible seulement pour les dépenses), facteur appliqué dans tous les calculs (dashboard, vue année, page années, bilans, rapports TVA, top correspondants, exports CSV) ; indicateur `~X%` dans les tableaux de la vue année ; sans prorata = 100% déductible (NULL en base)
- **Pagination vue année** - maximum 5 documents par section (Dépenses / Recettes / Autres / Archivés), contrôles Précédent / Suivant par section sans rechargement serveur (Alpine.js `x-show`)
- **Bouton "Tout voir"** par section - affiche tous les documents d'une catégorie sans limite, avec retour vers la vue paginée (paramètre `?category=`)
- **TVA par défaut à 20%** - champ Taux TVA pré-rempli à 20 à l'ouverture du formulaire d'édition et lors de l'import (single et batch), quelle que soit la catégorie initiale

### Modifié
- **Retour contextuel depuis l'édition** - le paramètre `?back=` encode désormais l'URL complète (filtres + catégorie + tri + ordre), Sauvegarder et Annuler ramènent exactement à la même vue filtrée
- **Tri en mode "Tout voir"** - les liens de tri préservent le paramètre `?category=` (plus de retour en vue paginée au clic)
- **Filtres en mode "Tout voir"** - le formulaire de filtres inclut un `<input type="hidden" name="category">` pour rester en mode "Tout voir" après application des filtres
- **Conversion devise sur changement de date de paiement** - la conversion BCE est re-déclenchée automatiquement dès que la date de paiement change (si devise ≠ EUR)
- **Page de recherche `/documents`** - mise en page flex avec dates en largeur fixe (`w-36`) et champs montant en `flex-1`, le bouton Réinitialiser ne compresse plus "Montant max"

### Corrigé
- **Écart visuel** - espacement équilibré (`gap-3`) entre le bouton calcul TVA et le champ Montant TVA, cohérent avec l'écart Montant TVA → Montant TTC

### Technique
- Colonne `prorata_pct NUMERIC(5,2) NULL` sur `documents` (migration `20260501_0009`)
- Valeur enum `prorata_changed` ajoutée à `activityeventenum` (migration `20260501_0010`, `ALTER TYPE … ADD VALUE IF NOT EXISTS`)
- Expression SQLAlchemy `_prorata_dep = case((depense & prorata_pct IS NOT NULL, prorata_pct/100), else_=1)` définie au niveau module, multipliée sur `_eur_amount`, `amount_ht` et `vat_amount` dans toutes les requêtes de dépenses
- Fonction Python `_eur(doc)` dans `year_view` proratise le montant pour les dépenses avec `prorata_pct` non nul
- Historique d'activité : `old_prorata` capturé avant commit, entrée `prorata_changed` avec ancien/nouveau % si modifié
- Colonne "Prorata (%)" ajoutée à l'export CSV documents

---

## [1.3.0] - 2026-04-27

### Ajouté
- **TVA trimestrielle** - nouvelle section dans `/reports` affichant T1→T4 : Base HT dépenses, TVA déductible, Base HT recettes, TVA collectée, Solde net TVA, avec ligne de total annuel
- **Export CSV TVA** - `GET /reports/export/tva?year=` dédié avec colonnes par trimestre + ligne de total

### Technique
- Query SQLAlchemy groupée par trimestre (`extract("quarter", ...)`) pour agréger HT et TVA par catégorie
- Données TVA toujours calculées sur l'année complète (indépendant du filtre `?quarter=` de la page)

---

## [1.2.0] - 2026-04-27

### Ajouté
- **Sélection groupée** - colonne checkbox dans tous les tableaux (vue année + vue documents), checkbox "sélectionner tout" par section
- **Barre d'actions flottante** - apparaît dès qu'un document est coché, affiche le nombre sélectionné, actions Archiver et Supprimer ; téléportée au `<body>` via `x-teleport`
- **Archivage groupé** - `POST /api/documents/bulk-archive` : archive tous les documents sélectionnés, log d'activité et sync notifications
- **Suppression groupée** - `POST /api/documents/bulk-delete` : modale de confirmation, supprime les fichiers physiques et previews, met à jour les compteurs de section
- Désélection automatique après action ; sélection nettoyée sur suppression individuelle via événement `doc-deleted`

### Technique
- `BulkActionRequest` - nouveau schéma Pydantic `{ ids: list[uuid] }`
- `yearData()` étendu avec `selectedIds[]`, `toggleSelect`, `toggleSelectAll`, `areAllSelected`, `clearSelection`, `bulkArchive`, `bulkDelete`
- `docsData()` - nouveau composant Alpine sur `/documents` unifiant `showFilters` et la sélection groupée

---

## [1.1.0] - 2026-04-26

### Ajouté
- **Import batch - modale carousel** - sélection multiple de fichiers (PDF, JPEG, PNG) ; modale plein-écran téléportée au `<body>` (`x-teleport`) pour éviter tout conflit de stacking context ; un fichier à la fois avec barre de progression carousel
- **Preview dans le carousel** - images rendues via FileReader (data URL), PDFs via `URL.createObjectURL` + `<embed>` natif ; nettoyage automatique des object URLs à la fermeture
- **Formulaire complet par fichier** - titre, date document, catégorie (Dépense / Recette / Autre), correspondant, type de document, tags, montants (HT / TVA / TTC / devise), date de paiement
- **Conversion BCE intégrée dans le batch** - bouton rotatif à côté du champ "Équivalent EUR", taux historique BCE à la date de paiement (ou du jour) ; nouvel endpoint générique `POST /api/documents/convert-currency` (sans doc ID requis)
- **Traitement séquentiel avec résumé** - upload + PATCH métadonnées pour chaque fichier, barre de progression X/N, résumé final (importés · doublons · erreurs)
- **Navigation clavier** - flèches ← → pour naviguer entre les fichiers, Échap pour fermer

### Technique
- `POST /api/documents/convert-currency` - endpoint générique acceptant `{ currency, amount, date? }` sans requérir un document existant
- Helper `_fetch_ecb_rate(currency, rate_date)` extrait et partagé entre les deux endpoints de conversion
- Objets `File` natifs stockés dans une closure non-réactive (`_rawFiles`) pour éviter que le proxy Alpine 3 ne corrompe leur réactivité
- `GenericConvertRequest` - nouveau schéma Pydantic avec champ `date` optionnel

---

## [1.0.0] - 2026-04-25

### Ajouté
- **Tooltips stylisés** - pill noire instantanée sur tous les boutons action de la page d'édition (historique, télécharger, e-mail, ouvrir, archiver/désarchiver) et sur le bouton d'import de la vue année
- **Badge raccourci** dans la barre de recherche navbar - badge `⌨ /` affiché à droite du champ, disparaît quand le champ est actif (pattern GitHub/Linear)

### Corrigé
- `GET /api/documents/{id}/file` - `Request` manquant dans les imports FastAPI (causait une erreur 422 `Field required`)
- `purge_previews` - utilisation de `.scalars().all()` plus robuste pour la requête `select(Document.id)`

---

## [0.9.0] - 2026-04-25

### Ajouté
- **ETags sur les fichiers documents** - `GET /api/documents/{id}/file` retourne un header `ETag` basé sur le hash SHA-256 du fichier ; répondavec `304 Not Modified` si le client envoie `If-None-Match` correspondant ; `Cache-Control: private, max-age=31536000, immutable`
- **Lazy loading** - attribut `loading="lazy"` sur l'image dans la modale de preview

### Technique
- **Tailwind CSS CLI** - remplacement du CDN `play.tailwindcss.com` (300+ KB, dépendance externe) par un build purgé local (~10 KB) ; binaire standalone `tailwindcss-linux-x64 v3.4.17` téléchargé dans le Dockerfile, build pendant `docker build`, servi via `/static/css/tailwind.css`
- `backend/tailwind.config.js` - scanne `./app/templates/**/*.html`, étend `fontFamily.sans` avec Inter
- `backend/app/static/css/input.css` - directives `@tailwind base/components/utilities`
- `backend/app/static/css/tailwind.css` - ignoré par git (généré au build)

---

## [0.8.0] - 2026-04-25

### Ajouté
- **Raccourcis clavier** - `/` focus la barre de recherche ; `N` ouvre le sélecteur de fichier (si sur une vue année) ou redirige vers l'année courante ; `?` affiche la modale d'aide des raccourcis ; `Esc` ferme les modales
- **Purge des previews orphelines** - bouton dans la page Profil (section Maintenance) : supprime les fichiers `previews/*.png` sans document associé en base, affiche le nombre de fichiers supprimés

### Technique
- `POST /profile/purge-previews` - scan `storage/previews/`, cross-référence avec les IDs documents en base, supprime les orphelins
- Listener `@trigger-upload.window` sur le composant Alpine de la vue année - déclenche le `<input type=file>` natif
- Script keydown global en fin de `base.html` - skip si focus sur `INPUT/TEXTAREA/SELECT` ou `contentEditable`, skip si `Ctrl/Meta/Alt`
- Modale raccourcis en `z-[70]` (au-dessus de la preview modale en `z-50`)

---

## [0.7.0] - 2026-04-25

### Ajouté
- **Authentification** - page de login (email + mot de passe), session cookie httpOnly signée HMAC (30 jours), middleware protégeant toutes les routes (pages → redirect `/login`, API → 401 JSON)
- **Compte admin** - créé automatiquement au premier démarrage depuis les variables `ADMIN_NAME` / `ADMIN_EMAIL` / `ADMIN_PASSWORD` du `.env`
- **Page Profil** (`/profile`) - modification du nom et de l'email, changement de mot de passe (ancien / nouveau / confirmation), préférences (devise par défaut, mois de début d'exercice fiscal), déconnexion
- **Backup téléchargeable** - bouton "Télécharger un backup" : génère un `.zip` (dump SQL + fichiers storage) et le télécharge directement dans le navigateur
- **Import backup** - upload d'un `.zip`, confirmation par mot de passe, avertissement irréversible, restaure DB + storage puis redirige vers `/login`
- **Nom dans la navbar** - icône profil cliquable + prénom affiché à droite, lien vers `/profile`
- **Reverse proxy Caddy** - domaine local `http://procompta.local` (port 80), entrée `/etc/hosts` one-shot

### Technique
- Modèle `User` : `name`, `email` (unique), `hashed_password` (scrypt), `default_currency`, `fiscal_year_start`, `backup_path`
- Migration Alembic `20260425_0008` - table `users`
- `AuthMiddleware` (Starlette BaseHTTPMiddleware) - vérifie le cookie `procompta_session`, charge l'user en `request.state.user`
- Tokens HMAC signés (stdlib uniquement : `hmac`, `hashlib`, `base64`, `json`) - aucune dépendance ajoutée
- Helper `render()` dans `templating.py` - injecte `current_user` dans tous les templates automatiquement
- `GET /api/backup/download` - `StreamingResponse` zip en mémoire (`io.BytesIO`)
- `POST /api/backup/restore` - reset schema public + `psql` restore + extraction storage

---

## [0.6.0] - 2026-04-25

### Ajouté
- **Centre de notifications** - cloche dans la navbar avec badge rouge (nombre non lus), dropdown des 5 dernières notifications, fermeture en cliquant ailleurs
- **Alerte documents incomplets** - notification créée automatiquement à l'upload ; réactivée si un document complet redevient incomplet (champ supprimé) ; marquée lue automatiquement dès que le document est complété
- **Page Notifications** (`/notifications`) - historique complet lu/non lu, marquer comme lu, marquer comme non lu, supprimer ; synchronisation bidirectionnelle en temps réel avec la cloche navbar (événements Alpine.js window)
- **Log d'activité** - bouton horloge dans le header de la page d'édition, ouvre un drawer latéral droit avec la timeline de toutes les modifications : upload, titre, correspondant, type, catégorie, montant + devise, date, notes, archivage/désarchivage ; icônes Heroicons par type d'événement, valeurs avant/après avec barré pour l'ancienne valeur
### Technique
- Modèle `Notification` (`notifications` table) : `type`, `document_id` (FK CASCADE), `title`, `body`, `read`
- Modèle `DocumentActivity` (`document_activity` table) : `document_id` (FK CASCADE), `event_type` (enum), `old_value`, `new_value`, `created_at` ; indexes sur `document_id` et `created_at`
- Router `/api/notifications` : `GET /`, `GET /unread-count`, `PATCH /read-all`, `PATCH /{id}/read`, `PATCH /{id}/unread`, `DELETE /{id}`
- Endpoint `GET /api/documents/{id}/activity` - retourne la liste des événements triée chronologiquement
- Migrations Alembic `20260425_0006` (notifications) et `20260425_0007` (document_activity) - pattern `DO $$ BEGIN CREATE TYPE ... EXCEPTION WHEN duplicate_object THEN NULL; END $$` pour les enums PostgreSQL
- Déduplication des notifications : réactivation de la notification existante (lue ou non lue) plutôt que création d'un doublon
- Alpine.js plain-object reactivity (`readMap`/`deletedMap`) à la place de `Set` (non intercepté par Proxy Alpine)
- Données JSON en `<script>` tag pour éviter les conflits de guillemets dans les attributs `x-data`

---

## [0.5.0] - 2026-04-25

### Ajouté
- **Recherche globale** - barre de recherche dans la navbar, redirige vers `/documents?search=…`
- **Highlight des résultats** - filtre Jinja2 `highlight` : les termes cherchés sont surlignés en jaune dans les titres
- **Tri des colonnes** - macro `sort_th` : clic sur Titre / Date / Correspondant / Montant TTC dans les tableaux, flèche d'indication, ordre persisté dans l'URL
- **Filtre par plage de dates** - champs `date_from` / `date_to` dans les formulaires de filtres (vue année + tous les documents)
- **Filtre par montant** - champs `amount_min` / `amount_max` (EUR) dans les mêmes formulaires
- **Archivage** - bouton "Archiver / Désarchiver" dans la page d'édition (PATCH JSON) ; documents archivés exclus de tous les totaux (dashboard, vue année, rapports, exports) ; section "Archivés" en bas de la vue année ; vue transversale `/documents?show_archived=1`
- **Pagination** - 50 documents par page sur `/documents`, avec contrôles prev/next + numéros, filtres et tri préservés
- **Aperçu modal** - bouton œil sur chaque ligne : overlay fond flouté, preview du fichier (iframe PDF / img), toutes les métadonnées, lien "Modifier"
- **Limite notes** - 250 caractères max sur les notes, compteur temps réel avec alerte amber à 240

### Technique
- Filtre Jinja2 `highlight(text, search)` dans `templating.py` (markupsafe, regex IGNORECASE)
- `sort_th` macro dans `macros.html` - paramètres `col`, `default_order`, `align`
- `_sort_base_url()` helper préservant tous les filtres actifs dans les URLs de tri
- Migration Alembic `20260425_0005` - colonne `archived BOOLEAN NOT NULL DEFAULT false`
- `Document.archived == False` ajouté systématiquement dans dashboard, years_list, reports, exports, available_years
- `_PAGE_SIZE = 50` dans `documents_list`, count query séparé pour la pagination

---

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
