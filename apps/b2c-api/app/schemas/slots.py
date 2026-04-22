from pydantic import BaseModel


class TalkDetailResponse(BaseModel):
    talk_id: int
    slot_id: int
    title: str
    speakers: list[str]
    description: str | None


class TalkResponse(TalkDetailResponse):
    is_selected: bool


class TalksListResponse(BaseModel):
    talks: list[TalkResponse]
    selected_talk_id: int | None


class SelectTalkRequest(BaseModel):
    talk_id: int
