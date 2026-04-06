#!/bin/bash
# Deploy Bifrost and Bifrost Docs in separate namespaces
# Usage: ./deploy.sh [environment]

set -e

ENVIRONMENT=${1:-development}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Deploying Bifrost multi-namespace architecture..."
echo "   Environment: $ENVIRONMENT"
echo ""

# Step 1: Create namespaces
echo "📦 Creating namespaces..."
kubectl apply -f "$SCRIPT_DIR/namespaces/"

# Step 2: Apply network policies
echo "🔒 Applying network policies..."
kubectl apply -k "$SCRIPT_DIR/platform/network-policies/"

# Step 3: Deploy Bifrost Docs
echo "📄 Deploying Bifrost Docs..."
kubectl apply -k "$SCRIPT_DIR/overlays/$ENVIRONMENT/"

echo ""
echo "✅ Bifrost Docs deployed!"
echo ""
echo "📋 Next steps:"
echo "   1. Deploy Bifrost from MTG-Thomas/bifrost repo into 'bifrost' namespace"
echo "   2. Verify cross-namespace connectivity:"
echo "      kubectl run debug -n bifrost-docs --rm -it --image=curlimages/curl -- curl http://bifrost-api.bifrost.svc.cluster.local:8000/health"
echo "   3. Check ingress is working:"
echo "      kubectl get ingress -n bifrost-docs"
echo ""
echo "🔗 Useful commands:"
echo "   - View all namespaces: kubectl get namespaces"
echo "   - View pods by namespace: kubectl get pods -n bifrost-docs"
echo "   - View network policies: kubectl get networkpolicy --all-namespaces"
