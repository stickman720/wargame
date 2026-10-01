# schemas.py
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "user"

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    password: Optional[str] = None


class BuildingCreate(BaseModel):
    name: str
    usage: str = "residential"
    earns: int = 0
    max_level: int = 1

class BuildingUpdate(BaseModel):
    name: Optional[str] = None
    usage: Optional[str] = None
    earns: Optional[int] = None


# --- new: recipe item for a building level ---
class BuildingLevelCostCreate(BaseModel):
    buildingname: str
    level: int = Field(ge=1)
    objectname: str
    kind: str = Field(..., pattern="^(asset|building|money)$")
    amount: int = Field(ge=0)


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


class CityOrCountryCreate(BaseModel):
    name: str
    type: str = "city"
    population: int = 0
    owner_id:int
    region: Optional[str] = None

class CityOrCountryUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    population: Optional[int] = None
    region: Optional[str] = None


class InventoryUpdate(BaseModel):
    objectname: str
    newamount: int = Field(ge=0)


class RelationBody(BaseModel):
    userid: int
    cityname: str


class BuildingActivityCreate(BaseModel):
    buildingname: str
    objectname: str
    op: str = Field(..., pattern="^(user|produce)$")
    amount: int = Field(ge=0)


# --- new: upgrade request ---
class UpgradeBody(BaseModel):
    userid: int
    buildingname: str