import json
from pathlib import Path


ENV_FILE = Path(".env.production")
OUTPUT_FILE = Path("backend-task-definition.json")

AWS_REGION = "us-east-1"
AWS_ACCOUNT_ID = "975585942582"

TASK_FAMILY = "seo-agent-backend"
CONTAINER_NAME = "seo-agent-backend"

EXECUTION_ROLE_ARN = (
    f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/"
    "seo-agent-ecs-task-execution-role"
)

IMAGE = (
    f"{AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com/"
    "seo-agent-backend:v3"
)

LOG_GROUP = "/ecs/seo-agent/backend"


def load_env_file(path: Path) -> dict[str, str]:
    """Load KEY=VALUE pairs from a .env file."""

    if not path.exists():
        raise FileNotFoundError(
            f"Environment file not found: {path}"
        )

    env = {}

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()

            # Ignore blank lines and comments
            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                raise ValueError(
                    f"Invalid .env syntax on line {line_number}: {line}"
                )

            key, value = line.split("=", 1)

            key = key.strip()
            value = value.strip()

            # Support:
            # KEY="value"
            # KEY='value'
            if (
                len(value) >= 2
                and value[0] == value[-1]
                and value[0] in ("'", '"')
            ):
                value = value[1:-1]

            env[key] = value

    return env


def build_task_definition(environment: dict[str, str]) -> dict:
    """Build the ECS Fargate task definition from scratch."""

    return {
        "family": TASK_FAMILY,

        "executionRoleArn": EXECUTION_ROLE_ARN,

        "networkMode": "awsvpc",

        "requiresCompatibilities": [
            "FARGATE"
        ],

        "cpu": "512",

        "memory": "1024",

        "containerDefinitions": [
            {
                "name": CONTAINER_NAME,

                "image": IMAGE,

                "essential": True,

                "environment": [
                    {
                        "name": key,
                        "value": value,
                    }
                    for key, value in environment.items()
                ],

                "command": [
                    "python",
                    "-m",
                    "uvicorn",
                    "main:app",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    "8000",
                ],

                "portMappings": [
                    {
                        "containerPort": 8000,
                        "hostPort": 8000,
                        "protocol": "tcp",
                    }
                ],

                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": LOG_GROUP,
                        "awslogs-region": AWS_REGION,
                        "awslogs-stream-prefix": "ecs",
                    },
                },
            }
        ],
    }


def main():
    environment = load_env_file(ENV_FILE)

    task_definition = build_task_definition(environment)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(
            task_definition,
            f,
            indent=4,
        )

    print()
    print("Created:", OUTPUT_FILE)
    print()
    print("Task definition:")
    print("  Family:    ", TASK_FAMILY)
    print("  Container: ", CONTAINER_NAME)
    print("  Image:     ", IMAGE)
    print("  CPU:       512")
    print("  Memory:    1024")
    print("  Environment variables:", len(environment))
    print("  Environment source:", ENV_FILE)
    print()
    print("Command:")
    print(
        "  python -m uvicorn main:app "
        "--host 0.0.0.0 --port 8000"
    )
    print()


if __name__ == "__main__":
    main()