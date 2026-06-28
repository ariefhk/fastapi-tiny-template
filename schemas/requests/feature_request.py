from pydantic import BaseModel

from models.feature_model import FeatureKindEnum


class FeatureCreateRequest(BaseModel):
    key: str
    name: str
    kind: FeatureKindEnum = FeatureKindEnum.BOOLEAN


class FeatureUpdateRequest(BaseModel):
    name: str | None = None
    kind: FeatureKindEnum | None = None


class FeatureFilterRequest(BaseModel):
    key: str | None = None
    name: str | None = None
    kind: FeatureKindEnum | None = None
