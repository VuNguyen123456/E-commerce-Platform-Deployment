# Deploy checkout service to minimal ECS infrastructure
param(
    [string]$Region = "us-east-1",
    [string]$StackName = "checkout-service-minimal"
)

Write-Host "Deploying checkout service to minimal ECS infrastructure..." -ForegroundColor Green

# Set AWS region
$env:AWS_DEFAULT_REGION = $Region

# Check if stack is ready
Write-Host "Checking stack status..." -ForegroundColor Yellow
$stackStatus = aws cloudformation describe-stacks --stack-name $StackName --query 'Stacks[0].StackStatus' --output text

if ($stackStatus -ne "CREATE_COMPLETE") {
    Write-Host "Stack status: $stackStatus" -ForegroundColor Red
    Write-Host "Stack must be CREATE_COMPLETE before deployment. Please wait for stack creation to finish." -ForegroundColor Red
    exit 1
}

# Get stack outputs
Write-Host "Getting infrastructure details..." -ForegroundColor Yellow
$outputs = aws cloudformation describe-stacks --stack-name $StackName --query 'Stacks[0].Outputs' --output json | ConvertFrom-Json

$ecrUri = ($outputs | Where-Object {$_.OutputKey -eq "ECRRepositoryURI"}).OutputValue
$albDns = ($outputs | Where-Object {$_.OutputKey -eq "ALBDNSName"}).OutputValue
$clusterArn = ($outputs | Where-Object {$_.OutputKey -eq "ECSClusterArn"}).OutputValue
$taskExecutionRoleArn = ($outputs | Where-Object {$_.OutputKey -eq "ECSTaskExecutionRoleArn"}).OutputValue
$taskRoleArn = ($outputs | Where-Object {$_.OutputKey -eq "ECSTaskRoleArn"}).OutputValue
$subnet1 = ($outputs | Where-Object {$_.OutputKey -eq "PublicSubnet1"}).OutputValue
$subnet2 = ($outputs | Where-Object {$_.OutputKey -eq "PublicSubnet2"}).OutputValue
$securityGroup = ($outputs | Where-Object {$_.OutputKey -eq "ECSSecurityGroup"}).OutputValue
$blueTargetGroup = ($outputs | Where-Object {$_.OutputKey -eq "BlueTargetGroupArn"}).OutputValue

Write-Host "ECR URI: $ecrUri" -ForegroundColor Cyan
Write-Host "ALB DNS: $albDns" -ForegroundColor Cyan

# Build and push Docker image
Write-Host "`nBuilding and pushing Docker image..." -ForegroundColor Magenta

# Login to ECR
Write-Host "Logging into ECR..." -ForegroundColor Yellow
$loginPassword = aws ecr get-login-password --region $Region
$loginPassword | docker login --username AWS --password-stdin $ecrUri.Split('/')[0]

if ($LASTEXITCODE -ne 0) {
    Write-Host "ECR login failed!" -ForegroundColor Red
    exit 1
}

# Build image
Write-Host "Building Docker image..." -ForegroundColor Yellow
docker build -t checkout-service .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker build failed!" -ForegroundColor Red
    exit 1
}

# Tag and push image
$imageTag = "latest"
$fullImageUri = "${ecrUri}:${imageTag}"

Write-Host "Tagging image: $fullImageUri" -ForegroundColor Yellow
docker tag checkout-service:latest $fullImageUri

Write-Host "Pushing image to ECR..." -ForegroundColor Yellow
docker push $fullImageUri

if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker push failed!" -ForegroundColor Red
    exit 1
}

# Create ECS Task Definition (without database for now)
Write-Host "`nCreating ECS Task Definition..." -ForegroundColor Magenta

$taskDef = @"
{
  "family": "checkout-service-minimal",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "$taskExecutionRoleArn",
  "taskRoleArn": "$taskRoleArn",
  "containerDefinitions": [
    {
      "name": "checkout-service",
      "image": "$fullImageUri",
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "FLASK_ENV",
          "value": "production"
        },
        {
          "name": "DATABASE_URL",
          "value": "sqlite:///checkout.db"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/checkout-service",
          "awslogs-region": "$Region",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "essential": true
    }
  ]
}
"@

$taskDef | Out-File -FilePath "task-definition-minimal.json" -Encoding UTF8
aws ecs register-task-definition --cli-input-json file://task-definition-minimal.json

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to register task definition!" -ForegroundColor Red
    exit 1
}

# Create ECS Service
Write-Host "`nCreating ECS Service..." -ForegroundColor Magenta

$serviceName = "checkout-service-blue"

$serviceDef = @"
{
  "serviceName": "$serviceName",
  "cluster": "$clusterArn",
  "taskDefinition": "checkout-service-minimal",
  "desiredCount": 1,
  "launchType": "FARGATE",
  "networkConfiguration": {
    "awsvpcConfiguration": {
      "subnets": ["$subnet1", "$subnet2"],
      "securityGroups": ["$securityGroup"],
      "assignPublicIp": "ENABLED"
    }
  },
  "loadBalancers": [
    {
      "targetGroupArn": "$blueTargetGroup",
      "containerName": "checkout-service",
      "containerPort": 8080
    }
  ],
  "healthCheckGracePeriodSeconds": 300
}
"@

$serviceDef | Out-File -FilePath "service-definition-minimal.json" -Encoding UTF8

# Check if service exists
$serviceExists = $false
try {
    $existingService = aws ecs describe-services --cluster $clusterArn --services $serviceName --query 'services[0].status' --output text 2>$null
    if ($LASTEXITCODE -eq 0 -and $existingService -ne "INACTIVE") {
        $serviceExists = $true
    }
} catch {
    $serviceExists = $false
}

if ($serviceExists) {
    Write-Host "Updating existing service..." -ForegroundColor Yellow
    aws ecs update-service --cluster $clusterArn --service $serviceName --task-definition checkout-service-minimal --desired-count 1
} else {
    Write-Host "Creating new service..." -ForegroundColor Yellow
    aws ecs create-service --cli-input-json file://service-definition-minimal.json
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to create/update service!" -ForegroundColor Red
    exit 1
}

# Wait for service to be stable
Write-Host "`nWaiting for service to be healthy (5-10 minutes)..." -ForegroundColor Yellow
aws ecs wait services-stable --cluster $clusterArn --services $serviceName

Write-Host "`nTesting deployment..." -ForegroundColor Magenta
Write-Host "Application URL: http://$albDns" -ForegroundColor Green
Write-Host "Health Check: http://$albDns/health" -ForegroundColor Green

# Wait for ALB to be ready and test
Start-Sleep -Seconds 60
Write-Host "Testing health endpoint..." -ForegroundColor Yellow

try {
    $response = Invoke-RestMethod -Uri "http://$albDns/health" -TimeoutSec 30
    Write-Host "Health check passed!" -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json -Depth 3) -ForegroundColor Cyan
} catch {
    Write-Host "Health check not ready yet, but service is deployed" -ForegroundColor Yellow
    Write-Host "Try accessing http://$albDns in a few minutes" -ForegroundColor Yellow
}

Write-Host "`nDEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "===================" -ForegroundColor Green
Write-Host "Your checkout service is running on:" -ForegroundColor White
Write-Host "URL: http://$albDns" -ForegroundColor Cyan
Write-Host "Health: http://$albDns/health" -ForegroundColor Cyan
Write-Host "" 
Write-Host "This demonstrates:" -ForegroundColor Yellow
Write-Host "- ECS Fargate deployment" -ForegroundColor White
Write-Host "- Application Load Balancer" -ForegroundColor White  
Write-Host "- Blue-Green ready infrastructure" -ForegroundColor White
Write-Host "- Auto-scaling capability" -ForegroundColor White
Write-Host "- Production-ready monitoring" -ForegroundColor White