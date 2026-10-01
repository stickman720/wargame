# models.py
import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship, Session, select


# ============================================================
# USER
# ============================================================
class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=100)
    email: str = Field(index=True, unique=True, max_length=255)
    role: str = Field(default="user", max_length=50)
    password_hash: str = Field(max_length=255)
    created_at: datetime.datetime = Field(default=datetime.datetime.now(datetime.timezone.utc))
    last_login: Optional[datetime.datetime] = None

    # relationships
    inventory_items: List["UserInventory"] = Relationship(back_populates="user")
    locations: List["UserLocation"] = Relationship(back_populates="user")

    #----------- GET‌ BY USERNAME---------
    @classmethod
    def get_by_username(cls , session:Session , username):
        stat = select(User).where(User.username == username)
        u = session.exec(stat).first()
        return u



    # ---------- CREATE ----------
    @classmethod
    def create(
        cls,
        session: Session,
        *,
        username: str,
        email: str,
        password: str,
        role: str = "user",
    ) -> "User":
        # (hash the password here — replace with real hashing)
        user = cls(
            username=username,
            email=email,
            password_hash=password,  # TODO: hash
            role=role,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    # ---------- GET ----------
    @classmethod
    def get(cls, session: Session, user_id: int) -> Optional["User"]:
        return session.get(cls, user_id)

    # ---------- GET ALL ----------
    @classmethod
    def get_all(cls, session: Session) -> List["User"]:
        return session.exec(select(cls)).all()

    # ---------- UPDATE ----------
    @classmethod
    def update(
        cls,
        session: Session,
        user_id: int,
        *,
        username: Optional[str] = None,
        email: Optional[str] = None,
        role: Optional[str] = None,
        password: Optional[str] = None,
    ) -> Optional["User"]:
        user = session.get(cls, user_id)
        if not user:
            return None
        if username is not None:
            user.username = username
        if email is not None:
            user.email = email
        if role is not None:
            user.role = role
        if password is not None:
            user.password_hash = password  # TODO: hash
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    # ---------- DELETE ----------
    @classmethod
    def delete(cls, session: Session, user_id: int) -> bool:
        user = session.get(cls, user_id)
        if not user:
            return False
        session.delete(user)
        session.commit()
        return True


# ============================================================
# BUILDING
# ============================================================
class Building(SQLModel, table=True):
    __tablename__ = "buildings"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=150)
    usage: str = Field(default="residential", max_length=50)
    earns: int = Field(default=0, ge=0)
    create_cost: int = Field(default=0, ge=0)
    update_cost: int = Field(default=0, ge=0)

    # ---------- CREATE ----------
    @classmethod
    def create(
        cls,
        session: Session,
        *,
        name: str,
        usage: str = "residential",
        earns: int = 0,
        create_cost: int = 0,
        update_cost: int = 0,
    ) -> "Building":
        building = cls(
            name=name,
            usage=usage,
            earns=earns,
            create_cost=create_cost,
            update_cost=update_cost,
        )
        session.add(building)
        session.commit()
        session.refresh(building)
        return building

    # ---------- GET ----------
    @classmethod
    def get(cls, session: Session, building_id: int) -> Optional["Building"]:
        return session.get(cls, building_id)

    @classmethod
    def get_all(cls, session: Session) -> List["Building"]:
        return session.exec(select(cls)).all()

    @classmethod
    def get_by_name(cls,session:Session , name):
        stat = select(Building).where(Building.name == name)
        return session.exec(stat).first()


    # ---------- UPDATE ----------
    @classmethod
    def update(
        cls,
        session: Session,
        building_id: int,
        *,
        name: Optional[str] = None,
        usage: Optional[str] = None,
        earns: Optional[int] = None,
        create_cost: Optional[int] = None,
        update_cost: Optional[int] = None,
    ) -> Optional["Building"]:
        b = session.get(cls, building_id)
        if not b:
            return None
        if name is not None:        b.name = name
        if usage is not None:       b.usage = usage
        if earns is not None:       b.earns = earns
        if create_cost is not None: b.create_cost = create_cost
        if update_cost is not None: b.update_cost = update_cost
        session.add(b)
        session.commit()
        session.refresh(b)
        return b

    # ---------- DELETE ----------
    @classmethod
    def delete(cls, session: Session, building_id: int) -> bool:
        b = session.get(cls, building_id)
        if not b:
            return False
        session.delete(b)
        session.commit()
        return True


# ============================================================
# ARMY OBJECT
# ============================================================
class ArmyObject(SQLModel, table=True):
    __tablename__ = "army_objects"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=150)
    type: str = Field(default="infantry", max_length=50)
    power: int = Field(default=0, ge=0)
    cost: int = Field(default=0, ge=0)

    inventory_items: List["UserInventory"] = Relationship(back_populates="army_object")

    # ---------- CREATE ----------
    @classmethod
    def create(
        cls,
        session: Session,
        *,
        name: str,
        type: str = "infantry",
        power: int = 0,
        cost: int = 0,
    ) -> "ArmyObject":
        obj = cls(name=name, type=type, power=power, cost=cost)
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj

    # ---------- GET ----------
    @classmethod
    def get(cls, session: Session, obj_id: int) -> Optional["ArmyObject"]:
        return session.get(cls, obj_id)

    @classmethod
    def get_by_name(cls, session: Session, name: str) -> Optional["ArmyObject"]:
        return session.exec(select(cls).where(cls.name == name)).first()

    @classmethod
    def get_all(cls, session: Session) -> List["ArmyObject"]:
        return session.exec(select(cls)).all()

    # ---------- UPDATE ----------
    @classmethod
    def update(
        cls,
        session: Session,
        obj_id: int,
        *,
        name: Optional[str] = None,
        type: Optional[str] = None,
        power: Optional[int] = None,
        cost: Optional[int] = None,
    ) -> Optional["ArmyObject"]:
        obj = session.get(cls, obj_id)
        if not obj:
            return None
        if name is not None:  obj.name = name
        if type is not None:  obj.type = type
        if power is not None: obj.power = power
        if cost is not None:  obj.cost = cost
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj

    # ---------- DELETE ----------
    @classmethod
    def delete(cls, session: Session, obj_id: int) -> bool:
        obj = session.get(cls, obj_id)
        if not obj:
            return False
        session.delete(obj)
        session.commit()
        return True


# ============================================================
# ASSET
# ============================================================
class Asset(SQLModel, table=True):
    __tablename__ = "assets"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=150)
    type: str = Field(default="resource", max_length=50)
    quantity: int = Field(default=0, ge=0)
    value: int = Field(default=0, ge=0)

    inventory_items: List["UserInventory"] = Relationship(back_populates="asset")

    # ---------- CREATE ----------
    @classmethod
    def create(
        cls,
        session: Session,
        *,
        name: str,
        type: str = "resource",
        quantity: int = 0,
        value: int = 0,
    ) -> "Asset":
        asset = cls(name=name, type=type, quantity=quantity, value=value)
        session.add(asset)
        session.commit()
        session.refresh(asset)
        return asset

    # ---------- GET ----------
    @classmethod
    def get(cls, session: Session, asset_id: int) -> Optional["Asset"]:
        return session.get(cls, asset_id)

    @classmethod
    def get_by_name(cls, session: Session, name: str) -> Optional["Asset"]:
        return session.exec(select(cls).where(cls.name == name)).first()

    @classmethod
    def get_all(cls, session: Session) -> List["Asset"]:
        return session.exec(select(cls)).all()

    # ---------- UPDATE ----------
    @classmethod
    def update(
        cls,
        session: Session,
        asset_id: int,
        *,
        name: Optional[str] = None,
        type: Optional[str] = None,
        quantity: Optional[int] = None,
        value: Optional[int] = None,
    ) -> Optional["Asset"]:
        asset = session.get(cls, asset_id)
        if not asset:
            return None
        if name is not None:     asset.name = name
        if type is not None:     asset.type = type
        if quantity is not None: asset.quantity = quantity
        if value is not None:    asset.value = value
        session.add(asset)
        session.commit()
        session.refresh(asset)
        return asset

    # ---------- DELETE ----------
    @classmethod
    def delete(cls, session: Session, asset_id: int) -> bool:
        asset = session.get(cls, asset_id)
        if not asset:
            return False
        session.delete(asset)
        session.commit()
        return True


# ============================================================
# CITY / COUNTRY
# ============================================================
class CityOrCountry(SQLModel, table=True):
    __tablename__ = "cities_countries"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=150)
    type: str = Field(default="city", max_length=20)  # "city" | "country"
    population: int = Field(default=0, ge=0)
    region: Optional[str] = Field(default=None, max_length=100)

    user_links: List["UserLocation"] = Relationship(back_populates="location")

    # ---------- CREATE ----------
    @classmethod
    def create(
        cls,
        session: Session,
        *,
        name: str,
        type: str = "city",
        population: int = 0,
        region: Optional[str] = None,
    ) -> "CityOrCountry":
        loc = cls(name=name, type=type, population=population, region=region)
        session.add(loc)
        session.commit()
        session.refresh(loc)
        return loc

    # ---------- GET ----------
    @classmethod
    def get(cls, session: Session, loc_id: int) -> Optional["CityOrCountry"]:
        return session.get(cls, loc_id)

    @classmethod
    def get_by_name(cls, session: Session, name: str) -> Optional["CityOrCountry"]:
        return session.exec(select(cls).where(cls.name == name)).first()

    @classmethod
    def get_all(cls, session: Session) -> List["CityOrCountry"]:
        return session.exec(select(cls)).all()

    # ---------- UPDATE ----------
    @classmethod
    def update(
        cls,
        session: Session,
        loc_id: int,
        *,
        name: Optional[str] = None,
        type: Optional[str] = None,
        population: Optional[int] = None,
        region: Optional[str] = None,
    ) -> Optional["CityOrCountry"]:
        loc = session.get(cls, loc_id)
        if not loc:
            return None
        if name is not None:       loc.name = name
        if type is not None:       loc.type = type
        if population is not None: loc.population = population
        if region is not None:     loc.region = region
        session.add(loc)
        session.commit()
        session.refresh(loc)
        return loc

    # ---------- DELETE ----------
    @classmethod
    def delete(cls, session: Session, loc_id: int) -> bool:
        loc = session.get(cls, loc_id)
        if not loc:
            return False
        session.delete(loc)
        session.commit()
        return True


# ============================================================
# USER INVENTORY  (user ↔ army_object / asset)
# ============================================================
class UserInventory(SQLModel, table=True):
    __tablename__ = "user_inventory"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    army_object_id: Optional[int] = Field(default=None, foreign_key="army_objects.id", index=True)
    asset_id: Optional[int] = Field(default=None, foreign_key="assets.id", index=True)
    amount: int = Field(default=0, ge=0)

    user: Optional[User] = Relationship(back_populates="inventory_items")
    army_object: Optional[ArmyObject] = Relationship(back_populates="inventory_items")
    asset: Optional[Asset] = Relationship(back_populates="inventory_items")

    # ---------- SET (upsert) ----------
    # Called by PUT /api/inventory/{userid}
    # Body: { "objectname": ..., "newamount": ... }
    @classmethod
    def set_amount(
        cls,
        session: Session,
        user_id: int,
        objectname: str,
        newamount: int,
    ) -> Optional["UserInventory"]:
        # 1) make sure user exists
        user = session.get(User, user_id)
        if not user:
            return None

        # 2) try army object first
        army = ArmyObject.get_by_name(session, objectname)
        if army:
            inv = session.exec(
                select(cls)
                .where(cls.user_id == user_id)
                .where(cls.army_object_id == army.id)
            ).first()
            if inv is None:
                inv = cls(user_id=user_id, army_object_id=army.id, amount=0)
                session.add(inv)
            inv.amount = newamount
            session.commit()
            session.refresh(inv)
            return inv

        # 3) then try asset
        asset = Asset.get_by_name(session, objectname)
        if asset:
            inv = session.exec(
                select(cls)
                .where(cls.user_id == user_id)
                .where(cls.asset_id == asset.id)
            ).first()
            if inv is None:
                inv = cls(user_id=user_id, asset_id=asset.id, amount=0)
                session.add(inv)
            inv.amount = newamount
            session.commit()
            session.refresh(inv)
            return inv

        # 4) object not found in either table
        return None

    # ---------- GET ONE ----------
    @classmethod
    def get_for_user(
        cls,
        session: Session,
        user_id: int,
        objectname: str,
    ) -> Optional["UserInventory"]:
        army = ArmyObject.get_by_name(session, objectname)
        if army:
            return session.exec(
                select(cls)
                .where(cls.user_id == user_id)
                .where(cls.army_object_id == army.id)
            ).first()

        asset = Asset.get_by_name(session, objectname)
        if asset:
            return session.exec(
                select(cls)
                .where(cls.user_id == user_id)
                .where(cls.asset_id == asset.id)
            ).first()

        return None

    # ---------- GET ALL FOR USER ----------
    @classmethod
    def get_all_for_user(cls, session: Session, user_id: int) -> List["UserInventory"]:
        return session.exec(select(cls).where(cls.user_id == user_id)).all()

    # ---------- DELETE ----------
    @classmethod
    def delete(cls, session: Session, inv_id: int) -> bool:
        inv = session.get(cls, inv_id)
        if not inv:
            return False
        session.delete(inv)
        session.commit()
        return True


# ============================================================
# USER ↔ LOCATION  (many-to-many)
# ============================================================
class UserLocation(SQLModel, table=True):
    __tablename__ = "user_locations"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    location_id: int = Field(foreign_key="cities_countries.id", index=True)

    user: Optional[User] = Relationship(back_populates="locations")
    location: Optional[CityOrCountry] = Relationship(back_populates="user_links")

    # ---------- CREATE ----------
    # Called by POST /api/cityorcountry/relation
    # Body: { "userid": 1, "cityname": "New Athens" }
    @classmethod
    def create(
        cls,
        session: Session,
        user_id: int,
        cityname: str,
    ) -> Optional["UserLocation"]:
        user = session.get(User, user_id)
        if not user:
            return None

        loc = CityOrCountry.get_by_name(session, cityname)
        if not loc:
            return None

        # avoid duplicate links
        existing = session.exec(
            select(cls)
            .where(cls.user_id == user_id)
            .where(cls.location_id == loc.id)
        ).first()
        if existing:
            return existing

        link = cls(user_id=user_id, location_id=loc.id)
        session.add(link)
        session.commit()
        session.refresh(link)
        return link

    # ---------- GET ALL FOR USER ----------
    @classmethod
    def get_all_for_user(cls, session: Session, user_id: int) -> List["UserLocation"]:
        return session.exec(select(cls).where(cls.user_id == user_id)).all()

    # ---------- DELETE ----------
    # Called by DELETE /api/cityorcountry/relation
    # Body: { "userid": 1, "cityname": "New Athens" }
    @classmethod
    def delete_by_name(
        cls,
        session: Session,
        user_id: int,
        cityname: str,
    ) -> bool:
        loc = CityOrCountry.get_by_name(session, cityname)
        if not loc:
            return False

        link = session.exec(
            select(cls)
            .where(cls.user_id == user_id)
            .where(cls.location_id == loc.id)
        ).first()
        if not link:
            return False

        session.delete(link)
        session.commit()
        return True

    @classmethod
    def delete(cls, session: Session, link_id: int) -> bool:
        link = session.get(cls, link_id)
        if not link:
            return False
        session.delete(link)
        session.commit()
        return True


# models.py  (only the BuildingActivity class shown — keep the rest as-is)

class BuildingActivity(SQLModel, table=True):
    """
    A weekly building activity record.
    `op` is either:
        - "user"    → the building is *using* the object (consumption)
        - "produce" → the building is *producing* the object (output)
    """
    __tablename__ = "building_activities"

    id: Optional[int] = Field(default=None, primary_key=True)
    building_id: int = Field(foreign_key="buildings.id", index=True)

    objectname: str = Field(index=True, max_length=150)
    op: str = Field(default="produce", max_length=20)   # "user" | "produce"
    amount: int = Field(default=0, ge=0)

    created_at: datetime.datetime = Field(default=datetime.datetime.now(datetime.timezone.utc))


    # ---------- CREATE ----------
    @classmethod
    def create(
        cls,
        session: Session,
        *,
        buildingname: str,
        objectname: str,
        op: str,
        amount: int,
    ) -> Optional["BuildingActivity"]:
        # 1) building must exist
        building = Building.get_by_name(session, buildingname)
        if not building:
            return None

        # 2) validate op
        if op not in ("use", "produce"):
            return None

        # 3) object must exist as an ArmyObject or an Asset
        obj_exists = (
            ArmyObject.get_by_name(session, objectname) is not None
            or Asset.get_by_name(session, objectname) is not None
        )
        if not obj_exists:
            return None

        activity = cls(
            building_id=building.id,
            objectname=objectname,
            op=op,
            amount=amount,
        )
        session.add(activity)
        session.commit()
        session.refresh(activity)
        return activity

    # ---------- READ ----------
    @classmethod
    def get(cls, session: Session, activity_id: int) -> Optional["BuildingActivity"]:
        return session.get(cls, activity_id)

    @classmethod
    def get_all(cls, session: Session) -> List["BuildingActivity"]:
        return session.exec(
            select(cls).order_by(cls.created_at.desc())
        ).all()

    @classmethod
    def get_all_for_building(cls, session: Session, building_id: int) -> List["BuildingActivity"]:
        return session.exec(
            select(cls)
            .where(cls.building_id == building_id)
            .order_by(cls.created_at.desc())
        ).all()

    # ---------- DELETE ----------
    @classmethod
    def delete(cls, session: Session, activity_id: int) -> bool:
        act = session.get(cls, activity_id)
        if not act:
            return False
        session.delete(act)
        session.commit()
        return True