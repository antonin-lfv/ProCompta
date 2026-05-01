#!/usr/bin/env bash
set -euo pipefail

# ── Couleurs ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${BLUE}→${NC}  $*"; }
success() { echo -e "${GREEN}✓${NC}  $*"; }
warn()    { echo -e "${YELLOW}⚠${NC}  $*"; }
die()     { echo -e "${RED}✗${NC}  $*" >&2; exit 1; }

trap '
  code=$?
  [ $code -ne 0 ] && echo -e "\n${YELLOW}⚠${NC}  Une erreur est survenue. Pas besoin de relancer ${BOLD}git clone${NC} - corrigez le problème puis relancez simplement : ${BOLD}./setup.sh${NC}"
' EXIT

echo ""
echo -e "${BOLD}ProCompta - Installation${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Prérequis ─────────────────────────────────────────────────────────────────
info "Vérification des prérequis..."

command -v docker >/dev/null 2>&1 \
  || die "Docker n'est pas installé. → https://docs.docker.com/get-docker/"

docker info >/dev/null 2>&1 \
  || die "Le daemon Docker n'est pas démarré. Lance Docker Desktop puis relance ce script."

[ -f "docker-compose.yml" ] \
  || die "Lance ce script depuis la racine du projet ProCompta."

success "Docker opérationnel."

# ── .env ──────────────────────────────────────────────────────────────────────
if [ -f ".env" ]; then
  warn ".env existe déjà - conservé tel quel."
  warn "Supprime-le manuellement si tu veux repartir de zéro."
else
  echo ""
  echo -e "${BOLD}Création du compte administrateur${NC}"
  echo ""

  read -r  -p "  Dénomination    : " ADMIN_NAME
  read -r  -p "  E-mail          : " ADMIN_EMAIL

  while true; do
    read -r -s -p "  Mot de passe    : " ADMIN_PASSWORD; echo ""
    read -r -s -p "  Confirmer       : " ADMIN_PASSWORD2; echo ""
    [ "$ADMIN_PASSWORD" = "$ADMIN_PASSWORD2" ] && break
    warn "Les mots de passe ne correspondent pas, réessaie."
  done

  # Génération automatique des secrets
  SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null \
    || openssl rand -hex 32)
  PG_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))" 2>/dev/null \
    || openssl rand -base64 12 | tr -d '\n/')

  cat > .env <<EOF
# PostgreSQL
POSTGRES_USER=procompta
POSTGRES_PASSWORD=${PG_PASSWORD}
POSTGRES_DB=procompta
POSTGRES_HOST=db
POSTGRES_PORT=5432

# API
API_PORT=8001
DATABASE_URL=postgresql+asyncpg://procompta:${PG_PASSWORD}@db:5432/procompta

# Storage
STORAGE_PATH=$(pwd)/storage

# Auth
SECRET_KEY=${SECRET_KEY}
ADMIN_NAME=${ADMIN_NAME}
ADMIN_EMAIL=${ADMIN_EMAIL}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
EOF

  success ".env créé (SECRET_KEY et mot de passe Postgres générés automatiquement)."
fi

# ── Dossiers ──────────────────────────────────────────────────────────────────
info "Création des dossiers de stockage..."
mkdir -p storage/previews backups
success "storage/  et  backups/  prêts."

# ── /etc/hosts ────────────────────────────────────────────────────────────────
echo ""
if grep -q "procompta.local" /etc/hosts 2>/dev/null; then
  success "procompta.local déjà présent dans /etc/hosts."
else
  warn "Pour accéder à l'app via http://procompta.local, une ligne doit être ajoutée à /etc/hosts (nécessite sudo)."
  read -r -p "  Autoriser ? [O/n] : " HOSTS_CONFIRM
  if [[ "$HOSTS_CONFIRM" != "n" && "$HOSTS_CONFIRM" != "N" ]]; then
    sudo sh -c 'echo "127.0.0.1 procompta.local" >> /etc/hosts'
    success "procompta.local ajouté dans /etc/hosts."
    USE_LOCAL_DOMAIN=true
  else
    warn "Domaine local ignoré. L'app sera accessible sur http://localhost:8000."
    USE_LOCAL_DOMAIN=false
  fi
fi

# ── Build + démarrage ─────────────────────────────────────────────────────────
echo ""
info "Build et démarrage des services (première fois : quelques minutes)..."
docker compose up --build -d

# ── Attente démarrage API ─────────────────────────────────────────────────────
API_PORT_VALUE=$(grep "^API_PORT=" .env | cut -d= -f2)
API_PORT_VALUE=${API_PORT_VALUE:-8001}

info "Attente du démarrage de l'API (port ${API_PORT_VALUE})..."
MAX_ATTEMPTS=60
attempt=0
until curl -sf "http://localhost:${API_PORT_VALUE}/health" >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  [ $attempt -ge $MAX_ATTEMPTS ] \
    && die "L'API n'a pas démarré. Consulte les logs : docker compose logs api"
  sleep 3
done
success "API opérationnelle."

# ── Résumé ────────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "  ${GREEN}${BOLD}ProCompta est prêt !${NC}"
echo ""

if grep -q "procompta.local" /etc/hosts 2>/dev/null; then
  echo -e "  ${BOLD}URL   →  http://procompta.local${NC}"
else
  echo -e "  ${BOLD}URL   →  http://localhost:${API_PORT_VALUE}${NC}"
fi

SAVED_EMAIL=$(grep "^ADMIN_EMAIL=" .env | cut -d= -f2)
echo -e "  Email →  ${SAVED_EMAIL}"
echo ""
echo -e "  Astuce : appuie sur ${BOLD}?${NC} dans l'app pour voir les raccourcis clavier."
echo ""
