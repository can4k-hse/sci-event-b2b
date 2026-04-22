from pydantic import BaseModel


class TalkResponse(BaseModel):
    talk_id: int
    slot_id: int
    title: str
    speaker: str | None
    description: str | None
    is_selected: bool


class TalksListResponse(BaseModel):
    talks: list[TalkResponse]
    selected_talk_id: int | None


class SelectTalkRequest(BaseModel):
    talk_id: int
