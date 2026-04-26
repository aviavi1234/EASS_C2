from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from sqlmodel import Session, select

from backend.database import db
from backend.models import PointOfInterest, PointOfInterestCreate, PointOfInterestUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.create_db_and_tables()
    yield


app = FastAPI(title="Command & Control API", lifespan=lifespan)


@app.post("/pois/", response_model=PointOfInterest, status_code=201)
def create_poi(
    poi: PointOfInterestCreate, session: Session = Depends(db.get_session)
):
    db_poi = PointOfInterest.model_validate(poi)
    session.add(db_poi)
    session.commit()
    session.refresh(db_poi)
    return db_poi


@app.get("/pois/", response_model=List[PointOfInterest])
def read_pois(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(db.get_session),
):
    pois = session.exec(select(PointOfInterest).offset(skip).limit(limit)).all()
    return pois


@app.get("/pois/{poi_id}", response_model=PointOfInterest)
def read_poi(poi_id: int, session: Session = Depends(db.get_session)):
    poi = session.get(PointOfInterest, poi_id)
    if not poi:
        raise HTTPException(status_code=404, detail="Point of Interest not found")
    return poi


@app.patch("/pois/{poi_id}", response_model=PointOfInterest)
def update_poi(
    poi_id: int,
    poi_update: PointOfInterestUpdate,
    session: Session = Depends(db.get_session),
):
    db_poi = session.get(PointOfInterest, poi_id)
    if not db_poi:
        raise HTTPException(status_code=404, detail="Point of Interest not found")

    update_data = poi_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_poi, key, value)

    db_poi.updated_at = datetime.now(timezone.utc)

    session.add(db_poi)
    session.commit()
    session.refresh(db_poi)
    return db_poi


@app.delete("/pois/{poi_id}", status_code=204)
def delete_poi(poi_id: int, session: Session = Depends(db.get_session)):
    poi = session.get(PointOfInterest, poi_id)
    if not poi:
        raise HTTPException(status_code=404, detail="Point of Interest not found")
    session.delete(poi)
    session.commit()
    return {"ok": True}
