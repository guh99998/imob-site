#!/bin/sh
# Backup do MoneyPilot: dump do Postgres (formato custom, restaurável com pg_restore).
# Uso: deploy/backup-moneypilot.sh [pasta-destino]   (padrão: /opt/backups)
# Roda na VPS, em /opt/moneypilot. Mantém os últimos 14 dias na VPS.
# Com BACKUP_REMOTE definido, também envia via rclone (mesmo remoto do backup.sh).
set -eu

DEST="${1:-/opt/backups}"
APP_DIR="${MONEYPILOT_DIR:-/opt/moneypilot}"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$DEST"
cd "$APP_DIR"

# -T: sem terminal (necessário no cron). Usuário e banco vêm do ambiente do container.
# Escreve em .tmp e só renomeia se der certo.
docker compose -f docker-compose.prod.yml exec -T db \
    sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl -Fc' \
    > "$DEST/mp-db-$STAMP.dump.tmp"
mv "$DEST/mp-db-$STAMP.dump.tmp" "$DEST/mp-db-$STAMP.dump"

find "$DEST" -name 'mp-db-*.dump' -mtime +14 -delete
echo "backup ok: $DEST/mp-db-$STAMP.dump"

# Cópia fora da VPS (opcional): BACKUP_REMOTE=r2crypt: (remoto rclone criptografado).
if [ -n "${BACKUP_REMOTE:-}" ]; then
    rclone copy "$DEST" "$BACKUP_REMOTE" --include "mp-db-$STAMP.*"
    echo "enviado para $BACKUP_REMOTE"
fi
