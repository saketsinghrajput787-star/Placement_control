from typing import Optional
from pydantic import BaseModel

class RoomBase(BaseModel):
    room_code: str
    building: str = "Placement Block"
    floor: int = 1
    capacity: int = 5
    has_video_conf: bool = True
    is_active: bool = True

class RoomCreate(RoomBase):
    pass

class RoomOut(RoomBase):
    id: str

    class Config:
        from_attributes = True

class PanelBase(BaseModel):
    company_id: str
    panel_code: str
    interviewer_names: str = "Interviewer Panel"
    is_active: bool = True

class PanelCreate(PanelBase):
    pass

class PanelOut(PanelBase):
    id: str
    company_name: Optional[str] = None

    class Config:
        from_attributes = True

class SlotOut(BaseModel):
    id: str
    day_number: int
    slot_index: int
    start_time_str: str
    end_time_str: str

    class Config:
        from_attributes = True
