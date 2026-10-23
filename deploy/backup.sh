#!/bin/sh
# Backup do imob-site: dump do Postgres + fotos (volume imob_media).
# Uso: deploy/backup.sh [pasta-destino]   (padrão: /opt/backups)
# Mantém os últimos 14 dias na VPS. Com BACKUP_REMOTE definido, também envia via rclone.
set -eu

DEST="${1:-/opt/backups}"
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$DEST"
cd "$APP_DIR"

# -T: sem terminal (necessário no cron). Escreve em .tmp e só renomeia se der certo.
docker compose exec -T db pg_dump -U imob --no-owner imob | gzip > "$DEST/db-$STAMP.sql.gz.tmp"
mv "$DEST/db-$STAMP.sql.gz.tmp" "$DEST/db-$STAMP.sql.gz"

docker run --rm -v imob_media:/media:ro -v "$DEST":/backup alpine \
    tar czf "/backup/media-$STAMP.tar.gz" -C /media .

find "$DEST" -name 'db-*.sql.gz' -mtime +14 -delete
find "$DEST" -name 'media-*.tar.gz' -mtime +14 -delete
echo "backup ok: $DEST/db-$STAMP.sql.gz e media-$STAMP.tar.gz"

# Cópia fora da VPS (opcional): BACKUP_REMOTE=r2crypt: (remoto rclone criptografado).
# Envia só os arquivos desta rodada e mantém 30 dias no destino.
if [ -n "${BACKUP_REMOTE:-}" ]; then
    rclone copy "$DEST" "$BACKUP_REMOTE" --include "*-$STAMP.*"
    rclone delete "$BACKUP_REMOTE" --min-age 30d
    echo "enviado para $BACKUP_REMOTE"
fi
