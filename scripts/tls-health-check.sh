#!/bin/bash
# TLS Configuration Health Check Script
#
# Verifies TLS certificate validity and configuration.

set -e

DOMAIN=${1:-}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -z "$DOMAIN" ]; then
    # Try to get domain from docker-compose.tls.yml
    if [ -f "$REPO_ROOT/docker-compose.tls.yml" ]; then
        DOMAIN=$(grep -E "^[[:space:]]*-[[:space:]]*docs\." "$REPO_ROOT/docker-compose.tls.yml" | head -1 | tr -d '[:space:]-' || true)
    fi
    
    if [ -z "$DOMAIN" ]; then
        echo "Usage: $0 <domain>"
        echo "Example: $0 docs.example.com"
        exit 1
    fi
fi

echo "🔍 TLS Health Check for $DOMAIN"
echo ""

# Check certificate files
echo "1. Checking certificate files..."
if [ -f "$REPO_ROOT/certs/fullchain.pem" ]; then
    echo "   ✅ fullchain.pem found"
else
    echo "   ❌ fullchain.pem missing"
    exit 1
fi

if [ -f "$REPO_ROOT/certs/privkey.pem" ]; then
    echo "   ✅ privkey.pem found"
else
    echo "   ❌ privkey.pem missing"
    exit 1
fi

# Check certificate validity
echo ""
echo "2. Checking certificate validity..."
if openssl x509 -in "$REPO_ROOT/certs/fullchain.pem" -noout -checkend 86400 > /dev/null 2>&1; then
    echo "   ✅ Certificate valid for at least 24 hours"
else
    echo "   ⚠️  Certificate expires within 24 hours or is invalid"
fi

# Display certificate info
echo ""
echo "3. Certificate details:"
echo "   Subject: $(openssl x509 -in "$REPO_ROOT/certs/fullchain.pem" -noout -subject | cut -d= -f2-)"
echo "   Issuer: $(openssl x509 -in "$REPO_ROOT/certs/fullchain.pem" -noout -issuer | cut -d= -f2-)"
echo "   Valid from: $(openssl x509 -in "$REPO_ROOT/certs/fullchain.pem" -noout -startdate | cut -d= -f2-)"
echo "   Valid until: $(openssl x509 -in "$REPO_ROOT/certs/fullchain.pem" -noout -enddate | cut -d= -f2-)"
echo "   Serial: $(openssl x509 -in "$REPO_ROOT/certs/fullchain.pem" -noout -serial | cut -d= -f2-)"

# Check HTTPS connectivity (if running)
echo ""
echo "4. Checking HTTPS connectivity..."
if curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN/health" 2>/dev/null | grep -q "200"; then
    echo "   ✅ HTTPS endpoint responding (200 OK)"
elif curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN" 2>/dev/null | grep -qE "(200|301|302)"; then
    echo "   ✅ HTTPS endpoint responding (redirect or OK)"
else
    echo "   ⚠️  Could not connect to HTTPS endpoint (may not be running)"
fi

# Check TLS version
echo ""
echo "5. Checking TLS version support..."
if command -v openssl &> /dev/null; then
    TLS_1_3=$(echo | openssl s_client -connect "$DOMAIN:443" -tls1_3 2>/dev/null | grep -c "TLSv1.3" || true)
    TLS_1_2=$(echo | openssl s_client -connect "$DOMAIN:443" -tls1_2 2>/dev/null | grep -c "TLSv1.2" || true)
    
    if [ "$TLS_1_3" -gt 0 ]; then
        echo "   ✅ TLS 1.3 supported"
    fi
    if [ "$TLS_1_2" -gt 0 ]; then
        echo "   ✅ TLS 1.2 supported"
    fi
fi

# Check certificate chain
echo ""
echo "6. Verifying certificate chain..."
if openssl verify -CAfile "$REPO_ROOT/certs/chain.pem" "$REPO_ROOT/certs/fullchain.pem" > /dev/null 2>&1; then
    echo "   ✅ Certificate chain valid"
else
    echo "   ⚠️  Certificate chain verification failed"
fi

echo ""
echo "✅ Health check complete"
echo ""
echo "📝 Next steps:"
echo "   - Test in browser: https://$DOMAIN"
echo "   - Check SSL Labs: https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
echo "   - Monitor certificate expiry with: ./scripts/renew-certs.sh"
