#!/bin/bash
kubectl apply -f api-gateway-hpa.yml
kubectl apply -f data-entry-web-hpa.yml
echo "Applied HPA configurations."
echo "getting HPA status ..."
kubectl get hpa