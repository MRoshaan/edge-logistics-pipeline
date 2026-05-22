use("logistics");

db.drivers.createIndex({ location: "2dsphere" });
db.drivers.createIndex({ status: 1, updatedAt: -1 });
db.drivers.createIndex({ driverId: 1 }, { unique: true });
