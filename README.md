<h1 align="center">
  <br>
  ProCompta
  <br>
</h1>

<h4 align="center">Gestionnaire de documents comptables · local · sans abonnement · sans cloud.</h4>

<p align="center">
  <img src="https://img.shields.io/badge/Version-1.3.0-green.svg" alt="Version">
  <img src="https://img.shields.io/badge/Python-3.13+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/PostgreSQL-16-orange.svg" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Docker-ready-2496ED.svg" alt="Docker">
</p>

<p align="center">
  <a href="#-à-quoi-ça-sert">À quoi ça sert</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-utilisation-au-quotidien">Utilisation</a> •
  <a href="#️-raccourcis-clavier">Raccourcis</a> •
  <a href="#-fonctionnalités">Fonctionnalités</a> •
  <a href="#️-stack">Stack</a>
</p>

## Aperçu

<p align="center">
<img width="1624" height="1062" alt="main_page" src="https://github.com/user-attachments/assets/b4957d8f-c601-4096-aab9-f4f27d76961d" />
</p>

---

## À quoi ça sert

ProCompta est un logiciel **auto-hébergé** pour gérer vos documents comptables (factures, relevés, contrats, bulletins de salaire…). Tout tourne en local sur votre machine via Docker — vos fichiers ne quittent jamais votre ordinateur.

Il s'adresse aux **indépendants, micro-entrepreneurs et petites structures** qui veulent un outil simple pour :

- centraliser leurs documents sans dépendre d'un service cloud
- suivre leurs dépenses et recettes par année
- garder une trace de leurs correspondants (fournisseurs, clients, banques)
- générer des bilans et rapports de TVA sans logiciel de comptabilité lourd

---

## 🚀 Installation

**Prérequis : Docker Desktop installé et démarré.**

```bash
git clone https://github.com/antonin-lfv/ProCompta.git
cd ProCompta
chmod +x setup.sh
./setup.sh
```

Le script fait tout automatiquement :

1. Vérifie que Docker est disponible
2. Demande votre prénom, e-mail et mot de passe
3. Génère une `SECRET_KEY` et un mot de passe PostgreSQL aléatoires
4. Crée les dossiers `storage/` (documents) et `backups/`
5. Propose de configurer le domaine local `http://procompta.local` (optionnel — nécessite sudo)
6. Construit les images Docker et applique les migrations de base de données

À la fin, l'URL et vos identifiants s'affichent dans le terminal.

> **Mise à jour** : `git pull && docker compose up --build -d`

---

## 📋 Utilisation au quotidien

### Ajouter un document

Cliquez sur **Nouveau** (ou appuyez sur `N`), puis glissez-déposez un fichier PDF, JPEG ou PNG.

ProCompta détecte automatiquement :
- **La date** du document (depuis les métadonnées PDF)
- **Le correspondant** (en cherchant son nom dans le texte du document)
- **Le type de document** (facture, devis, contrat… en français et en anglais)

Pour les images, une analyse OCR est effectuée automatiquement.

Vous pouvez ensuite compléter les informations manuellement : montant HT/TVA/TTC, devise, catégorie (dépense / recette / autre), tags.

### Importer plusieurs fichiers d'un coup

Utilisez l'import par lot (bouton **Importer**) pour uploader plusieurs fichiers en une seule fois. Chaque fichier est traité indépendamment — les doublons sont détectés automatiquement.

### Naviguer dans vos documents

- **Tableau de bord** : vue d'ensemble de l'année en cours — totaux dépenses/recettes, documents récents, alertes documents incomplets
- **Vue par année** : tous les documents d'une année, avec filtres et tri
- **Tous les documents** : vue globale avec recherche, filtres par correspondant / type / tags / catégorie

### Suivre les finances

Chaque document peut avoir :
- Un montant HT, un taux de TVA (calculé automatiquement), un montant TTC
- Une devise étrangère — conversion automatique vers € via les taux BCE à la date du document

### Rapports

La page **Rapports** affiche pour l'année sélectionnée :
- Bilan mensuel (dépenses vs recettes)
- Répartition par type de document
- **TVA trimestrielle** : base HT, TVA déductible (dépenses), TVA collectée (recettes), solde net par trimestre
- Export CSV du bilan et de la liste des documents

### Actions groupées

Sélectionnez plusieurs documents dans le tableau (cases à cocher) pour les **archiver**, **désarchiver** ou **supprimer** en une seule action.

### Sauvegarder et restaurer

Page **Profil** → section Backup :
- **Télécharger** : génère un ZIP contenant le dump SQL et tous vos fichiers
- **Restaurer** : importe un ZIP de backup (confirmation par mot de passe requise)

---

## ⌨️ Raccourcis clavier

| Touche | Action |
|--------|--------|
| `/` | Focus la barre de recherche |
| `N` | Nouveau document |
| `?` | Afficher l'aide des raccourcis |
| `Esc` | Fermer les modales |

---

## ✨ Fonctionnalités

| Catégorie | Détail |
|-----------|--------|
| **Import** | PDF / JPEG / PNG, import unitaire ou par lot, détection de doublons (hash SHA-256) |
| **Auto-détection** | Date PDF, correspondant et type extraits du contenu (OCR pour les images) |
| **Organisation** | Correspondants, types de document (12 par défaut), tags colorés (5 par défaut), catégories |
| **Finances** | Montants HT / TVA / TTC, 6 devises, conversion BCE automatique à la date du document |
| **Vues** | Tableau de bord, vue par année, tous les documents, rapports trimestriels TVA |
| **Recherche** | Recherche par titre, filtres multiples (date, montant, correspondant, type, tags), tri des colonnes |
| **Actions groupées** | Sélection multiple, archivage / désarchivage / suppression en lot |
| **Exports** | CSV bilan comptable, CSV TVA trimestrielle, CSV liste des documents |
| **Workflow** | Archivage, journal d'activité par document, notifications documents incomplets |
| **Sécurité** | Authentification e-mail + mot de passe, session 30 jours (HMAC signé) |
| **Backup** | Export ZIP (dump SQL + fichiers), restauration avec confirmation par mot de passe |
| **Ergonomie** | Raccourcis clavier, tooltips, preview intégrée, responsive |

---

## 🛠️ Stack

| Couche | Technologie |
|--------|-------------|
| Backend | Python 3.13, FastAPI, SQLAlchemy async |
| Base de données | PostgreSQL 16 |
| Migrations | Alembic |
| Frontend | Jinja2, Tailwind CSS 3 (build CLI), Alpine.js |
| Previews & OCR | pdf2image + Poppler, Pillow, Tesseract (fra + eng) |
| Packaging | uv |
| Reverse proxy | Caddy |
| Infrastructure | Docker Compose |
