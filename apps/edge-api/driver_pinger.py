import asyncio

from simulator.driver_pinger import ping_loop, shutdown


if __name__ == "__main__":
    try:
        asyncio.run(ping_loop())
    finally:
        asyncio.run(shutdown())
