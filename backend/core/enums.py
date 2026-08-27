from enum import Enum
from enum import StrEnum


class OAuthProvider(str, Enum):
    GOOGLE = "google"



class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"