<h1 align="center">
  <br>
  ProCompta - Logiciel de suivi de comptabilité
  <br>
</h1>

<h4 align="center">Gestionnaire de documents comptables, local, sans abonnement, sans cloud.</h4>

<p align="center">
  <img src="https://img.shields.io/badge/Version-1.0.0-green.svg" alt="Version">
  <img src="https://img.shields.io/badge/Python-3.13+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/PostgreSQL-16-orange.svg" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Docker-ready-2496ED.svg" alt="Docker">
</p>

<p align="center">
  Organisez vos factures, relevés et reçus par année, correspondant et catégorie.<br>
  Suivez vos dépenses et recettes, exportez vos bilans, gérez vos devises étrangères.
</p>

<p align="center">
  <a href="#-installation">Installation</a> •
  <a href="#-utilisation-quotidienne">Utilisation quotidienne</a> •
  <a href="#-fonctionnalités">Fonctionnalités</a> •
  <a href="#️-raccourcis-clavier">Raccourcis clavier</a> •
  <a href="#️-stack">Stack</a>
</p>

---

## 🚀 Installation

```bash
git clone https://github.com/antonin-lfv/ProCompta.git
cd ProCompta
chmod +x setup.sh
./setup.sh
```

Le script s'occupe de tout :

- vérifie que Docker est installé et démarré
- demande le prénom, e-mail et mot de passe
- génère automatiquement `SECRET_KEY` et le mot de passe PostgreSQL
- crée les dossiers `storage/` et `backups/`
- configure le domaine local `http://procompta.local` (optionnel, nécessite sudo)
- build les images Docker et applique les migrations

À la fin, l'URL et les identifiants s'affichent dans le terminal.

---

## 📅 Utilisation quotidienne

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

## ✨ Fonctionnalités

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

## ⌨️ Raccourcis clavier

| Touche | Action |
|--------|--------|
| `/` | Focus la barre de recherche |
| `N` | Nouveau document (import fichier) |
| `?` | Afficher l'aide des raccourcis |
| `Esc` | Fermer les modales |

---

## 🛠️ Stack

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
