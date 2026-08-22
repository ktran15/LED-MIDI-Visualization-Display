import asyncio
from bleak import BleakScanner

async def findPiano():
    devices = await BleakScanner.discover(return_adv=True)
    for address, (device, adv_data) in devices.items():
        print(f"Name: {adv_data.local_name}, RSSI: {adv_data.rssi}, UUID: {adv_data.service_uuids}")

asyncio.run(findPiano())