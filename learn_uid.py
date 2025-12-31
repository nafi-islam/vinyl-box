import time
import board, busio
from adafruit_pn532.i2c import PN532_I2C

i2c = busio.I2C(board.SCL, board.SDA)
pn532 = PN532_I2C(i2c, debug=False)
pn532.SAM_configuration()

print("Tap an NFC tag")
seen = set()

while True:
    uid = pn532.read_passive_target(timeout=0.2)
    if uid:
        uid_hex = "".join(f"{b:02X}" for b in uid)
        if uid_hex not in seen:
            print("UID:", uid_hex)
            seen.add(uid_hex)
        time.sleep(0.3)
