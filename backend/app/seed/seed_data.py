"""Seed script to populate SQLite database with realistic initial data."""

import logging
import random

from sqlalchemy.orm import Session

from backend.app.auth.security import hash_password
from backend.app.config import get_settings
from backend.app.db import Base, SessionLocal, engine
from backend.app.models.schema import (
    Alert,
    District,
    Facility,
    GridPoint,
    HelpRequest,
    RiskScore,
    User,
    Volunteer,
    WeatherSnapshot,
    utcnow_str,
)

logger = logging.getLogger(__name__)

DISTRICTS_DATA = [
    # Assam
    {"name": "Morigaon", "state": "Assam", "lat": 26.25, "lon": 92.34, "dlat": 0.3, "dlon": 0.3},
    {"name": "Dhubri", "state": "Assam", "lat": 26.02, "lon": 89.98, "dlat": 0.3, "dlon": 0.3},
    {"name": "Barpeta", "state": "Assam", "lat": 26.32, "lon": 91.01, "dlat": 0.3, "dlon": 0.3},
    {"name": "Lakhimpur", "state": "Assam", "lat": 27.24, "lon": 94.10, "dlat": 0.3, "dlon": 0.3},
    {"name": "Goalpara", "state": "Assam", "lat": 26.17, "lon": 90.62, "dlat": 0.3, "dlon": 0.3},
    # Bihar
    {"name": "Darbhanga", "state": "Bihar", "lat": 26.15, "lon": 85.90, "dlat": 0.25, "dlon": 0.25},
    {
        "name": "Muzaffarpur",
        "state": "Bihar",
        "lat": 26.12,
        "lon": 85.36,
        "dlat": 0.25,
        "dlon": 0.25,
    },
    {"name": "Sitamarhi", "state": "Bihar", "lat": 26.59, "lon": 85.48, "dlat": 0.25, "dlon": 0.25},
    {"name": "Patna", "state": "Bihar", "lat": 25.5941, "lon": 85.1376, "dlat": 0.25, "dlon": 0.25},
    # Kerala
    {"name": "Alappuzha", "state": "Kerala", "lat": 9.49, "lon": 76.33, "dlat": 0.2, "dlon": 0.2},
    {"name": "Ernakulam", "state": "Kerala", "lat": 9.98, "lon": 76.28, "dlat": 0.2, "dlon": 0.2},
]

VOLUNTEER_NAMES = [
    "Arjun Singh",
    "Meena Devi",
    "Raju Sharma",
    "Sunita Kumari",
    "Vikram Rao",
    "Priya Nair",
    "Ajay Verma",
    "Kavitha Menon",
    "Ramesh Patel",
    "Anita Das",
    "Suresh Babu",
    "Lakshmi Iyer",
    "Mohan Lal",
    "Geeta Rani",
    "Sanjay Gupta",
    "Usha Pillai",
    "Deepak Kumar",
    "Asha Devi",
    "Rajesh Tiwari",
    "Nandini Roy",
]

SKILLS_POOL = [
    "rescue,first-aid",
    "first-aid,logistics",
    "rescue,boat",
    "logistics,communication",
    "medical,first-aid",
    "cooking,shelter",
]


def seed_database():
    """Create all tables and insert seed data if empty."""
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    settings = get_settings()

    try:
        # 1. Seed Users
        if db.query(User).count() == 0:
            coordinator = User(
                username=settings.COORDINATOR_EMAIL,
                role="coordinator",
                password_hash=hash_password(settings.COORDINATOR_PASSWORD),
                created_at=utcnow_str(),
            )
            volunteer_user = User(
                username=settings.VOLUNTEER_EMAIL,
                role="volunteer",
                password_hash=hash_password(settings.VOLUNTEER_PASSWORD),
                created_at=utcnow_str(),
            )
            db.add_all([coordinator, volunteer_user])
            db.commit()
            print("✓ Seeded coordinator and volunteer users.")

        # 2. Seed Districts & Grid Points
        if db.query(District).count() == 0:
            random.seed(42)
            districts_to_add = []
            for d in DISTRICTS_DATA:
                dist = District(
                    name=d["name"],
                    state=d["state"],
                    centroid_lat=d["lat"],
                    centroid_lon=d["lon"],
                    bbox_min_lat=d["lat"] - d["dlat"],
                    bbox_max_lat=d["lat"] + d["dlat"],
                    bbox_min_lon=d["lon"] - d["dlon"],
                    bbox_max_lon=d["lon"] + d["dlon"],
                )
                districts_to_add.append(dist)
            db.add_all(districts_to_add)
            db.commit()
            print(f"✓ Seeded {len(districts_to_add)} districts.")

            # Create 9 grid points per district (3x3 grid)
            all_districts = db.query(District).all()
            for dist in all_districts:
                for dy in [-0.08, 0.0, 0.08]:
                    for dx in [-0.08, 0.0, 0.08]:
                        gp = GridPoint(
                            district_id=dist.id,
                            lat=dist.centroid_lat + dy,
                            lon=dist.centroid_lon + dx,
                            elevation_m=round(random.uniform(15.0, 65.0), 1),
                        )
                        db.add(gp)
                        db.flush()

                        # Weather snapshot
                        precip_48h = round(random.uniform(5.0, 140.0), 1)
                        ws = WeatherSnapshot(
                            grid_point_id=gp.id,
                            fetched_at=utcnow_str(),
                            valid_from=utcnow_str(),
                            valid_to=utcnow_str(),
                            precip_1h_mm=round(precip_48h / 48, 2),
                            precip_24h_mm=round(precip_48h * 0.55, 1),
                            precip_48h_mm=precip_48h,
                            river_discharge_m3s=round(random.uniform(20.0, 450.0), 1),
                            wind_speed_kmh=round(random.uniform(10.0, 35.0), 1),
                        )
                        db.add(ws)

                # District risk score
                level = random.choice(["low", "medium", "high", "severe"])
                raw_score = {"low": 0.22, "medium": 0.48, "high": 0.72, "severe": 0.88}[level]
                rs = RiskScore(
                    district_id=dist.id,
                    level=level,
                    explanation=f"Forecast shows precipitation impact with river discharge variation in {dist.name}.",
                    score_raw=raw_score,
                    computed_at=utcnow_str(),
                )
                db.add(rs)

                # Facilities per district
                facilities = [
                    Facility(
                        district_id=dist.id,
                        name=f"{dist.name} District Civil Hospital",
                        type="hospital",
                        lat=dist.centroid_lat + 0.012,
                        lon=dist.centroid_lon - 0.015,
                        capacity=150,
                        capacity_used=random.randint(40, 110),
                        source="seed",
                    ),
                    Facility(
                        district_id=dist.id,
                        name=f"{dist.name} Community Relief Shelter",
                        type="shelter",
                        lat=dist.centroid_lat - 0.018,
                        lon=dist.centroid_lon + 0.014,
                        capacity=300,
                        capacity_used=random.randint(50, 180),
                        source="seed",
                    ),
                    Facility(
                        district_id=dist.id,
                        name=f"{dist.name} Red Cross Medical Post",
                        type="clinic",
                        lat=dist.centroid_lat + 0.025,
                        lon=dist.centroid_lon + 0.022,
                        capacity=40,
                        capacity_used=15,
                        source="seed",
                    ),
                ]
                db.add_all(facilities)

            db.commit()
            print("✓ Seeded grid points, weather snapshots, risk scores, and facilities.")

        # 3. Seed Volunteers
        if db.query(Volunteer).count() == 0:
            all_districts = db.query(District).all()
            vols = []
            for i, name in enumerate(VOLUNTEER_NAMES):
                dist = all_districts[i % len(all_districts)]
                vols.append(
                    Volunteer(
                        district_id=dist.id,
                        name=name,
                        skills=random.choice(SKILLS_POOL),
                        capacity=random.randint(1, 4),
                        lat=dist.centroid_lat + random.uniform(-0.04, 0.04),
                        lon=dist.centroid_lon + random.uniform(-0.04, 0.04),
                        available=1,
                        created_at=utcnow_str(),
                    )
                )
            db.add_all(vols)
            db.commit()
            print(f"✓ Seeded {len(vols)} synthetic volunteers.")

        # 4. Seed Initial Help Requests
        if db.query(HelpRequest).count() == 0:
            sample_requests = [
                {
                    "text": "Water level entered our ground floor, 5 people trapped on terrace including elderly grandmother.",
                    "lang": "en",
                    "urgency": 5,
                    "need": "rescue",
                    "people": 5,
                    "vulnerable": '["elderly"]',
                    "sum_en": "5 people trapped on terrace with elderly person, water entering ground floor.",
                    "sum_hi": "छत पर 5 लोग फंसे हैं, बुजुर्ग महिला साथ हैं, पानी घर में घुस गया है।",
                },
                {
                    "text": "हम 4 लोग हैं, खाना और पीने का पानी खत्म हो गया है 2 दिन से।",
                    "lang": "hi",
                    "urgency": 4,
                    "need": "food",
                    "people": 4,
                    "vulnerable": '["children"]',
                    "sum_en": "4 people without food and clean drinking water for 2 days.",
                    "sum_hi": "4 लोगों को 2 दिन से भोजन और शुद्ध पेयजल की तत्काल आवश्यकता है।",
                },
                {
                    "text": "Bhaiya paani bohot tez aa raha hai, road block hai hospital pahunchna hai delivery case hai.",
                    "lang": "hinglish",
                    "urgency": 5,
                    "need": "medical",
                    "people": 2,
                    "vulnerable": '["pregnant"]',
                    "sum_en": "Emergency delivery case requiring hospital transport; road is blocked by floodwaters.",
                    "sum_hi": "गर्भवती महिला को अस्पताल पहुंचाने हेतु तत्काल सहायता की आवश्यकता, मार्ग जलमग्न।",
                },
            ]

            dist = (
                db.query(District).filter(District.name == "Patna").first()
                or db.query(District).first()
            )
            for req in sample_requests:
                hr = HelpRequest(
                    district_id=dist.id if dist else None,
                    raw_text=req["text"],
                    language=req["lang"],
                    location_raw=f"{dist.name if dist else 'City'} Center",
                    lat=(dist.centroid_lat + random.uniform(-0.02, 0.02)) if dist else 25.594,
                    lon=(dist.centroid_lon + random.uniform(-0.02, 0.02)) if dist else 85.137,
                    urgency=req["urgency"],
                    need=req["need"],
                    people_count=req["people"],
                    vulnerable_groups=req["vulnerable"],
                    summary_en=req["sum_en"],
                    summary_hi=req["sum_hi"],
                    triage_method="llm",
                    status="new",
                    created_at=utcnow_str(),
                    updated_at=utcnow_str(),
                )
                db.add(hr)
            db.commit()
            print("✓ Seeded realistic initial help requests.")

        # 5. Seed Official Alerts
        if db.query(Alert).count() == 0:
            dist = (
                db.query(District).filter(District.name == "Patna").first()
                or db.query(District).first()
            )
            sample_alert = Alert(
                district_id=dist.id if dist else None,
                level="severe",
                message_hi="गंडक और गंगा नदी के जलस्तर में अप्रत्याशित वृद्धि। निचले इलाकों के निवासी तुरंत सुरक्षित स्थानों पर जाएं।",
                message_en="Significant rise in Ganga and Gandak river discharge. Residents in low-lying zones must evacuate immediately to designated relief shelters.",
                channel="all",
                sent_at=utcnow_str(),
                source="SACHET",
                identifier="SACHET-ALERT-2026-FLOOD-001",
            )
            db.add(sample_alert)
            db.commit()
            print("✓ Seeded official SACHET alert fixture.")

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
