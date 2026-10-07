

from fastapi import FastAPI , Request , Form , Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse , HTMLResponse
from sqlmodel import Session
import uuid , time
from datetime import datetime , timezone

from database.database import get_session , init , engine
from database.models import *
from database.models import User,Building,ArmyObject,Asset,CityOrCountry,UserInventory,UserLocation,BuildingActivity
from user import router
init()


app = FastAPI()
app.mount("/static" , StaticFiles(directory="static"),"static")
app.include_router(router=router)

tmp = Jinja2Templates("templates")




# ============================================================
# COOKIE HELPER
# ============================================================
def get_uid_from_cookie(request: Request):
    uid = request.cookies.get("uid")
    try:
        return int(uid) if uid else None
    except (TypeError, ValueError):
        return None


# ============================================================
# ROOT  →  templates/login.html
# ============================================================
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    uid = get_uid_from_cookie(request)
    if uid:
        with Session(engine) as session:
            user = session.get(User, uid)
            if user:
                if user.role == "admin":
                    return RedirectResponse("/admin", status_code=303)
                return RedirectResponse(f"/panel?user={user.id}", status_code=303)
    return tmp.TemplateResponse(
        request=request,
        name="login.html",
        context={"request": request, "error": request.query_params.get("error")},
    )


# ============================================================
# LOGIN  →  POST /api/auth/login
# ============================================================
@app.post("/api/auth/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    user = User.get_by_username_or_email(session, username.strip())
    if not user:
        return RedirectResponse("/?error=Invalid+credentials", status_code=303)

    # TODO: replace with bcrypt verification
    if user.password_hash != password:
        return RedirectResponse("/?error=Invalid+credentials", status_code=303)

    user.last_login = datetime.now(timezone.utc)
    session.add(user)
    session.commit()
    session.refresh(user)

    redirect_to = "/admin" if user.role == "admin" else f"/panel?user={user.id}"

    response = RedirectResponse(redirect_to, status_code=303)
    response.set_cookie(
        key="uid",
        value=str(user.id),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return response


# ============================================================
# LOGOUT
# ============================================================
@app.get("/api/auth/logout")
def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("uid")
    return response


# ============================================================
# USER PANEL  →  templates/up.html
# ============================================================
@app.get("/panel", response_class=HTMLResponse)
def user_panel(request: Request):
    uid = get_uid_from_cookie(request)
    if not uid:
        return RedirectResponse("/?error=Please+log+in", status_code=303)

    return tmp.TemplateResponse(
        request=request,
        name="up.html",
        context={"request": request, "user_id": uid},
    )


# ============================================================
# ADMIN PANEL  →  templates/adminpage.html
# ============================================================
@app.get("/admin", response_class=HTMLResponse)
def admin_panel(request: Request):
    uid = get_uid_from_cookie(request)
    if not uid:
        return RedirectResponse("/?error=Please+log+in", status_code=303)

    with Session(engine) as session:
        user = session.get(User, uid)
        if not user or user.role != "admin":
            return RedirectResponse("/401", status_code=303)

    return tmp.TemplateResponse(
        request=request,
        name="adminpage.html",
        context={"request": request, "user_id": uid},
    )


# ============================================================
# 401 PAGE  →  templates/401.html
# ============================================================
@app.get("/401", response_class=HTMLResponse)
def page_401(request: Request):
    return tmp.TemplateResponse("401.html", {"request": request}, status_code=401)


@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    if "text/html" in request.headers.get("accept", ""):
        return tmp.TemplateResponse("401.html", {"request": request}, status_code=401)
    return JSONResponse({"status": "error", "message": "Unauthorized"}, status_code=401)






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
    return {"status": "success", "level_cost": dict(c)}


@app.get("/api/buildinglevelcost/building/{bid}")
def list_building_level_costs(bid: int, session: Session = Depends(get_session)):
    rows = BuildingLevelCost.get_all_for_building(session, bid)
    return {"status": "success",
            "level_costs": [dict(c) for c in rows]}


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

# main.py — add at the bottom
from database.models import AttackRequest, UserInventory, ArmyObject, Asset
import random

def _attack_to_dict(a: AttackRequest, session: Session) -> dict:
    attacker = session.get(User, a.attacker_id)
    target   = session.get(User, a.target_id)
    return {
        "id": a.id,
        "attacker_id": a.attacker_id,
        "attacker_username": attacker.username if attacker else None,
        "target_id": a.target_id,
        "target_username": target.username if target else None,
        "role_message": a.role_message,
        "units": a.units(),
        "status": a.status,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@app.get("/api/admin/attacks")
def admin_list_attacks(session: Session = Depends(get_session)):
    rows = AttackRequest.get_all(session)
    return {"status": "success",
            "attacks": [_attack_to_dict(a, session) for a in rows]}


@app.get("/api/admin/attacks/pending")
def admin_list_pending_attacks(session: Session = Depends(get_session)):
    rows = AttackRequest.get_pending(session)
    return {"status": "success",
            "attacks": [_attack_to_dict(a, session) for a in rows]}


@app.post("/api/admin/attacks/{attack_id}/approve")
def admin_approve_attack(attack_id: int, session: Session = Depends(get_session)):
    a :AttackRequest= AttackRequest.get(session, attack_id)
    if not a:
        raise HTTPException(404, "Attack not found")
    if a.status != "pending":
        raise HTTPException(400, f"Attack already {a.status}")

    for ao in a.units():
        aoi = ArmyObject.get_by_name(session , ao["objectname"])
        stat = select(UserInventory).where(UserInventory.user_id == a.attacker_id).where(UserInventory.army_object_id == aoi.id)
        io :UserInventory= session.exec(stat).first()
        io.amount -= ao["amount"]
        session.add(io)
        session.commit()
        session.refresh(io)




    
   

    
    

    # 5) mark as approved
    a.status = "approved"
    session.add(a); session.commit(); session.refresh(a)

    return {
        "status": "success",
        "message": f"Attack aproved",
        "result": {
            "attack": _attack_to_dict(a, session),
        },
    }


@app.post("/api/admin/attacks/{attack_id}/reject")
def admin_reject_attack(attack_id: int, session: Session = Depends(get_session)):
    a = AttackRequest.get(session, attack_id)
    if not a:
        raise HTTPException(404, "Attack not found")
    if a.status != "pending":
        raise HTTPException(400, f"Attack already {a.status}")
    a.status = "rejected"
    session.add(a); session.commit(); session.refresh(a)
    return {"status": "success", "message": "Attack rejected"}



# ============================================================
# BACKGROUND LOOP — building activities
# ============================================================
import asyncio
import uvicorn
from sqlmodel import Session, select
from database.database import engine
from database.models import (
    UserBuilding, BuildingActivity, UserInventory,
)


def _process_one_tick():
    """One tick — runs in a worker thread (DB is sync)."""
    with Session(engine) as session:
        # every (user, building) pair where the user owns >=1 copy at level >=1
        rows = session.exec(
            select(UserBuilding)
            .where(UserBuilding.level >= 1)
            .where(UserBuilding.amount >= 1)
        ).all()

        for ub in rows:
            # all activities defined for this building
            acts = session.exec(
                select(BuildingActivity)
                .where(BuildingActivity.building_id == ub.building_id)
            ).all()
            if not acts:
                continue

            copies = ub.amount or 1
            inputs  = [(a.objectname, a.amount * copies) for a in acts if a.op == "user"]
            outputs = [(a.objectname, a.amount * copies) for a in acts if a.op == "produce"]
            if not outputs:
                continue

            # merge duplicate names (e.g. two rows for "stone")
            def _merge(items):
                d = {}
                for n, a in items:
                    d[n] = d.get(n, 0) + a
                return d

            need = _merge(inputs)
            give = _merge(outputs)

            # 1) does the user have everything?
            has_all = True
            for name, amt in need.items():
                if amt <= 0:
                    continue
                if UserInventory.get_amount(session, ub.user_id, name) < amt:
                    has_all = False
                    break

            # 2) if not enough → skip this user, do nothing
            if not has_all:
                continue

            # 3) consume inputs
            for name, amt in need.items():
                if amt > 0:
                    UserInventory.add_amount(session, ub.user_id, name, -amt)

            # 4) add outputs
            for name, amt in give.items():
                if amt > 0:
                    UserInventory.add_amount(session, ub.user_id, name, +amt)

            print(f"[tick] user={ub.user_id} building={ub.building_id} "
                  f"consumed={need} produced={give}")


async def wloop():
    print("[loop] started")
    eventt =7*24*60*60
    while True:
        try:
            await asyncio.to_thread(_process_one_tick)
        except Exception as e:
            print(f"[loop] error: {e!r}")
        await asyncio.sleep(eventt)   # seconds between ticks


@app.on_event("startup")
async def _start_loop():
    asyncio.create_task(wloop())


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    
