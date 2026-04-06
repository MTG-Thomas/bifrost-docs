#!/bin/bash
# Let's Encrypt TLS Certificate Setup Script
#
# This script obtains TLS certificates from Let's Encrypt using certbot
# with the nginx webroot plugin.
#
# Usage: ./setup-letsencrypt.sh <domain> [email]

set -e

DOMAIN=${1:-}
EMAIL=${2:-admin@example.com}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -z "$DOMAIN" ]; then
    echo "Usage: $0 <domain> [email]"
    echo "Example: $0 docs.example.com admin@example.com"
    exit 1
fi

echo "🔐 Let's Encrypt TLS Certificate Setup"
echo "   Domain: $DOMAIN"
echo "   Email: $EMAIL"
echo ""

# Create directories
mkdir -p "$REPO_ROOT/certs"
mkdir -p "$REPO_ROOT/certbot/www"
mkdir -p "$REPO_ROOT/certbot/conf"

# Check if certbot is available
if ! command -v certbot &> /dev/null; then
    echo "❌ certbot not found. Installing..."
    
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y certbot
    elif command -v yum &> /dev/null; then
        sudo yum install -y certbot
    elif command -v brew &> /dev/null; then
        brew install certbot
    else
        echo "❌ Unable to install certbot automatically."
        echo "   Please install certbot manually: https://certbot.eff.org/instructions"
        exit 1
    fi
fi

# Check if nginx is running with the production config
echo "1. Checking nginx configuration..."
if ! docker compose ps nginx &>/dev/null; then
    echo "   Starting nginx with webroot configuration..."
    
    # Create temporary nginx config for certbot
    cat > "$REPO_ROOT/config/nginx.temp-certbot.conf" << 'EOF'
server {
    listen 80;
    server_name _;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 404;
    }
}
EOF
    
    # Start nginx with temp config
    docker compose -f "$REPO_ROOT/docker-compose.yml" \
        -f "$REPO_ROOT/docker-compose.prod.yml" up -d nginx
fi

# Obtain certificate
echo "2. Obtaining certificate from Let's Encrypt..."
certbot certonly \
    --webroot \
    --webroot-path "$REPO_ROOT/certbot/www" \
    --domain "$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos \
    --non-interactive \
    --config-dir "$REPO_ROOT/certbot/conf" \
    --work-dir "$REPO_ROOT/certbot/work" \
    --logs-dir "$REPO_ROOT/certbot/logs"

# Copy certificates to nginx certs directory
echo "3. Installing certificates..."
CERT_PATH="$REPO_ROOT/certbot/conf/live/$DOMAIN"

if [ -f "$CERT_PATH/fullchain.pem" ]; then
    cp "$CERT_PATH/fullchain.pem" "$REPO_ROOT/certs/fullchain.pem"
    cp "$CERT_PATH/privkey.pem" "$REPO_ROOT/certs/privkey.pem"
    cp "$CERT_PATH/chain.pem" "$REPO_ROOT/certs/chain.pem"
    
    echo "   ✅ Certificates installed successfully"
else
    echo "   ❌ Certificate files not found at $CERT_PATH"
    exit 1
fi

# Update docker-compose.tls.yml with domain
echo "4. Updating configuration..."
if [ -f "$REPO_ROOT/docker-compose.tls.yml" ]; then
    sed -i "s/your-domain.com/$DOMAIN/g" "$REPO_ROOT/docker-compose.tls.yml"
fi

# Reload nginx with production config
echo "5. Reloading nginx with TLS configuration..."
if [ -f "$REPO_ROOT/config/nginx.temp-certbot.conf" ]; then
    rm "$REPO_ROOT/config/nginx.temp-certbot.conf"
fi

docker compose -f "$REPO_ROOT/docker-compose.yml" \
    -f "$REPO_ROOT/docker-compose.prod.yml" \
    -f "$REPO_ROOT/docker-compose.tls.yml" \
    exec nginx nginx -s reload 2>/dev/null || \
    docker compose -f "$REPO_ROOT/docker-compose.yml" \
        -f "$REPO_ROOT/docker-compose.prod.yml" \
        -f "$REPO_ROOT/docker-compose.tls.yml" \
        up -d --force-recreate nginx

# Set up auto-renewal
echo "6. Setting up certificate auto-renewal..."
(crontab -l 2>/dev/null | grep -v "renew-certs.sh"; echo "0 3 * * 0 $REPO_ROOT/scripts/renew-certs.sh >> /var/log/letsencrypt-renewal.log 2>&1") | crontab -

echo ""
echo "✅ TLS Certificate Setup Complete!"
echo ""
echo "📋 Summary:"
echo "   Domain: $DOMAIN"
echo "   Certificate: $REPO_ROOT/certs/fullchain.pem"
echo "   Private Key: $REPO_ROOT/certs/privkey.pem"
echo "   Auto-renewal: Sundays at 3:00 AM"
echo ""
echo "🔗 Testing:"
echo "   curl -I https://$DOMAIN"
echo ""
echo "📅 Certificate Expiry:"
openssl x509 -in "$REPO_ROOT/certs/fullchain.pem" -noout -dates | grep notAfter
