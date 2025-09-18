#!/bin/bash
set -e

# Configuration
PROJECT_ID=$GCP_PROJECT_ID  # Replace with your GCP project ID
SERVICE_NAME="unbabel-web"  # This should match the service name used in deployment
REGION="us-central1"  # Change to your preferred region
MIN_INSTANCES=1
MAX_INSTANCES=10
MEMORY="8192Mi"
CPU="8"
CONCURRENCY=80

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Deploying Unbabel to Google Cloud Run...${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed. Please install it first.${NC}"
    echo "Visit: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if user is logged in to gcloud
if ! gcloud auth print-identity-token &> /dev/null; then
    echo -e "${YELLOW}You need to log in to Google Cloud first.${NC}"
    gcloud auth login
fi

# Set the project
echo -e "${YELLOW}Setting Google Cloud project to: ${PROJECT_ID}${NC}"
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo -e "${YELLOW}Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com

# Create Artifact Registry repository if it doesn't exist
echo -e "${YELLOW}Creating Artifact Registry repository...${NC}"
if ! gcloud artifacts repositories describe unbabel --location=us-central1 &>/dev/null; then
  echo "Creating repository 'unbabel' in us-central1..."
  gcloud artifacts repositories create unbabel \
    --repository-format=docker \
    --location=us-central1 \
    --description="Docker repository for Unbabel application"
  
  # Configure Docker to use gcloud as a credential helper
  gcloud auth configure-docker us-central1-docker.pkg.dev
else
  echo "Repository 'unbabel' already exists."
fi

# Build the Docker image and push it to Artifact Registry
IMAGE_NAME="us-central1-docker.pkg.dev/$PROJECT_ID/unbabel/unbabel-web:latest"
echo -e "${YELLOW}Building and pushing Docker image: ${IMAGE_NAME}${NC}"

echo "Building and pushing Docker image..."
# Build specifically for linux/amd64 platform
docker buildx create --use
docker buildx build --no-cache --platform linux/amd64 -t $IMAGE_NAME --push .

# Create a .env.yaml file for environment variables
if [ ! -f .env.yaml ]; then
    echo -e "${YELLOW}Creating .env.yaml file for environment variables...${NC}"
    cat > .env.yaml << EOL
# API Keys
DEEPGRAM_API_KEY: "your-deepgram-api-key"
OPENAI_API_KEY: "your-openai-api-key"

# Application Settings
SOURCE_LANGUAGE: "ko"
TARGET_LANGUAGE: "en"
DEBUG: "true"

# Note: Do not set PORT or other reserved variables here
# Cloud Run automatically sets: PORT, K_SERVICE, K_REVISION, K_CONFIGURATION
EOL
    echo -e "${YELLOW}Please edit .env.yaml with your actual API keys before continuing.${NC}"
    echo -e "${YELLOW}Press Enter to continue after editing, or Ctrl+C to cancel.${NC}"
    read
else
    echo -e "${YELLOW}Using existing .env.yaml file.${NC}"
fi

# Deploy to Cloud Run
echo -e "${YELLOW}Deploying to Cloud Run...${NC}"

echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --env-vars-file .env.yaml \
    --min-instances ${MIN_INSTANCES} \
    --max-instances ${MAX_INSTANCES} \
    --memory ${MEMORY} \
    --cpu ${CPU} \
    --concurrency ${CONCURRENCY} \
    --port 5000


# Note: Public access is restricted by organization policy
echo -e "${YELLOW}Note: Your organization policy restricts public access to Cloud Run services.${NC}"
echo -e "${YELLOW}You'll need to use authenticated access or set up Identity-Aware Proxy (IAP).${NC}"

# Get the URL of the deployed service
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --platform managed --region ${REGION} --format="value(status.url)")

echo -e "${GREEN}Deployment complete!${NC}"
echo -e "${GREEN}Your application is available at: ${SERVICE_URL}${NC}"

echo -e "${YELLOW}To access your service securely, you have several options:${NC}"
echo -e "${YELLOW}1. Use gcloud authentication:${NC}"
echo -e "   gcloud auth login"
echo -e "   curl -H \"Authorization: Bearer $(gcloud auth print-identity-token)\" ${SERVICE_URL}"

echo -e "${YELLOW}2. Set up Identity-Aware Proxy (IAP) for more controlled access:${NC}"
echo -e "   https://cloud.google.com/iap/docs/enabling-cloud-run"

echo -e "${YELLOW}3. Request an organization policy exception from your admin${NC}"
echo -e "   to allow unauthenticated access if needed for your use case."

