import asyncio
import machine
import json

from M5_LoraWan import M5_LoRaWAN

_CONF_FILE = "config.json"

# import euis and key 
import private as pr 
# euis same order as in element platform

try:
    with open(_CONF_FILE) as f:
        cfdata = json.load(f)
    #print(cfdata)
    uartCfg = cfdata["io"]["grove"]
    tx = uartCfg[1]
    rx = uartCfg[0]
    #print("uartCfg:",uartCfg)
except:
    type = "atom-lite"  # or "atom-s3"
    if type == "atom-lite":
        #atom lite:
        tx=26
        rx=32
    elif type == "atom-s3":
        # atom s3
        tx=2
        rx=1


LoRaWAN = M5_LoRaWAN()
response = ""

async def setup():
    uart = machine.UART(2, tx=tx, rx=rx, baudrate=115200, bits=8, parity=None, stop=1, timeout=1000)
    LoRaWAN.init(uart)
    print("Module Connect.....")
    while not LoRaWAN.check_device_connect():
        await asyncio.sleep(0)
    print("Module Connected")
    LoRaWAN.write_cmd("AT+CRESTORE\r\n")
    # Disable Log Information
    LoRaWAN.write_cmd("AT+ILOGLVL=0\r\n")
    # Enable  Log Information
    # LoRaWAN.write_cmd("AT+ILOGLVL=5\r\n")
    LoRaWAN.write_cmd("AT+CSAVE\r\n")
    LoRaWAN.write_cmd("AT+IREBOOT=0\r\n")
    await asyncio.sleep(1)
    while not LoRaWAN.check_device_connect():
        await asyncio.sleep(0)
    print("Module Config...")

    LoRaWAN.config_otta(pr.devEui, # Device EUI
                       pr.appEui,  # APP EUI
                       pr.appKey,  # APP KEY
                       "2"  # Upload Download Mode
    )
    response = LoRaWAN.wait_msg(1000)
    print(response)

    # Set Class Mode A
    LoRaWAN.set_class("0")

    LoRaWAN.write_cmd("AT+CWORKMODE=2\r\n")

    # LoRaWAN868 TX Freq
    # 868.1 - SF7BW125 to SF12BW125
    # 868.3 - SF7BW125 to SF12BW125 and SF7BW250
    # 868.5 - SF7BW125 to SF12BW125
    # 867.1 - SF7BW125 to SF12BW125
    # 867.3 - SF7BW125 to SF12BW125
    # 867.5 - SF7BW125 to SF12BW125
    # 867.7 - SF7BW125 to SF12BW125
    # 867.9 - SF7BW125 to SF12BW125
    # 868.8 - FSK
    LoRaWAN.set_freq_mask("0001")
    # 869.525 - SF9BW125 (RX2)              | 869525000
    LoRaWAN.set_rx_window("869525000")

    await asyncio.sleep(0.1)
    response = LoRaWAN.wait_msg(1000)
    print(response)
    LoRaWAN.start_join()
    print("Start Join.....")
    while not LoRaWAN.check_join_status():
        await asyncio.sleep(0.1)
    print("Join success.....")

async def loop():
    # send data
    print("Sending Data: ")
    LoRaWAN.send_msg(1, 15, "4d35535441434b")
    # receive data
    response = LoRaWAN.receive_msg()
    if response != "":
        print("Received: ")
        print(response)
    #await asyncio.sleep(20*60)
    await asyncio.sleep(1*60)

async def main():
    await setup()
    while True:
        await loop()

asyncio.run(main())

