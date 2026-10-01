# models.py
from datetime import datetime , timezone
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
    created_at: datetime = Field(default=datetime.now(timezone.utc))
    last_login: Optional[datetime] = None

    inventory_items: List["UserInventory"] = Relationship(back_populates="user")
    locations: List["UserLocation"] = Relationship(back_populates="user")

    @staticmethod
    def create( session, *, username, email, password, role="user"):
        u = User(username=username, email=email, password_hash=password, role=role)
        session.add(u); session.commit(); session.refresh(u)
        return u

    @classmethod
    def get(cls, session, user_id): return session.get(cls, user_id)

    @classmethod
    def get_all(cls, session): return session.exec(select(cls)).all()

    @classmethod
    def update(cls, session, user_id, *, username=None, email=None,
               role=None, password=None):
        u = session.get(cls, user_id)
        if not u: return None
        if username is not None: u.username = username
        if email is not None:    u.email = email
        if role is not None:     u.role = role
        if password is not None: u.password_hash = password
        session.add(u); session.commit(); session.refresh(u)
        return u

    @classmethod
    def get_by_username(cls , session:Session , username):
        stat = select(User).where(User.username==username)
        u = session.exec(stat).first()
        return u

    @classmethod
    def delete(cls, session, user_id):
        u = session.get(cls, user_id)
        if not u: return False
        session.delete(u); session.commit()
        return True


# ============================================================
# BUILDING  (leveled, upgrade recipe defined per level)
# ============================================================
class Building(SQLModel, table=True):
    """
    A building is identified by its name. Its per-level *upgrade recipe*
    (i.e. what it costs to reach each level) is defined in BuildingLevelCost.
    Buildings themselves are NOT freely editable; only new levels can be added.
    """
    __tablename__ = "buildings"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=150)
    usage: str = Field(default="residential", max_length=50)
    earns: int = Field(default=0, ge=0)      # income per turn at level 1
    max_level: int = Field(default=1, ge=1)  # highest level currently defined

    level_costs: List["BuildingLevelCost"] = Relationship(back_populates="building")

    # ---- create ----
    @classmethod
    def create(cls, session, *, name, usage="residential", earns=0, max_level=1):
        b = cls(name=name, usage=usage, earns=earns, max_level=max_level)
        session.add(b); session.commit(); session.refresh(b)
        return b

    # ---- read ----
    @classmethod
    def get(cls, session, bid): return session.get(cls, bid)

    @classmethod
    def get_by_name(cls, session, name):
        return session.exec(select(cls).where(cls.name == name)).first()

    @classmethod
    def get_all(cls, session): return session.exec(select(cls)).all()

    # ---- update basic info (NOT the cost — cost is handled separately) ----
    @classmethod
    def update(cls, session, bid, *, name=None, usage=None, earns=None):
        b = session.get(cls, bid)
        if not b: return None
        if name is not None:  b.name = name
        if usage is not None: b.usage = usage
        if earns is not None: b.earns = earns
        session.add(b); session.commit(); session.refresh(b)
        return b

    # ---- delete ----
    @classmethod
    def delete(cls, session, bid):
        b = session.get(cls, bid)
        if not b: return False
        session.delete(b); session.commit()
        return True


# ============================================================
# BUILDING LEVEL COST  (recipe per level)
# ============================================================
class BuildingLevelCost(SQLModel, table=True):
    """
    One ingredient in the recipe to reach `level` of `building`.
    `objectname` refers to EITHER:
      - an Asset.name   (kind = "asset")
      - a Building.name (kind = "building")  ← yes, buildings can require other buildings
      - money            (kind = "money")    ← optional, still supported
    """
    __tablename__ = "building_level_costs"

    id: Optional[int] = Field(default=None, primary_key=True)
    building_id: int = Field(foreign_key="buildings.id", index=True)
    level: int = Field(index=True, ge=2)         # level this recipe unlocks
    objectname: str = Field(index=True, max_length=150)
    kind: str = Field(default="asset", max_length=20)  # "asset" | "building" | "money"
    amount: int = Field(default=0, ge=0)

    building: Optional[Building] = Relationship(back_populates="level_costs")

    # ---- create ----
    @classmethod
    def create(cls, session, *, buildingname, level, objectname, kind, amount):
        b = Building.get_by_name(session, buildingname)
        if not b:
            print(buildingname) 
            return None
        if level < 1: return None

        # validate the referenced object exists (except money)
        if kind == "asset" and Asset.get_by_name(session, objectname) is None:
            return None
        if kind == "building" and Building.get_by_name(session, objectname) is None:
            return None
        if kind == "money":
            objectname = "money"   # normalise

        # upsert: if the same (building, level, objectname) exists, update it
        existing = session.exec(
            select(cls)
            .where(cls.building_id == b.id)
            .where(cls.level == level)
            .where(cls.objectname == objectname)
        ).first()

        if existing:
            existing.kind = kind
            existing.amount = amount
            session.add(existing); session.commit(); session.refresh(existing)
            return existing

        row = cls(building_id=b.id, level=level,
                  objectname=objectname, kind=kind, amount=amount)
        session.add(row); session.commit(); session.refresh(row)

        if level > b.max_level:
            b.max_level = level
            session.add(b); session.commit(); session.refresh(b)

        return row

    # ---- read ----
    @classmethod
    def get(cls, session, rid): return session.get(cls, rid)

    @classmethod
    def get_all(cls, session):
        return session.exec(select(cls)).all()

    @classmethod
    def get_recipe(cls, session, building_id, level):
        """Return the full recipe (list of BuildingLevelCost) for a given level."""
        return session.exec(
            select(cls)
            .where(cls.building_id == building_id)
            .where(cls.level == level)
        ).all()

    @classmethod
    def get_all_for_building(cls, session, building_id):
        return session.exec(
            select(cls)
            .where(cls.building_id == building_id)
            .order_by(cls.level)
        ).all()

    # ---- delete ----
    @classmethod
    def delete(cls, session, rid):
        row = session.get(cls, rid)
        if not row: return False
        session.delete(row); session.commit()
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

    @classmethod
    def create(cls, session, *, name, type="infantry", power=0, cost=0):
        o = cls(name=name, type=type, power=power, cost=cost)
        session.add(o); session.commit(); session.refresh(o)
        return o

    @classmethod
    def get(cls, session, oid): return session.get(cls, oid)

    @classmethod
    def get_by_name(cls, session, name):
        return session.exec(select(cls).where(cls.name == name)).first()

    @classmethod
    def get_all(cls, session): return session.exec(select(cls)).all()

    @classmethod
    def update(cls, session, oid, *, name=None, type=None, power=None, cost=None):
        o = session.get(cls, oid)
        if not o: return None
        if name is not None:  o.name = name
        if type is not None:  o.type = type
        if power is not None: o.power = power
        if cost is not None:  o.cost = cost
        session.add(o); session.commit(); session.refresh(o)
        return o

    @classmethod
    def delete(cls, session, oid):
        o = session.get(cls, oid)
        if not o: return False
        session.delete(o); session.commit()
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

    @classmethod
    def create(cls, session, *, name, type="resource", quantity=0, value=0):
        a = cls(name=name, type=type, quantity=quantity, value=value)
        session.add(a); session.commit(); session.refresh(a)
        return a

    @classmethod
    def get(cls, session, aid): return session.get(cls, aid)

    @classmethod
    def get_by_name(cls, session, name):
        return session.exec(select(cls).where(cls.name == name)).first()

    @classmethod
    def get_all(cls, session): return session.exec(select(cls)).all()

    @classmethod
    def update(cls, session, aid, *, name=None, type=None, quantity=None, value=None):
        a = session.get(cls, aid)
        if not a: return None
        if name is not None:     a.name = name
        if type is not None:     a.type = type
        if quantity is not None: a.quantity = quantity
        if value is not None:    a.value = value
        session.add(a); session.commit(); session.refresh(a)
        return a

    @classmethod
    def delete(cls, session, aid):
        a = session.get(cls, aid)
        if not a: return False
        session.delete(a); session.commit()
        return True


# ============================================================
# CITY / COUNTRY
# ============================================================
class CityOrCountry(SQLModel, table=True):
    __tablename__ = "cities_countries"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=150)
    type: str = Field(default="city", max_length=20)
    population: int = Field(default=0, ge=0)
    region: Optional[str] = Field(default=None, max_length=100)
    owner_id:int
    user_links: List["UserLocation"] = Relationship(back_populates="location")

    @classmethod
    def create(cls, session, *, name, type="city", population=0, region=None , owner_id):
        loc = cls(name=name, type=type, population=population, region=region , owner_id = owner_id)
        session.add(loc); session.commit(); session.refresh(loc)
        return loc

    @classmethod
    def get(cls, session, lid): return session.get(cls, lid)

    @classmethod
    def get_by_name(cls, session, name):
        return session.exec(select(cls).where(cls.name == name)).first()

    @classmethod
    def get_all(cls, session): return session.exec(select(cls)).all()

    @classmethod
    def update(cls, session, lid, *, name=None, type=None, population=None, region=None):
        loc = session.get(cls, lid)
        if not loc: return None
        if name is not None:       loc.name = name
        if type is not None:       loc.type = type
        if population is not None: loc.population = population
        if region is not None:     loc.region = region
        session.add(loc); session.commit(); session.refresh(loc)
        return loc

    @classmethod
    def delete(cls, session, lid):
        loc = session.get(cls, lid)
        if not loc: return False
        session.delete(loc); session.commit()
        return True


# ============================================================
# USER INVENTORY
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

    @classmethod
    def set_amount(cls, session, user_id, objectname, newamount):
        if not session.get(User, user_id): return None
        army = ArmyObject.get_by_name(session, objectname)
        if army:
            inv = session.exec(
                select(cls).where(cls.user_id == user_id)
                          .where(cls.army_object_id == army.id)
            ).first()
            if inv is None:
                inv = cls(user_id=user_id, army_object_id=army.id, amount=0)
                session.add(inv)
            inv.amount = newamount
            session.commit(); session.refresh(inv)
            return inv
        asset = Asset.get_by_name(session, objectname)
        if asset:
            inv = session.exec(
                select(cls).where(cls.user_id == user_id)
                          .where(cls.asset_id == asset.id)
            ).first()
            if inv is None:
                inv = cls(user_id=user_id, asset_id=asset.id, amount=0)
                session.add(inv)
            inv.amount = newamount
            session.commit(); session.refresh(inv)
            return inv
        return None

    @classmethod
    def get_amount(cls, session, user_id, objectname):
        """Return the user's current amount of an object (army or asset), 0 if none."""
        army = ArmyObject.get_by_name(session, objectname)
        if army:
            inv = session.exec(
                select(cls).where(cls.user_id == user_id)
                          .where(cls.army_object_id == army.id)
            ).first()
            return inv.amount if inv else 0
        asset = Asset.get_by_name(session, objectname)
        if asset:
            inv = session.exec(
                select(cls).where(cls.user_id == user_id)
                          .where(cls.asset_id == asset.id)
            ).first()
            return inv.amount if inv else 0
        return 0

    @classmethod
    def add_amount(cls, session, user_id, objectname, delta):
        if not session.get(User, user_id): return None
        current = cls.get_amount(session, user_id, objectname)
        return cls.set_amount(session, user_id, objectname, max(0, current + delta))

    @classmethod
    def get_all_for_user(cls, session, user_id):
        return session.exec(select(cls).where(cls.user_id == user_id)).all()


# ============================================================
# USER ↔ LOCATION
# ============================================================
class UserLocation(SQLModel, table=True):
    __tablename__ = "user_locations"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    location_id: int = Field(foreign_key="cities_countries.id", index=True)

    user: Optional[User] = Relationship(back_populates="locations")
    location: Optional[CityOrCountry] = Relationship(back_populates="user_links")

    @classmethod
    def create(cls, session, user_id, cityname):
        if not session.get(User, user_id): return None
        loc = CityOrCountry.get_by_name(session, cityname)
        if not loc: return None
        existing = session.exec(
            select(cls).where(cls.user_id == user_id)
                      .where(cls.location_id == loc.id)
        ).first()
        if existing: return existing
        link = cls(user_id=user_id, location_id=loc.id)
        session.add(link); session.commit(); session.refresh(link)
        return link

    @classmethod
    def delete_by_name(cls, session, user_id, cityname):
        loc = CityOrCountry.get_by_name(session, cityname)
        if not loc: return False
        link = session.exec(
            select(cls).where(cls.user_id == user_id)
                      .where(cls.location_id == loc.id)
        ).first()
        if not link: return False
        session.delete(link); session.commit()
        return True


# ============================================================
# USER BUILDING  (which level a user owns of each building)
# ============================================================
class UserBuilding(SQLModel, table=True):
    __tablename__ = "user_buildings"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    building_id: int = Field(foreign_key="buildings.id", index=True)
    level: int = Field(default=1, ge=1)

    @classmethod
    def get_or_create(cls, session, user_id, building_id):
        if not session.get(User, user_id): return None
        if not session.get(Building, building_id): return None
        row = session.exec(
            select(cls).where(cls.user_id == user_id)
                      .where(cls.building_id == building_id)
        ).first()
        if row: return row
        row = cls(user_id=user_id, building_id=building_id, level=0)
        session.add(row); session.commit(); session.refresh(row)
        return row

    # ---- upgrade: only path that can change a building's level for a user ----
    @classmethod
    def upgrade(cls, session, user_id, buildingname):
        """
        Check the recipe of level (current + 1). Deduct required assets/money
        from the user's inventory, and check that required buildings are owned
        at the correct level. On success, raise the user's level by 1.
        """
        building = Building.get_by_name(session, buildingname)
        if not building: return None, "Building not found"

        row = cls.get_or_create(session, user_id, building.id)
        if row is None: return None, "User not found"

        next_level = row.level + 1
        if next_level > building.max_level:
            return None, f"Building has no level {next_level} yet"

        recipe = BuildingLevelCost.get_recipe(session, building.id, next_level)
        if not recipe:
            return None, f"No recipe defined for level {next_level}"

        # 1) validate all requirements
        for item in recipe:
            if item.kind == "money":
                # treat money as a special "money" asset held in inventory
                have = UserInventory.get_amount(session, user_id, "money")
                if have < item.amount:
                    return None, f"Not enough money (need {item.amount}, have {have})"
            elif item.kind == "asset":
                have = UserInventory.get_amount(session, user_id, item.objectname)
                if have < item.amount:
                    return None, f"Not enough {item.objectname} (need {item.amount}, have {have})"
            elif item.kind == "building":
                req_b = Building.get_by_name(session, item.objectname)
                if not req_b:
                    return None, f"Required building '{item.objectname}' not found"
                req_row = cls.get_or_create(session, user_id, req_b.id)
                # The amount for a "building" ingredient = required level
                if req_row.level < item.amount:
                    return None, (
                        f"'{item.objectname}' must be level {item.amount} "
                        f"(you have level {req_row.level})"
                    )

        # 2) deduct
        for item in recipe:
            if item.kind == "money":
                UserInventory.add_amount(session, user_id, "money", -item.amount)
            elif item.kind == "asset":
                UserInventory.add_amount(session, user_id, item.objectname, -item.amount)
            # buildings are not consumed

        row.level = next_level
        session.add(row); session.commit(); session.refresh(row)
        return row, None


# ============================================================
# BUILDING WEEKLY ACTIVITY  (using / producing)
# ============================================================
class BuildingActivity(SQLModel, table=True):
    __tablename__ = "building_activities"

    id: Optional[int] = Field(default=None, primary_key=True)
    building_id: int = Field(foreign_key="buildings.id", index=True)
    objectname: str = Field(index=True, max_length=150)
    op: str = Field(default="produce", max_length=20)   # "user" | "produce"
    amount: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    building: Optional[Building] = Relationship()

    @classmethod
    def create(cls, session, *, buildingname, objectname, op, amount):
        b = Building.get_by_name(session, buildingname)
        if not b: return None
        if op not in ("user", "produce"): return None
        if (ArmyObject.get_by_name(session, objectname) is None
                and Asset.get_by_name(session, objectname) is None):
            return None
        row = cls(building_id=b.id, objectname=objectname, op=op, amount=amount)
        session.add(row); session.commit(); session.refresh(row)
        return row

    @classmethod
    def get(cls, session, aid): return session.get(cls, aid)

    @classmethod
    def get_all(cls, session):
        return session.exec(select(cls).order_by(cls.created_at.desc())).all()

    @classmethod
    def delete(cls, session, aid):
        row = session.get(cls, aid)
        if not row: return False
        session.delete(row); session.commit()
        return True