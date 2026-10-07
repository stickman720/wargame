# user_router.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from database.database import get_session
from database.models import (
    User, Building, BuildingLevelCost, ArmyObject, Asset,
    CityOrCountry, UserInventory, UserLocation, UserBuilding,
    BuildingActivity,
)

router = APIRouter(prefix="/api/me", tags=["user-panel"])


# ============================================================
# AUTH DEPENDENCY
# ============================================================
def current_user(
    x_user_id: Optional[int] = Header(default=None, alias="X-User-Id"),
    session: Session = Depends(get_session),
) -> User:
    if x_user_id is None:
        raise HTTPException(401, "Missing X-User-Id header")
    user = session.get(User, x_user_id)
    if not user:
        raise HTTPException(401, "Invalid user")
    return user


# ============================================================
# PROFILE
# ============================================================
@router.get("/profile")
def get_profile(user: User = Depends(current_user)):
    return {
        "status": "success",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
    }


# ============================================================
# INVENTORY
# ============================================================
@router.get("/inventory")
def get_inventory(user: User = Depends(current_user),
                  session: Session = Depends(get_session)):
    rows = UserInventory.get_all_for_user(session, user.id)
    items = []
    for r in rows:
        entry = {"id": r.id, "amount": r.amount}
        if r.army_object_id:
            obj = session.get(ArmyObject, r.army_object_id)
            if obj:
                entry.update({"kind": "army", "name": obj.name, "type": obj.type,
                              "power": obj.power, "cost": obj.cost})
        elif r.asset_id:
            a = session.get(Asset, r.asset_id)
            if a:
                entry.update({"kind": "asset", "name": a.name,
                              "type": a.type, "value": a.value})
        items.append(entry)
    return {"status": "success", "inventory": items}


# ============================================================
# BUILDINGS — shared payload builder
# ============================================================
def _building_payload(session: Session, b: Building, level: int, amount: int) -> dict:
    next_level = level + 1
    next_recipe = []
    if next_level <= b.max_level:
        for c in BuildingLevelCost.get_recipe(session, b.id, next_level):
            next_recipe.append({
                "objectname": c.objectname,
                "kind": c.kind,
                "amount": c.amount,
            })
    return {
        "id": b.id, "name": b.name, "usage": b.usage, "earns": b.earns,
        "max_level": b.max_level,
        "current_level": level,
        "amount": amount,                                  # ← NEW
        "next_level": next_level if next_level <= b.max_level else None,
        "next_recipe": next_recipe,
    }

# ---------- list my buildings ----------
@router.get("/buildings")
def get_my_buildings(user: User = Depends(current_user),
                     session: Session = Depends(get_session)):
    rows = session.exec(
        select(UserBuilding).where(UserBuilding.user_id == user.id)
    ).all()
    out = []
    for r in rows:
        b = session.get(Building, r.building_id)
        if b and r.level >= 1 and r.amount >= 1:
            out.append(_building_payload(session, b, r.level, r.amount))
    return {"status": "success", "buildings": out}

# ---------- list available buildings ----------
@router.get("/buildings/available")
def get_available_buildings(user: User = Depends(current_user),
                            session: Session = Depends(get_session)):
    # With multi-copy ownership, every building is always buildable again.
    out = [
        {"id": b.id, "name": b.name, "usage": b.usage,
         "earns": b.earns, "max_level": b.max_level}
        for b in Building.get_all(session)
    ]
    return {"status": "success", "available": out}

# ============================================================
# CREATE A BRAND-NEW BUILDING  (user-initiated)
# ============================================================
class NewBuildingBody(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    usage: str = Field(default="residential")
    earns: int = Field(default=0, ge=0)


@router.post("/buildings/create", status_code=201)
def create_my_building(
    body: NewBuildingBody,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Name is required")

    existing = Building.get_by_name(session, name)
    if existing:
        raise HTTPException(409, "A building with that name already exists")

    b = Building.create(session, name=name, usage=body.usage,
                        earns=body.earns, max_level=1)

    row = UserBuilding(user_id=user.id, building_id=b.id, level=1, amount=1)
    session.add(row); session.commit(); session.refresh(row)

    return {
        "status": "success",
        "message": "Building created and added to your empire",
        "building": _building_payload(session, b, row.level, row.amount),
    }

# ---------- claim (kept for compatibility) ----------
@router.post("/buildings/{building_id}/claim")
def claim_building(building_id: int,
                   user: User = Depends(current_user),
                   session: Session = Depends(get_session)):
    b = session.get(Building, building_id)
    if not b:
        raise HTTPException(404, "Building not found")
    row = UserBuilding.get_or_create(session, user.id, b.id)
    if not row:
        raise HTTPException(400, "Cannot claim this building")
    if row.level < 1:
        row.level = 1
    row.amount += 1
    session.add(row); session.commit(); session.refresh(row)
    return {"status": "success", "message": "Building claimed",
            "building": _building_payload(session, b, row.level, row.amount)}

# ---------- upgrade ----------
@router.post("/buildings/{building_id}/upgrade")
def upgrade_building(building_id: int,
                     user: User = Depends(current_user),
                     session: Session = Depends(get_session)):
    b = session.get(Building, building_id)
    if not b:
        raise HTTPException(404, "Building not found")
    row, err = UserBuilding.upgrade(session, user.id, b.name)
    if err:
        raise HTTPException(400, {"message": "Upgrade failed", "missing": err})
    return {"status": "success", "message": "Building upgraded",
            "building": _building_payload(session, b, row.level, row.amount)}

# ---------- requirements (level 1 recipe + missing list) ----------
@router.get("/buildings/{building_id}/requirements")
def get_building_requirements(building_id: int,
                              user: User = Depends(current_user),
                              session: Session = Depends(get_session)):
    b = session.get(Building, building_id)
    if not b:
        raise HTTPException(404, "Building not found")

    check = UserBuilding.check_requirements(session, user.id, building_id, level=1)

    recipe = [{
        "kind": c.kind, "objectname": c.objectname, "amount": c.amount,
    } for c in check["recipe"]]

    return {
        "status": "success",
        "building": {"id": b.id, "name": b.name,
                     "usage": b.usage, "earns": b.earns},
        "recipe": recipe,
        "ok": check["ok"],
        "missing": check["missing"],
    }


# ---------- build (level 1, consumes recipe) ----------
@router.post("/buildings/{building_id}/build")
def build_new_building(building_id: int,
                       user: User = Depends(current_user),
                       session: Session = Depends(get_session)):
    row, err = UserBuilding.build_new(session, user.id, building_id)
    if err:
        raise HTTPException(400, {"message": "Cannot build", "missing": err})
    b = session.get(Building, building_id)
    return {"status": "success", "message": "Building constructed",
            "building": _building_payload(session, b, row.level, row.amount)}

# ============================================================
# LOCATIONS
# ============================================================
@router.get("/locations")
def get_my_locations(user: User = Depends(current_user),
                     session: Session = Depends(get_session)):
    rows = CityOrCountry.get_by_owner(session, user.id)
    return {"status": "success",
            "locations": [{"id": l.id, "name": l.name, "type": l.type,
                           "population": l.population, "region": l.region}
                          for l in rows]}


# ============================================================
# ACTIVITY
# ============================================================
@router.get("/activity")
def get_my_activity(user: User = Depends(current_user),
                    session: Session = Depends(get_session)):
    owned_ids = {
        r.building_id for r in session.exec(
            select(UserBuilding)
            .where(UserBuilding.user_id == user.id)
            .where(UserBuilding.level >= 1)
        ).all()
    }
    out = []
    for a in BuildingActivity.get_all(session):
        if a.building_id in owned_ids:
            b = session.get(Building, a.building_id)
            out.append({
                "id": a.id, "building_id": a.building_id,
                "building_name": b.name if b else None,
                "objectname": a.objectname, "op": a.op,
                "amount": a.amount,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            })
    return {"status": "success", "activities": out}


# ============================================================
# TRANSPORT — send army objects / assets to another user
# ============================================================
class TransportBody(BaseModel):
    to_username: str = Field(..., min_length=1, max_length=100)
    objectname: str = Field(..., min_length=1, max_length=150)
    amount: int = Field(..., ge=1)


@router.post("/transport")
def transport_object(
    body: TransportBody,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    """
    Send `amount` of an army object or asset from the current user to another user.

    Rules:
      - Recipient must exist (looked up by username or email).
      - Sender cannot send to themselves.
      - Sender must have at least `amount` of the object.
      - The object must exist as either an ArmyObject or an Asset.
    """
    # 1) resolve recipient
    to_username = body.to_username.strip()
    recipient = User.get_by_username_or_email(session, to_username)
    if not recipient:
        raise HTTPException(404, f"Recipient '{to_username}' not found")

    if recipient.id == user.id:
        raise HTTPException(400, "You cannot send to yourself")

    # 2) resolve object (army or asset)
    army = ArmyObject.get_by_name(session, body.objectname)
    asset = None
    if not army:
        asset = Asset.get_by_name(session, body.objectname)
    if not army and not asset:
        raise HTTPException(404, f"Object '{body.objectname}' not found")

    # 3) check sender has enough
    sender_amount = UserInventory.get_amount(session, user.id, body.objectname)
    if sender_amount < body.amount:
        raise HTTPException(
            400,
            f"Not enough {body.objectname} "
            f"(you have {sender_amount}, trying to send {body.amount})"
        )

    # 4) deduct from sender, add to recipient
    UserInventory.add_amount(session, user.id, body.objectname, -body.amount)
    UserInventory.add_amount(session, recipient.id, body.objectname, +body.amount)

    # 5) read back the sender's new amount
    new_amount = UserInventory.get_amount(session, user.id, body.objectname)

    return {
        "status": "success",
        "message": f"Sent {body.amount}× {body.objectname} to {recipient.username}",
        "transport": {
            "from_user_id": user.id,
            "to_user_id": recipient.id,
            "to_username": recipient.username,
            "objectname": body.objectname,
            "amount": body.amount,
            "remaining": new_amount,
        },
    }


@router.get("/transport/history")
def transport_history(user: User = Depends(current_user),
                      session: Session = Depends(get_session)):
    """
    Optional: return the current user's inventory so the frontend can show
    what's available to send. (We're reusing the inventory endpoint, so this
    is just a friendly alias.)
    """
    return get_inventory(user=user, session=session)

# ============================================================
# ATTACK — user submits an attack request
# ============================================================
class AttackUnit(BaseModel):
    objectname: str = Field(..., min_length=1, max_length=150)
    amount: int = Field(..., ge=1)


class AttackBody(BaseModel):
    target_username: str = Field(..., min_length=1, max_length=100)
    role_message: str = Field(default="", max_length=500)
    units: list[AttackUnit] = Field(..., min_items=1)


@router.post("/attack", status_code=201)
def submit_attack(
    body: AttackBody,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    from database.models import AttackRequest   # local import to avoid circular

    # 1) resolve target
    target = User.get_by_username_or_email(session, body.target_username.strip())
    if not target:
        raise HTTPException(404, f"Target '{body.target_username}' not found")
    if target.id == user.id:
        raise HTTPException(400, "You cannot attack yourself")

    # 2) validate each unit exists AND the attacker actually owns enough
    for u in body.units:
        obj_army = ArmyObject.get_by_name(session, u.objectname)
        obj_asset = None if obj_army else Asset.get_by_name(session, u.objectname)
        if not obj_army and not obj_asset:
            raise HTTPException(404, f"Object '{u.objectname}' not found")
        have = UserInventory.get_amount(session, user.id, u.objectname)
        if have < u.amount:
            raise HTTPException(
                400,
                f"Not enough {u.objectname} (you have {have}, requested {u.amount})"
            )

    # 3) store the request
    row = AttackRequest.create(
        session,
        attacker_id=user.id,
        target_id=target.id,
        units=[{"objectname": u.objectname, "amount": u.amount} for u in body.units],
        role_message=body.role_message.strip(),
    )

    return {
        "status": "success",
        "message": "Attack submitted for review",
        "attack": {
            "id": row.id,
            "attacker_id": row.attacker_id,
            "target_id": row.target_id,
            "target_username": target.username,
            "role_message": row.role_message,
            "units": row.units(),
            "status": row.status,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        },
    }