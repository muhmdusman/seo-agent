import json
from pathlib import Path


SOURCE_FILE = Path("worker-task-source.json")
OUTPUT_FILE = Path("worker-task-definition.json")

WORKER_IMAGE = (
    "975585942582.dkr.ecr.us-east-1.amazonaws.com/"
    "seo-agent-worker:v2"
)


with SOURCE_FILE.open("r", encoding="utf-8-sig") as f:
    task_definition = json.load(f)


# Remove fields returned by describe-task-definition
# that cannot be submitted during registration.
for field in [
    "taskDefinitionArn",
    "revision",
    "status",
    "requiresAttributes",
    "compatibilities",
    "registeredAt",
    "registeredBy",
]:
    task_definition.pop(field, None)


# Worker must have its own ECS task-definition family.
task_definition["family"] = "seo-agent-worker"


container = task_definition["containerDefinitions"][0]

# Worker-specific container configuration.
container["name"] = "seo-agent-worker"

container["image"] = WORKER_IMAGE

container["command"] = [
    "celery",
    "-A",
    "workers.daily_report_worker",
    "worker",
    "--loglevel=info",
    "--without-mingle",
]

# Celery worker does not expose an HTTP port.
container.pop("portMappings", None)


# Write the final ECS task definition.
with OUTPUT_FILE.open("w", encoding="utf-8") as f:
    json.dump(task_definition, f, indent=4)


print(f"Created {OUTPUT_FILE}")
print(f"Family: {task_definition['family']}")
print(f"Image: {container['image']}")
print(f"Command: {' '.join(container['command'])}")
