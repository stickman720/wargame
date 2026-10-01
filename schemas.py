# schemas.py
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ---------- USER ----------
class UserCreate(BaseModel):
    username: str = Field(..., max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=4)
    role: str = "user"


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    password: Optional[str] = None


# ---------- BUILDING ----------
class BuildingCreate(BaseModel):
    name: str
    usage: str = "residential"
    earns: int = 0
    create_cost: int = 0
    update_cost: int = 0


class BuildingUpdate(BaseModel):
    name: Optional[str] = None
    usage: Optional[str] = None
    earns: Optional[int] = None
    create_cost: Optional[int] = None
    update_cost: Optional[int] = None


# ---------- ARMY ----------
class ArmyCreate(BaseModel):
    name: str
    type: str = "infantry"
    power: int = 0
    cost: int = 0


class ArmyUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    power: Optional[int] = None
    cost: Optional[int] = None


# ---------- ASSET ----------
class AssetCreate(BaseModel):
    name: str
    type: str = "resource"
    quantity: int = 0
    value: int = 0


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    quantity: Optional[int] = None
    value: Optional[int] = None


# ---------- CITY / COUNTRY ----------
class CityOrCountryCreate(BaseModel):
    name: str
    type: str = "city"
    population: int = 0
    region: Optional[str] = None


class CityOrCountryUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    population: Optional[int] = None
    region: Optional[str] = None


# ---------- INVENTORY ----------
class InventoryUpdate(BaseModel):
    objectname: str
    newamount: int = Field(ge=0)


# ---------- RELATION ----------
class RelationBody(BaseModel):
    userid: int
    cityname: str

# schemas.py  (only the BuildingActivityCreate block shown)

class BuildingActivityCreate(BaseModel):
    buildingname: str
    objectname: str
    op: str = Field(..., pattern="^(user|produce)$")   # "user" = using, "produce" = producing
    amount: int = Field(ge=0)