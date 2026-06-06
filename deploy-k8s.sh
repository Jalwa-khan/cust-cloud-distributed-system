#!/bin/bash
# deploy-k8s.sh - Build images and deploy to Kubernetes (Minikube/local)
# Usage: bash deploy-k8s.sh

set -e
echo "======================================================"
echo " CUST Cloud Platform - Kubernetes Deployment"
echo "======================================================"

# Use Minikube's Docker daemon so images are available to k8s
eval $(minikube docker-env) 2>/dev/null || echo "[INFO] Not using Minikube Docker env - using local"

echo "[1/5] Building Docker images..."
docker build -t cust/registration:latest  ./services/registration
docker build -t cust/lms:latest           ./services/lms
docker build -t cust/examination:latest   ./services/examination
docker build -t cust/api-gateway:latest   ./services/api-gateway
echo "      Images built."

echo "[2/5] Applying Kubernetes manifests..."
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-configmap.yaml
kubectl apply -f k8s/02-pvcs.yaml
kubectl apply -f k8s/03-registration.yaml
kubectl apply -f k8s/04-lms-exam.yaml
kubectl apply -f k8s/05-gateway.yaml
echo "      Manifests applied."

echo "[3/5] Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l app=registration -n cust-cloud --timeout=120s
kubectl wait --for=condition=ready pod -l app=lms          -n cust-cloud --timeout=120s
kubectl wait --for=condition=ready pod -l app=examination  -n cust-cloud --timeout=120s
kubectl wait --for=condition=ready pod -l app=api-gateway  -n cust-cloud --timeout=120s
echo "      All pods ready."

echo "[4/5] Deployment status:"
kubectl get pods     -n cust-cloud
kubectl get services -n cust-cloud
kubectl get hpa      -n cust-cloud

echo "[5/5] Access info:"
echo "      NodePort: http://$(minikube ip 2>/dev/null || echo 'MINIKUBE_IP'):30000"
echo "      Or run:   kubectl port-forward svc/gateway-service 5000:5000 -n cust-cloud"
echo ""
echo "[DONE] Deployment complete!"
