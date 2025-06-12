#!/bin/bash

# Personal Finance App Deployment Script
set -e

# Configuration
PROJECT_NAME="personal-finance"
AWS_REGION="us-east-1"
ENVIRONMENT=${1:-development}

echo "🚀 Deploying Personal Finance App to $ENVIRONMENT environment..."

# Check if required tools are installed
check_dependencies() {
    echo "📋 Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v aws &> /dev/null; then
        echo "❌ AWS CLI is not installed. Please install AWS CLI first."
        exit 1
    fi
    
    if ! command -v terraform &> /dev/null; then
        echo "❌ Terraform is not installed. Please install Terraform first."
        exit 1
    fi
    
    echo "✅ All dependencies are installed."
}

# Setup AWS credentials
setup_aws() {
    echo "🔑 Setting up AWS credentials..."
    
    if [[ -z "$AWS_ACCESS_KEY_ID" || -z "$AWS_SECRET_ACCESS_KEY" ]]; then
        echo "⚠️  AWS credentials not found in environment variables."
        echo "Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY or run 'aws configure'"
        
        # Check if AWS CLI is configured
        if ! aws sts get-caller-identity &> /dev/null; then
            echo "❌ AWS CLI is not configured. Please run 'aws configure' first."
            exit 1
        fi
    fi
    
    echo "✅ AWS credentials are configured."
}

# Build and push Docker image
build_and_push() {
    echo "🏗️  Building and pushing Docker image..."
    
    # Get AWS account ID
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    ECR_REPOSITORY_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME"
    
    # Login to ECR
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY_URI
    
    # Build image
    docker build -t $PROJECT_NAME .
    
    # Tag image
    docker tag $PROJECT_NAME:latest $ECR_REPOSITORY_URI:latest
    docker tag $PROJECT_NAME:latest $ECR_REPOSITORY_URI:$ENVIRONMENT
    
    # Push image
    docker push $ECR_REPOSITORY_URI:latest
    docker push $ECR_REPOSITORY_URI:$ENVIRONMENT
    
    echo "✅ Docker image built and pushed successfully."
}

# Deploy infrastructure
deploy_infrastructure() {
    echo "🏗️  Deploying infrastructure with Terraform..."
    
    cd terraform
    
    # Initialize Terraform
    terraform init
    
    # Plan deployment
    terraform plan -var="environment=$ENVIRONMENT" -out=tfplan
    
    # Apply deployment
    terraform apply tfplan
    
    # Get outputs
    LOAD_BALANCER_URL=$(terraform output -raw load_balancer_url)
    
    cd ..
    
    echo "✅ Infrastructure deployed successfully."
    echo "🌐 Application URL: $LOAD_BALANCER_URL"
}

# Update ECS service
update_service() {
    echo "🔄 Updating ECS service..."
    
    # Force new deployment
    aws ecs update-service \
        --cluster "$PROJECT_NAME-cluster" \
        --service "$PROJECT_NAME-service" \
        --force-new-deployment \
        --region $AWS_REGION
    
    # Wait for deployment to complete
    aws ecs wait services-stable \
        --cluster "$PROJECT_NAME-cluster" \
        --services "$PROJECT_NAME-service" \
        --region $AWS_REGION
    
    echo "✅ ECS service updated successfully."
}

# Run database migrations
run_migrations() {
    echo "🗄️  Running database migrations..."
    
    # Get running task ARN
    TASK_ARN=$(aws ecs list-tasks \
        --cluster "$PROJECT_NAME-cluster" \
        --service-name "$PROJECT_NAME-service" \
        --query 'taskArns[0]' \
        --output text \
        --region $AWS_REGION)
    
    if [ "$TASK_ARN" != "None" ]; then
        # Run migration
        aws ecs execute-command \
            --cluster "$PROJECT_NAME-cluster" \
            --task $TASK_ARN \
            --container $PROJECT_NAME \
            --interactive \
            --command "flask db upgrade" \
            --region $AWS_REGION
        
        echo "✅ Database migrations completed."
    else
        echo "⚠️  No running tasks found. Migrations will run on next deployment."
    fi
}

# Health check
health_check() {
    echo "🏥 Performing health check..."
    
    # Get load balancer URL from Terraform output
    cd terraform
    LOAD_BALANCER_URL=$(terraform output -raw load_balancer_url 2>/dev/null || echo "")
    cd ..
    
    if [ -n "$LOAD_BALANCER_URL" ]; then
        # Wait for application to be ready
        echo "⏳ Waiting for application to be ready..."
        for i in {1..30}; do
            if curl -s "$LOAD_BALANCER_URL/health" > /dev/null; then
                echo "✅ Application is healthy and ready!"
                echo "🌐 Access your application at: $LOAD_BALANCER_URL"
                return 0
            fi
            echo "⏳ Attempt $i/30: Application not ready yet, waiting..."
            sleep 10
        done
        
        echo "❌ Health check failed. Application may not be ready."
        return 1
    else
        echo "⚠️  Could not determine load balancer URL for health check."
    fi
}

# Main deployment flow
main() {
    echo "🎯 Starting deployment for environment: $ENVIRONMENT"
    
    check_dependencies
    setup_aws
    
    if [ "$ENVIRONMENT" = "production" ] || [ "$ENVIRONMENT" = "staging" ]; then
        build_and_push
        deploy_infrastructure
        update_service
        run_migrations
        health_check
    else
        echo "🐳 For development, use docker-compose:"
        echo "   docker-compose up --build"
    fi
    
    echo "🎉 Deployment completed successfully!"
}

# Help function
show_help() {
    echo "Usage: $0 [ENVIRONMENT]"
    echo ""
    echo "ENVIRONMENT options:"
    echo "  development (default) - Local development with docker-compose"
    echo "  staging              - Deploy to AWS staging environment"
    echo "  production           - Deploy to AWS production environment"
    echo ""
    echo "Examples:"
    echo "  $0                   # Deploy to development"
    echo "  $0 staging           # Deploy to staging"
    echo "  $0 production        # Deploy to production"
    echo ""
    echo "Prerequisites:"
    echo "  - Docker installed"
    echo "  - AWS CLI configured"
    echo "  - Terraform installed"
    echo "  - AWS credentials set up"
}

# Check for help flag
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_help
    exit 0
fi

# Run main function
main 