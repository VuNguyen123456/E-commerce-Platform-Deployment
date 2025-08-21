# Simple AWS ECS Deployment Script
param(
    [string]$Region = "us-east-1",
    [string]$StackName = "checkout-service-infra"
)

Write-Host "Starting AWS ECS Deployment..." -ForegroundColor Green
Write-Host "Region: $Region" -ForegroundColor Yellow
Write-Host "Stack: $StackName" -ForegroundColor Yellow

# Set AWS region
$env:AWS_DEFAULT_REGION = $Region

# Step 1: Deploy Infrastructure
Write-Host "`nStep 1: Deploying Infrastructure..." -ForegroundColor Magenta

Write-Host "Creating new stack..." -ForegroundColor Yellow
aws cloudformation create-stack --stack-name $StackName --template-body file://infrastructure.yaml --capabilities CAPABILITY_IAM

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to create stack!" -ForegroundColor Red
    exit 1
}

# Wait for stack to complete
Write-Host "Waiting for stack creation (5-10 minutes)..." -ForegroundColor Yellow

do {
    Start-Sleep -Seconds 30
    $status = aws cloudformation describe-stacks --stack-name $StackName --query 'Stacks[0].StackStatus' --output text
    Write-Host "Stack Status: $status" -ForegroundColor Cyan
} while ($status -like "*_IN_PROGRESS")

if ($status -like "*_COMPLETE") {
    Write-Host "Stack created successfully!" -ForegroundColor Green
} else {
    Write-Host "Stack creation failed!" -ForegroundColor Red
    aws cloudformation describe-stack-events --stack-name $StackName --max-items 5
    exit 1
}

Write-Host "`nDeployment Complete! Check AWS Console for details." -ForegroundColor Green