import asyncio
import random
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

from app.settings import get_settings


async def seed_drivers() -> None:
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_database_name]
    drivers = db["drivers"]

    await client.admin.command("ping")
    await drivers.create_index([("location", "2dsphere")])

    base_lon = 67.0011
    base_lat = 24.8607

    first_names = [
        "Ali", "Usman", "Fatima", "Ayesha", "Hamza", "Zain", "Hina", "Bilal", "Sana", "Ahmed",
        "Mariam", "Talha", "Ibrahim", "Saad", "Noor", "Kiran", "Arham", "Dua", "Adeel", "Sarah",
    ]
    last_names = [
        "Khan", "Tariq", "Ali", "Raza", "Hassan", "Qureshi", "Malik", "Farooq", "Aziz", "Nawaz",
    ]
    vehicle_types = ["Car", "Bike"]

    docs = []
    for idx in range(1, 16):
        lon = base_lon + random.uniform(-0.08, 0.08)
        lat = base_lat + random.uniform(-0.06, 0.06)
        driver_name = f"{random.choice(first_names)} {random.choice(last_names)}"
        plate_number = f"KHI-{random.randint(1000, 9999)}"
        vehicle_type = random.choice(vehicle_types)
        docs.append(
            {
                "driverId": f"KHI-{idx:04d}",
                "driverName": driver_name,
                "plateNumber": plate_number,
                "vehicleType": vehicle_type,
                "status": "online",
                "location": {
                    "type": "Point",
                    "coordinates": [round(lon, 6), round(lat, 6)],
                },
                "heading": round(random.uniform(0, 359), 2),
                "speedKph": round(random.uniform(20, 55), 2),
                "updatedAt": datetime.now(timezone.utc),
            }
        )

    await drivers.delete_many({"driverId": {"$regex": r"^KHI-\d{4}$"}})
    result = await drivers.insert_many(docs)
    print(f"Inserted {len(result.inserted_ids)} Karachi drivers.")

    client.close()


if __name__ == "__main__":
    asyncio.run(seed_drivers())
