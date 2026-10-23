from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class LinkCreate(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    alias: str | None = None
    title: str | None = Field(default=None, max_length=200)
    expires_at: datetime | None = None


class LinkUpdate(BaseModel):
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    title: str | None = Field(default=None, max_length=200)
    is_active: bool | None = None
    expires_at: datetime | None = None


class LinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    short_url: str
    target_url: str
    title: str | None
    is_active: bool
    expires_at: datetime | None
    click_count: int
    created_at: datetime
    updated_at: datetime


class LinkPage(BaseModel):
    items: list[LinkOut]
    total: int
    page: int
    page_size: int


class CountRow(BaseModel):
    key: str
    count: int


class DayRow(BaseModel):
    date: date
    clicks: int
    visitors: int


class LinkStats(BaseModel):
    link_id: int
    days: int
    total_clicks: int
    unique_visitors: int
    bot_clicks: int
    timeseries: list[DayRow]
    countries: list[CountRow]
    devices: list[CountRow]
    browsers: list[CountRow]
    os: list[CountRow]
    referrers: list[CountRow]


class Overview(BaseModel):
    total_links: int
    active_links: int
    total_clicks: int
    clicks_last_7d: int
    timeseries: list[DayRow]
    top_links: list[LinkOut]
