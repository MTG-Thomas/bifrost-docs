#!/bin/bash
# Certificate Renewal Script
#
# This script renews Let's Encrypt certificates and reloads nginx.
# It should be run weekly via cron.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

LOG_FILE="/var/log/letsencrypt-renewal.log"

echo "$(date): Starting certificate renewal check..." >> "$LOG_FILE"

# Check if certbot is available
if ! command -v certbot &> /dev/null; then
    echo "$(date): ❌ certbot not found" >> "$LOG_FILE"
    exit 1
fi

# Run renewal
if certbot renew \
    --config-dir "$REPO_ROOT/certbot/conf" \
    --work-dir "$REPO_ROOT/certbot/work" \
    --logs-dir "$REPO_ROOT/certbot/logs" \
    --quiet >> "$LOG_FILE" 2>&1; then
    
    echo "$(date): ✅ Renewal check completed" >> "$LOG_FILE"
    
    # Check if certificates were renewed (files would have changed)
    CERT_PATH="$REPO_ROOT/certbot/conf/live"
    
    if [ -d "$CERT_PATH" ]; then
        for domain_dir in "$CERT_PATH"/*; do
            if [ -d "$domain_dir" ]; then
                domain=$(basename "$domain_dir")
                
                # Copy renewed certificates
                if [ -f "$domain_dir/fullchain.pem" ]; then
                    cp "$domain_dir/fullchain.pem" "$REPO_ROOT/certs/fullchain.pem"
                    cp "$domain_dir/privkey.pem" "$REPO_ROOT/certs/privkey.pem"
                    cp "$domain_dir/chain.pem" "$REPO_ROOT/certs/chain.pem"
                    
                    echo "$(date): ✅ Updated certificates for $domain" >> "$LOG_FILE"
                fi
            fi
        done
        
        # Reload nginx to pick up new certificates
        if docker compose -f "$REPO_ROOT/docker-compose.yml" \
            -f "$REPO_ROOT/docker-compose.prod.yml" \
            -f "$REPO_ROOT/docker-compose.tls.yml" \
            ps nginx &>/dev/null; then
            
            echo "$(date): 🔄 Reloading nginx..." >> "$LOG_FILE"
            docker compose -f "$REPO_ROOT/docker-compose.yml" \
                -f "$REPO_ROOT/docker-compose.prod.yml" \
                -f "$REPO_ROOT/docker-compose.tls.yml" \
                exec nginx nginx -s reload >> "$LOG_FILE" 2>&1 || true
        fi
    fi
else
    echo "$(date): ⚠️ Renewal check failed" >> "$LOG_FILE"
    exit 1
fi

echo "$(date): Renewal process complete" >> "$LOG_FILE"
