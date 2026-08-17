from pydantic import BaseModel


class SessionResponse(BaseModel):
    sessionNumber: int
    session_id: int
    startDate: str
    endDate: str
    meanNoiseSession: float
    data: list[float]
    startTimes: list[str | None]
    descriptions: list[str]


class PointResponse(BaseModel):
    pointId: str
    lat: float
    lon: float
    brgy: str
    city: str
    meanNoise: float
    sessions: list[SessionResponse]
