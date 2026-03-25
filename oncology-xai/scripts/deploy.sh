#!/bin/bash
set -euo pipefail

# LCHAI v2.0 AWS EKS Deployment Script
# Usage: ./scripts/deploy.sh [build|push|deploy|all]

REGION="us-east-1"
ACCOUNT="632100838024"
CLUSTER="lchai-prod-eks"
REGISTRY="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"
PREFIX="lchai-prod"
TAG="${TAG:-latest}"

SERVICES=(
  "api-gateway"
  "case-service"
  "image-service"
  "inference-service"
  "ehr-service"
  "graph-service"
  "ontology-admin-service"
  "audit-service"
  "webapp"
)

ecr_login() {
  echo "==> Logging in to ECR..."
  aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REGISTRY
}

build_images() {
  echo "==> Building Docker images..."
  cd "$(dirname "$0")/.."
  for svc in "${SERVICES[@]}"; do
    echo "  Building $svc..."
    docker build -t ${REGISTRY}/${PREFIX}/${svc}:${TAG} \
      -f apps/${svc}/Dockerfile . &
  done
  wait
  echo "==> All images built."
}

push_images() {
  ecr_login
  echo "==> Pushing images to ECR..."
  for svc in "${SERVICES[@]}"; do
    echo "  Pushing $svc..."
    docker push ${REGISTRY}/${PREFIX}/${svc}:${TAG} &
  done
  wait
  echo "==> All images pushed."
}

upload_models() {
  echo "==> Uploading model checkpoints to S3..."
  BACKBONE_DIR="${BACKBONE_HOST_DIR:-D:/Dropbox/PHD/THESIS/SCRIPTS/BACKBONES}"
  CHECKPOINT_DIR="${V2_CHECKPOINT_HOST_PATH:-D:/Dropbox/PHD/THESIS/CHECKPOINTS LUAD V2/checkpoints}"

  aws s3 sync "$BACKBONE_DIR" s3://lchai-prod-models/backbones/ --exclude "*.pyc"
  aws s3 sync "$CHECKPOINT_DIR" s3://lchai-prod-models/checkpoints/ --exclude "*.pyc"
  echo "==> Models uploaded."
}

deploy_helm() {
  echo "==> Updating kubeconfig..."
  aws eks update-kubeconfig --region $REGION --name $CLUSTER

  echo "==> Installing AWS Load Balancer Controller..."
  helm repo add eks https://aws.github.io/eks-charts || true
  helm repo update
  helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
    -n kube-system \
    --set clusterName=$CLUSTER \
    --set serviceAccount.create=true || true

  echo "==> Installing NVIDIA device plugin..."
  helm repo add nvdp https://nvidia.github.io/k8s-device-plugin || true
  helm repo update
  helm upgrade --install nvidia-device-plugin nvdp/nvidia-device-plugin \
    -n kube-system \
    --set tolerations[0].key=nvidia.com/gpu \
    --set tolerations[0].operator=Exists \
    --set tolerations[0].effect=NoSchedule || true

  echo "==> Installing LCHAI..."
  helm upgrade --install lchai ./infra/helm/lchai \
    --set postgres.password="${DB_PASSWORD}" \
    --set openaiApiKey="${OPENAI_API_KEY}" \
    --set image.tag="${TAG}"

  echo "==> Deployment complete!"
  echo "    Cluster: $CLUSTER"
  echo "    Domain:  https://lchai.gptfy.biz"
  kubectl get ingress lchai-ingress
}

case "${1:-all}" in
  build)   build_images ;;
  push)    push_images ;;
  models)  upload_models ;;
  deploy)  deploy_helm ;;
  all)
    build_images
    push_images
    upload_models
    deploy_helm
    ;;
  *)
    echo "Usage: $0 [build|push|models|deploy|all]"
    exit 1
    ;;
esac
