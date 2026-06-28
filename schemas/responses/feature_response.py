import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from models.feature_model import FeatureKindEnum


class FeatureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    name: str
    kind: FeatureKindEnum
    created_at: datetime
    updated_at: datetime
