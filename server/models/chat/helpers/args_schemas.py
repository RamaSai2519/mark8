from pydantic import BaseModel


class SaveUserCity(BaseModel):
    city: str


class SaveUserName(BaseModel):
    name: str


class SaveUserBirthDate(BaseModel):
    birthDate: str


class GetUserDetails(BaseModel):
    pass


class GetAvailableSarathis(BaseModel):
    page: int
    size: int


class GetUpcomingEvents(BaseModel):
    pass
