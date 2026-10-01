

from fastapi import FastAPI , Request , Form , Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlmodel import Session
import uuid


from database.database import get_session , init
from database.models import *
from database.models import User,Building,ArmyObject,Asset,CityOrCountry,UserInventory,UserLocation,BuildingActivity
init()


app = FastAPI()
app.mount("/static" , StaticFiles(directory="static"),"static")


tmp = Jinja2Templates("templates")




cache = {}








@app.get("/")
def index(r:Request , session : Session = Depends(get_session)):
    return(tmp.TemplateResponse(request=r , name="login.html"))

@app.post("/admin/{tk}")
def index(r:Request,tk:str):
    print(tk)
    print(cache)
    if tk in cache:
        cache.pop(tk)
        return(tmp.TemplateResponse(request=r , name="adminpage.html"))
    return tmp.TemplateResponse(r , name="401.html")





#====================================================
#auth-e
#====================================================
@app.post("/api/auth/login")
def index(r:Request, username:str = Form(...) , password:str = Form(...),session:Session=Depends(get_session)):
    u = User.get_by_username(session,username=username)
    if u == None or u.password_hash != password:
        return tmp.TemplateResponse(request=r , name="401.html")

    if u.role == "admin":
        tk = str(uuid.uuid4())
        cache[tk] = ""
        return RedirectResponse(f"/admin/{tk}")





# main.py
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse

import schemas



# ============================================================
# HELPER: shape a "user" response
# ============================================================
def user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


# ============================================================
# USERS
# ============================================================
@app.post("/api/user", status_code=201)
def create_user(body: schemas.UserCreate, session: Session = Depends(get_session)):
    
    user = User.create(
        session,
        username=body.username,
        email=body.email,
        password=body.password,
        role=body.role,
    )
    
    return {"status": "success", "message": "User created successfully",
            "user": user_to_dict(user)}


@app.get("/api/user")
def list_users(session: Session = Depends(get_session)):
    users = User.get_all(session)
    if not users:
        return {"status": "success", "message": "No users found", "users": []}
    return {"status": "success", "users": [user_to_dict(u) for u in users]}


@app.get("/api/user/{user_id}")
def get_user(user_id: int, session: Session = Depends(get_session)):
    user = User.get(session, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return {"status": "success", "user": user_to_dict(user)}


@app.put("/api/user/{user_id}")
def update_user(user_id: int, body: schemas.UserUpdate,
                session: Session = Depends(get_session)):
    user = User.update(
        session, user_id,
        username=body.username,
        email=body.email,
        role=body.role,
        password=body.password,
    )
    if not user:
        raise HTTPException(404, "User not found")
    return {"status": "success", "message": "User updated successfully",
            "user": user_to_dict(user)}


@app.delete("/api/user/{user_id}")
def delete_user(user_id: int, session: Session = Depends(get_session)):
    ok = User.delete(session, user_id)
    if not ok:
        raise HTTPException(404, "User not found")
    return {"status": "success", "message": "User deleted successfully"}


# ============================================================
# BUILDINGS
# ============================================================
@app.post("/api/building", status_code=201)
def create_building(body: schemas.BuildingCreate,
                    session: Session = Depends(get_session)):
    b = Building.create(
        session,
        name=body.name, usage=body.usage, earns=body.earns,
    
    )
    return {"status": "success", "message": "Building created successfully",
            "building": b}


@app.get("/api/building")
def list_buildings(session: Session = Depends(get_session)):
    buildings = Building.get_all(session)
    return {"status": "success", "buildings": buildings}


@app.get("/api/building/{building_id}")
def get_building(building_id: int, session: Session = Depends(get_session)):
    b = Building.get(session, building_id)
    if not b:
        raise HTTPException(404, "Building not found")
    return {"status": "success", "building": b}


@app.put("/api/building/{building_id}")
def update_building(building_id: int, body: schemas.BuildingUpdate,
                    session: Session = Depends(get_session)):
    b = Building.update(
        session, building_id,
        name=body.name, usage=body.usage, earns=body.earns,
        create_cost=body.create_cost, update_cost=body.update_cost,
    )
    if not b:
        raise HTTPException(404, "Building not found")
    return {"status": "success", "message": "Building updated successfully",
            "building": b}


@app.delete("/api/building/{building_id}")
def delete_building(building_id: int, session: Session = Depends(get_session)):
    ok = Building.delete(session, building_id)
    if not ok:
        raise HTTPException(404, "Building not found")
    return {"status": "success", "message": "Building deleted successfully"}


# ============================================================
# ARMY OBJECTS
# ============================================================
@app.post("/api/army", status_code=201)
def create_army(body: schemas.ArmyCreate, session: Session = Depends(get_session)):
    obj = ArmyObject.create(
        session, name=body.name, type=body.type,
        power=body.power, cost=body.cost,
    )
    return {"status": "success", "message": "Army object created successfully",
            "army": obj}


@app.get("/api/army")
def list_army(session: Session = Depends(get_session)):
    return {"status": "success", "army": ArmyObject.get_all(session)}


@app.get("/api/army/{army_id}")
def get_army(army_id: int, session: Session = Depends(get_session)):
    obj = ArmyObject.get(session, army_id)
    if not obj:
        raise HTTPException(404, "Army object not found")
    return {"status": "success", "army": obj}


@app.put("/api/army/{army_id}")
def update_army(army_id: int, body: schemas.ArmyUpdate,
                session: Session = Depends(get_session)):
    obj = ArmyObject.update(
        session, army_id,
        name=body.name, type=body.type,
        power=body.power, cost=body.cost,
    )
    if not obj:
        raise HTTPException(404, "Army object not found")
    return {"status": "success", "message": "Army object updated successfully",
            "army": obj}


@app.delete("/api/army/{army_id}")
def delete_army(army_id: int, session: Session = Depends(get_session)):
    ok = ArmyObject.delete(session, army_id)
    if not ok:
        raise HTTPException(404, "Army object not found")
    return {"status": "success", "message": "Army object deleted successfully"}


# ============================================================
# ASSETS
# ============================================================
@app.post("/api/asset", status_code=201)
def create_asset(body: schemas.AssetCreate, session: Session = Depends(get_session)):
    a = Asset.create(
        session, name=body.name, type=body.type,
        quantity=body.quantity, value=body.value,
    )
    return {"status": "success", "message": "Asset created successfully",
            "asset": a}


@app.get("/api/asset")
def list_assets(session: Session = Depends(get_session)):
    return {"status": "success", "assets": Asset.get_all(session)}


@app.get("/api/asset/{asset_id}")
def get_asset(asset_id: int, session: Session = Depends(get_session)):
    a = Asset.get(session, asset_id)
    if not a:
        raise HTTPException(404, "Asset not found")
    return {"status": "success", "asset": a}


@app.put("/api/asset/{asset_id}")
def update_asset(asset_id: int, body: schemas.AssetUpdate,
                 session: Session = Depends(get_session)):
    a = Asset.update(
        session, asset_id,
        name=body.name, type=body.type,
        quantity=body.quantity, value=body.value,
    )
    if not a:
        raise HTTPException(404, "Asset not found")
    return {"status": "success", "message": "Asset updated successfully",
            "asset": a}


@app.delete("/api/asset/{asset_id}")
def delete_asset(asset_id: int, session: Session = Depends(get_session)):
    ok = Asset.delete(session, asset_id)
    if not ok:
        raise HTTPException(404, "Asset not found")
    return {"status": "success", "message": "Asset deleted successfully"}


# ============================================================
# CITY / COUNTRY
# ============================================================
@app.post("/api/cityorcountry", status_code=201)
def create_location(body: schemas.CityOrCountryCreate,
                    session: Session = Depends(get_session)):
    loc = CityOrCountry.create(
        session, name=body.name, type=body.type,
        population=body.population, region=body.region,owner_id=body.owner_id
    )
    return {"status": "success", "message": "Location created successfully",
            "location": loc}


@app.get("/api/cityorcountry")
def list_locations(session: Session = Depends(get_session)):
    return {"status": "success", "locations": CityOrCountry.get_all(session)}


@app.get("/api/cityorcountry/{loc_id}")
def get_location(loc_id: int, session: Session = Depends(get_session)):
    loc = CityOrCountry.get(session, loc_id)
    if not loc:
        raise HTTPException(404, "Location not found")
    return {"status": "success", "location": loc}


@app.put("/api/cityorcountry/{loc_id}")
def update_location(loc_id: int, body: schemas.CityOrCountryUpdate,
                    session: Session = Depends(get_session)):
    loc = CityOrCountry.update(
        session, loc_id,
        name=body.name, type=body.type,
        population=body.population, region=body.region,
    )
    if not loc:
        raise HTTPException(404, "Location not found")
    return {"status": "success", "message": "Location updated successfully",
            "location": loc}


@app.delete("/api/cityorcountry/{loc_id}")
def delete_location(loc_id: int, session: Session = Depends(get_session)):
    ok = CityOrCountry.delete(session, loc_id)
    if not ok:
        raise HTTPException(404, "Location not found")
    return {"status": "success", "message": "Location deleted successfully"}


# ============================================================
# INVENTORY  (User ↔ Army / Asset quantity)
# ============================================================
@app.put("/api/inventory/{userid}")
def update_inventory(userid: int, body: schemas.InventoryUpdate,
                     session: Session = Depends(get_session)):
    inv = UserInventory.set_amount(
        session,
        user_id=userid,
        objectname=body.objectname,
        newamount=body.newamount,
    )
    if not inv:
        raise HTTPException(
            404,
            f"User {userid} or object '{body.objectname}' not found",
        )
    return {
        "status": "success",
        "message": "Inventory updated successfully",
        "inventory": {
            "id": inv.id,
            "user_id": inv.user_id,
            "army_object_id": inv.army_object_id,
            "asset_id": inv.asset_id,
            "amount": inv.amount,
        },
    }


# ============================================================
# RELATIONS  (User ↔ City / Country)
# ============================================================
@app.post("/api/cityorcountry/relation", status_code=201)
def create_relation(body: schemas.RelationBody,
                    session: Session = Depends(get_session)):
    link = UserLocation.create(session, body.userid, body.cityname)
    if not link:
        raise HTTPException(
            404,
            f"User {body.userid} or location '{body.cityname}' not found",
        )
    return {
        "status": "success",
        "message": "Relation created successfully",
        "relation": {"userid": link.user_id, "location_id": link.location_id},
    }


@app.delete("/api/cityorcountry/relation")
def delete_relation(body: schemas.RelationBody,
                    session: Session = Depends(get_session)):
    ok = UserLocation.delete_by_name(session, body.userid, body.cityname)
    if not ok:
        raise HTTPException(
            404,
            f"Relation between user {body.userid} and '{body.cityname}' not found",
        )
    return {"status": "success", "message": "Relation removed successfully"}


# ============================================================
# 401 PAGE
# ============================================================
@app.get("/401")
def page_401():
    return FileResponse("static/401.html", status_code=401)


# ============================================================
# GLOBAL 401 HANDLER — returns HTML for 401s
# ============================================================
@app.exception_handler(401)
async def unauthorized_handler(request, exc):
    return FileResponse("static/401.html", status_code=401)




# main.py  (only the BuildingActivity section shown)

def activity_to_dict(a: BuildingActivity) -> dict:
    return {
        "id": a.id,
        "building_id": a.building_id,
        "objectname": a.objectname,
        "op": a.op,
        "amount": a.amount,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@app.post("/api/buildingactivity", status_code=201)
def create_building_activity(body: schemas.BuildingActivityCreate,
                             session: Session = Depends(get_session)):
    activity = BuildingActivity.create(
        session,
        buildingname=body.buildingname,
        objectname=body.objectname,
        op=body.op,
        amount=body.amount,
    )
    if not activity:
        raise HTTPException(
            404,
            f"Building '{body.buildingname}' or object '{body.objectname}' not found",
        )
    return {"status": "success", "message": "Activity recorded successfully",
            "activity": activity_to_dict(activity)}


@app.get("/api/buildingactivity")
def list_building_activities(session: Session = Depends(get_session)):
    return {"status": "success",
            "activities": [activity_to_dict(a) for a in BuildingActivity.get_all(session)]}


@app.get("/api/buildingactivity/{aid}")
def get_building_activity(aid: int, session: Session = Depends(get_session)):
    a = BuildingActivity.get(session, aid)
    if not a:
        raise HTTPException(404, "Activity not found")
    return {"status": "success", "activity": activity_to_dict(a)}


@app.delete("/api/buildingactivity/{aid}")
def delete_building_activity(aid: int, session: Session = Depends(get_session)):
    if not BuildingActivity.delete(session, aid):
        raise HTTPException(404, "Activity not found")
    return {"status": "success", "message": "Activity deleted successfully"}





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
            "level_cost": dict(row)}


@app.get("/api/buildinglevelcost")
def list_level_costs(session: Session = Depends(get_session)):
    return {"status": "success",
            "level_costs": [dict(c) for c in BuildingLevelCost.get_all(session)]}


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


#