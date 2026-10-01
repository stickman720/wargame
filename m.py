# main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session

from .database import init_db, get_session
from . import schemas
from .models import (
    User, Building, BuildingLevelCost, ArmyObject, Asset,
    CityOrCountry, UserInventory, UserLocation, UserBuilding,
    BuildingActivity,
)

app = FastAPI(title="Admin API", version="2.0.0")



@app.on_event("startup")
def on_startup():
    init_db()


def user_to_dict(u: User) -> dict:
    return {"id": u.id, "username": u.username, "email": u.email,
            "role": u.role,
            "created_at": u.created_at.isoformat() if u.created_at else None}


def building_to_dict(b: Building) -> dict:
    return {"id": b.id, "name": b.name, "usage": b.usage,
            "earns": b.earns, "max_level": b.max_level}


def levelcost_to_dict(c: BuildingLevelCost) -> dict:
    return {"id": c.id, "building_id": c.building_id, "level": c.level,
            "objectname": c.objectname, "kind": c.kind, "amount": c.amount}


def activity_to_dict(a: BuildingActivity) -> dict:
    return {"id": a.id, "building_id": a.building_id,
            "objectname": a.objectname, "op": a.op, "amount": a.amount,
            "created_at": a.created_at.isoformat() if a.created_at else None}


# ============================================================
# USERS
# ============================================================
@app.post("/api/user", status_code=201)
def create_user(body: schemas.UserCreate, session: Session = Depends(get_session)):
    try:
        u = User.create(session, username=body.username, email=body.email,
                        password=body.password, role=body.role)
    except Exception as e:
        raise HTTPException(409, str(e))
    return {"status": "success", "message": "User created successfully",
            "user": user_to_dict(u)}


@app.get("/api/user")
def list_users(session: Session = Depends(get_session)):
    return {"status": "success", "users": [user_to_dict(u) for u in User.get_all(session)]}


@app.get("/api/user/{user_id}")
def get_user(user_id: int, session: Session = Depends(get_session)):
    u = User.get(session, user_id)
    if not u: raise HTTPException(404, "User not found")
    return {"status": "success", "user": user_to_dict(u)}


@app.put("/api/user/{user_id}")
def update_user(user_id: int, body: schemas.UserUpdate,
                session: Session = Depends(get_session)):
    u = User.update(session, user_id, username=body.username, email=body.email,
                    role=body.role, password=body.password)
    if not u: raise HTTPException(404, "User not found")
    return {"status": "success", "message": "User updated successfully",
            "user": user_to_dict(u)}


@app.delete("/api/user/{user_id}")
def delete_user(user_id: int, session: Session = Depends(get_session)):
    if not User.delete(session, user_id):
        raise HTTPException(404, "User not found")
    return {"status": "success", "message": "User deleted successfully"}


# ============================================================
# BUILDINGS
# ============================================================
@app.post("/api/building", status_code=201)
def create_building(body: schemas.BuildingCreate, session: Session = Depends(get_session)):
    b = Building.create(session, name=body.name, usage=body.usage,
                        earns=body.earns, max_level=body.max_level)
    return {"status": "success", "message": "Building created successfully",
            "building": building_to_dict(b)}


@app.get("/api/building")
def list_buildings(session: Session = Depends(get_session)):
    return {"status": "success",
            "buildings": [building_to_dict(b) for b in Building.get_all(session)]}


@app.get("/api/building/{bid}")
def get_building(bid: int, session: Session = Depends(get_session)):
    b = Building.get(session, bid)
    if not b: raise HTTPException(404, "Building not found")
    return {"status": "success", "building": building_to_dict(b)}


@app.put("/api/building/{bid}")
def update_building(bid: int, body: schemas.BuildingUpdate,
                    session: Session = Depends(get_session)):
    b = Building.update(session, bid, name=body.name, usage=body.usage, earns=body.earns)
    if not b: raise HTTPException(404, "Building not found")
    return {"status": "success", "message": "Building updated successfully",
            "building": building_to_dict(b)}


@app.delete("/api/building/{bid}")
def delete_building(bid: int, session: Session = Depends(get_session)):
    if not Building.delete(session, bid):
        raise HTTPException(404, "Building not found")
    return {"status": "success", "message": "Building deleted successfully"}


# ============================================================
# BUILDING LEVEL COST  (recipe endpoints)
# ============================================================
@app.post("/api/buildinglevelcost", status_code=201)
def create_level_cost(body: schemas.BuildingLevelCostCreate,
                      session: Session = Depends(get_session)):
    row = BuildingLevelCost.create(
        session,
        buildingname=body.buildingname,
        level=body.level,
        objectname=body.objectname,
        kind=body.kind,
        amount=body.amount,
    )
    if not row:
        raise HTTPException(404,
            f"Building '{body.buildingname}' or referenced object not found, "
            f"or level < 2")
    return {"status": "success", "message": "Level cost saved",
            "level_cost": levelcost_to_dict(row)}


@app.get("/api/buildinglevelcost")
def list_level_costs(session: Session = Depends(get_session)):
    return {"status": "success",
            "level_costs": [levelcost_to_dict(c) for c in BuildingLevelCost.get_all(session)]}


@app.get("/api/buildinglevelcost/{rid}")
def get_level_cost(rid: int, session: Session = Depends(get_session)):
    c = BuildingLevelCost.get(session, rid)
    if not c: raise HTTPException(404, "Level cost not found")
    return {"status": "success", "level_cost": levelcost_to_dict(c)}


@app.get("/api/buildinglevelcost/building/{bid}")
def list_building_level_costs(bid: int, session: Session = Depends(get_session)):
    rows = BuildingLevelCost.get_all_for_building(session, bid)
    return {"status": "success",
            "level_costs": [levelcost_to_dict(c) for c in rows]}


@app.delete("/api/buildinglevelcost/{rid}")
def delete_level_cost(rid: int, session: Session = Depends(get_session)):
    if not BuildingLevelCost.delete(session, rid):
        raise HTTPException(404, "Level cost not found")
    return {"status": "success", "message": "Level cost deleted"}


# ============================================================
# UPGRADE  (the only way to advance a building)
# ============================================================
@app.post("/api/building/upgrade")
def upgrade_building(body: schemas.UpgradeBody, session: Session = Depends(get_session)):
    row, err = UserBuilding.upgrade(session, body.userid, body.buildingname)
    if err:
        raise HTTPException(400, err)
    return {"status": "success", "message": "Building upgraded successfully",
            "user_building": {"user_id": row.user_id,
                              "building_id": row.building_id,
                              "level": row.level}}


@app.get("/api/userbuilding/{userid}")
def get_user_buildings(userid: int, session: Session = Depends(get_session)):
    rows = session.exec(
        # local import to keep the file short
        __import__("sqlmodel").select(UserBuilding)
        .where(UserBuilding.user_id == userid)
    ).all()
    return {"status": "success",
            "user_buildings": [
                {"id": r.id, "user_id": r.user_id,
                 "building_id": r.building_id, "level": r.level}
                for r in rows
            ]}


# ============================================================
# ARMY / ASSET / LOCATION  (unchanged from earlier version)
# ============================================================
@app.post("/api/army", status_code=201)
def create_army(body: schemas.ArmyCreate, session: Session = Depends(get_session)):
    o = ArmyObject.create(session, name=body.name, type=body.type,
                          power=body.power, cost=body.cost)
    return {"status": "success", "message": "Army object created successfully", "army": o}


@app.get("/api/army")
def list_army(session: Session = Depends(get_session)):
    return {"status": "success", "army": ArmyObject.get_all(session)}


@app.get("/api/army/{oid}")
def get_army(oid: int, session: Session = Depends(get_session)):
    o = ArmyObject.get(session, oid)
    if not o: raise HTTPException(404, "Army object not found")
    return {"status": "success", "army": o}


@app.put("/api/army/{oid}")
def update_army(oid: int, body: schemas.ArmyUpdate, session: Session = Depends(get_session)):
    o = ArmyObject.update(session, oid, name=body.name, type=body.type,
                          power=body.power, cost=body.cost)
    if not o: raise HTTPException(404, "Army object not found")
    return {"status": "success", "message": "Army object updated successfully", "army": o}


@app.delete("/api/army/{oid}")
def delete_army(oid: int, session: Session = Depends(get_session)):
    if not ArmyObject.delete(session, oid):
        raise HTTPException(404, "Army object not found")
    return {"status": "success", "message": "Army object deleted successfully"}


@app.post("/api/asset", status_code=201)
def create_asset(body: schemas.AssetCreate, session: Session = Depends(get_session)):
    a = Asset.create(session, name=body.name, type=body.type,
                     quantity=body.quantity, value=body.value)
    return {"status": "success", "message": "Asset created successfully", "asset": a}


@app.get("/api/asset")
def list_assets(session: Session = Depends(get_session)):
    return {"status": "success", "assets": Asset.get_all(session)}


@app.get("/api/asset/{aid}")
def get_asset(aid: int, session: Session = Depends(get_session)):
    a = Asset.get(session, aid)
    if not a: raise HTTPException(404, "Asset not found")
    return {"status": "success", "asset": a}


@app.put("/api/asset/{aid}")
def update_asset(aid: int, body: schemas.AssetUpdate, session: Session = Depends(get_session)):
    a = Asset.update(session, aid, name=body.name, type=body.type,
                     quantity=body.quantity, value=body.value)
    if not a: raise HTTPException(404, "Asset not found")
    return {"status": "success", "message": "Asset updated successfully", "asset": a}


@app.delete("/api/asset/{aid}")
def delete_asset(aid: int, session: Session = Depends(get_session)):
    if not Asset.delete(session, aid):
        raise HTTPException(404, "Asset not found")
    return {"status": "success", "message": "Asset deleted successfully"}


@app.post("/api/cityorcountry", status_code=201)
def create_location(body: schemas.CityOrCountryCreate, session: Session = Depends(get_session)):
    loc = CityOrCountry.create(session, name=body.name, type=body.type,
                               population=body.population, region=body.region)
    return {"status": "success", "message": "Location created successfully", "location": loc}


@app.get("/api/cityorcountry")
def list_locations(session: Session = Depends(get_session)):
    return {"status": "success", "locations": CityOrCountry.get_all(session)}


@app.get("/api/cityorcountry/{lid}")
def get_location(lid: int, session: Session = Depends(get_session)):
    loc = CityOrCountry.get(session, lid)
    if not loc: raise HTTPException(404, "Location not found")
    return {"status": "success", "location": loc}


@app.put("/api/cityorcountry/{lid}")
def update_location(lid: int, body: schemas.CityOrCountryUpdate,
                    session: Session = Depends(get_session)):
    loc = CityOrCountry.update(session, lid, name=body.name, type=body.type,
                               population=body.population, region=body.region)
    if not loc: raise HTTPException(404, "Location not found")
    return {"status": "success", "message": "Location updated successfully", "location": loc}


@app.delete("/api/cityorcountry/{lid}")
def delete_location(lid: int, session: Session = Depends(get_session)):
    if not CityOrCountry.delete(session, lid):
        raise HTTPException(404, "Location not found")
    return {"status": "success", "message": "Location deleted successfully"}


@app.put("/api/inventory/{userid}")
def update_inventory(userid: int, body: schemas.InventoryUpdate,
                     session: Session = Depends(get_session)):
    inv = UserInventory.set_amount(session, userid, body.objectname, body.newamount)
    if not inv:
        raise HTTPException(404, f"User {userid} or object '{body.objectname}' not found")
    return {"status": "success", "message": "Inventory updated successfully",
            "inventory": {"id": inv.id, "user_id": inv.user_id,
                          "army_object_id": inv.army_object_id,
                          "asset_id": inv.asset_id, "amount": inv.amount}}


@app.post("/api/cityorcountry/relation", status_code=201)
def create_relation(body: schemas.RelationBody, session: Session = Depends(get_session)):
    link = UserLocation.create(session, body.userid, body.cityname)
    if not link:
        raise HTTPException(404, f"User {body.userid} or location '{body.cityname}' not found")
    return {"status": "success", "message": "Relation created successfully"}


@app.delete("/api/cityorcountry/relation")
def delete_relation(body: schemas.RelationBody, session: Session = Depends(get_session)):
    if not UserLocation.delete_by_name(session, body.userid, body.cityname):
        raise HTTPException(404, "Relation not found")
    return {"status": "success", "message": "Relation removed successfully"}


# ============================================================
# WEEKLY ACTIVITY
# ============================================================
@app.post("/api/buildingactivity", status_code=201)
def create_building_activity(body: schemas.BuildingActivityCreate,
                             session: Session = Depends(get_session)):
    a = BuildingActivity.create(session, buildingname=body.buildingname,
                                objectname=body.objectname,
                                op=body.op, amount=body.amount)
    if not a:
        raise HTTPException(404, f"Building '{body.buildingname}' or object "
                                f"'{body.objectname}' not found")
    return {"status": "success", "message": "Activity recorded successfully",
            "activity": activity_to_dict(a)}


@app.get("/api/buildingactivity")
def list_building_activities(session: Session = Depends(get_session)):
    return {"status": "success",
            "activities": [activity_to_dict(a) for a in BuildingActivity.get_all(session)]}


@app.get("/api/buildingactivity/{aid}")
def get_building_activity(aid: int, session: Session = Depends(get_session)):
    a = BuildingActivity.get(session, aid)
    if not a: raise HTTPException(404, "Activity not found")
    return {"status": "success", "activity": activity_to_dict(a)}


@app.delete("/api/buildingactivity/{aid}")
def delete_building_activity(aid: int, session: Session = Depends(get_session)):
    if not BuildingActivity.delete(session, aid):
        raise HTTPException(404, "Activity not found")
    return {"status": "success", "message": "Activity deleted successfully"}


# ============================================================
# 401 PAGE
# ============================================================
@app.get("/401")
def page_401():
    return FileResponse("static/401.html", status_code=401)


@app.exception_handler(401)
async def unauthorized_handler(request, exc):
    return FileResponse("static/401.html", status_code=401)