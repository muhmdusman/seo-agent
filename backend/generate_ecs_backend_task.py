import json
import subprocess
from pathlib import Path
from urllib.parse import quote

from dotenv import dotenv_values


REGION = "us-east-1"
ACCOUNT_ID = "975585942582"

ENV_FILE = ".env.production"

IMAGE = (
    f"{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/"
    "seo-agent-backend:v1"
)

RDS_HOST = "seo-agent-postgres.c6z20owu436x.us-east-1.rds.amazonaws.com"

REDIS_HOST = "seo-agent-redis-mqihh3.serverless.use1.cache.amazonaws.com"

RDS_SECRET_ARN = (
    "arn:aws:secretsmanager:us-east-1:975585942582:"
    "secret:rds!db-868a0f1f-72cf-447b-89e9-0dc525de9485-VSVYDq"
)


# ---------------------------------------------------------
# Check production environment file
# ---------------------------------------------------------

if not Path(ENV_FILE).exists():
    print(f"ERROR: {ENV_FILE} was not found.")
    print("Create the production environment file first.")
    raise SystemExit(1)


# ---------------------------------------------------------
# Load production application configuration
# ---------------------------------------------------------

env = dotenv_values(ENV_FILE)


required_variables = [
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_REDIRECT_URI",
    "JWT_SECRET",
    "JWT_ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "REFRESH_TOKEN_EXPIRY_DAYS",
    "APP_NAME",
    "APP_URL",
    "FRONTEND_URL",
    "MISTRAL_API_KEY",
    "Groq_Api_Key",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "SMTP_FROM_EMAIL",
    "SMTP_FROM_NAME",
    "SCHEDULER_ENABLED",
    "DAILY_REPORT_TIME",
    "ADMIN_EMAIL",
]


missing = [
    key
    for key in required_variables
    if not env.get(key)
]

if missing:
    print(f"Missing variables in {ENV_FILE}:")
    for key in missing:
        print(f"  - {key}")

    raise SystemExit(1)


# ---------------------------------------------------------
# Retrieve RDS managed password locally
# ---------------------------------------------------------

print("Retrieving RDS credentials from AWS...")

result = subprocess.run(
    [
        "aws",
        "secretsmanager",
        "get-secret-value",
        "--secret-id",
        RDS_SECRET_ARN,
        "--query",
        "SecretString",
        "--output",
        "text",
        "--region",
        REGION,
    ],
    capture_output=True,
    text=True,
    check=True,
)

secret = json.loads(result.stdout)

username = secret["username"]
password = secret["password"]

encoded_username = quote(username, safe="")
encoded_password = quote(password, safe="")


# ---------------------------------------------------------
# Construct AWS runtime URLs
# ---------------------------------------------------------

database_url = (
    f"postgresql+psycopg://"
    f"{encoded_username}:{encoded_password}"
    f"@{RDS_HOST}:5432/seo_agent"
)

redis_url = (
    f"rediss://{REDIS_HOST}:6379/0"
)


# ---------------------------------------------------------
# ECS environment variables
# ---------------------------------------------------------

environment = []

# Application configuration from .env.production
for key in required_variables:
    environment.append(
        {
            "name": key,
            "value": str(env[key]),
        }
    )


# AWS infrastructure configuration
environment.extend(
    [
        {
            "name": "DATABASE_URL",
            "value": database_url,
        },
        {
            "name": "REDIS_URL",
            "value": redis_url,
        },
    ]
)


# ---------------------------------------------------------
# ECS task definition
# ---------------------------------------------------------

task_definition = {
    "family": "seo-agent-backend",

    "networkMode": "awsvpc",

    "requiresCompatibilities": [
        "FARGATE"
    ],

    "cpu": "512",

    "memory": "1024",

    "executionRoleArn": (
        f"arn:aws:iam::{ACCOUNT_ID}:role/"
        "seo-agent-ecs-task-execution-role"
    ),

    "containerDefinitions": [
        {
            "name": "seo-agent-backend",

            "image": IMAGE,

            "essential": True,

            "portMappings": [
                {
                    "containerPort": 8000,
                    "protocol": "tcp"
                }
            ],

            "environment": environment,

            "logConfiguration": {
                "logDriver": "awslogs",

                "options": {
                    "awslogs-group": "/ecs/seo-agent/backend",
                    "awslogs-region": REGION,
                    "awslogs-stream-prefix": "ecs"
                }
            }
        }
    ]
}


# ---------------------------------------------------------
# Write task definition
# ---------------------------------------------------------

output_file = "ecs-backend-task-definition.json"

with open(
    output_file,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        task_definition,
        file,
        indent=2
    )


# ---------------------------------------------------------
# Safe output
# ---------------------------------------------------------

print()
print(f"Created {output_file}")
print("Application configuration loaded from .env.production.")
print("DATABASE_URL configured for RDS.")
print("REDIS_URL configured for Valkey.")
print("Secrets were not printed.")