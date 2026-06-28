from pydantic import BaseModel


class WebhookEventCreateRequest(BaseModel):
    provider: str
    external_event_id: str
    type: str
    payload: dict | None = None
