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

async def setup(restore = False):
    uart = machine.UART(2, tx=tx, rx=rx, baudrate=115200, bits=8, parity=None, stop=1, timeout=1000)
    LoRaWAN.init(uart)

    print("Module power .....")
    LoRaWAN.write_cmd("AT+CLPM=0\r\n")
    #LoRaWAN.write_cmd("\x00\x00\x00\x00\x00\x00\r\n")
    await asyncio.sleep(0.1)
    response = LoRaWAN.wait_msg(1000)
    print("Response:", response)

    print("Module Connect.....")
    while not LoRaWAN.check_device_connect():
        await asyncio.sleep(0)
    print("Module Connected")

    if not restore:
        return

    print("Restore Module...")
    LoRaWAN.write_cmd("AT+CRESTORE\r\n")
    await asyncio.sleep(1)
    while not LoRaWAN.check_device_connect():
        await asyncio.sleep(0)
    print("Module Restored")
        
    # Disable Log Information
    LoRaWAN.write_cmd("AT+ILOGLVL=0\r\n")
    LoRaWAN.write_cmd("AT+CSAVE\r\n")
    LoRaWAN.write_cmd("AT+IREBOOT=0\r\n")
    await asyncio.sleep(1)
    while not LoRaWAN.check_device_connect():
        await asyncio.sleep(0)
    print("Module Config...")

    # Configure for ABP, with eui
    LoRaWAN.config_abp(pr.devEui_abp,
                       pr.devAddr_abp,
                       pr.nwsKey_abp,
                       pr.appsKey_abp,
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
    print("Module up .....")

async def loop():
    # send data
    print("Sending Data: ")
    LoRaWAN.send_msg(1, 15, "4d35535441434b")
    # receive data
    response = LoRaWAN.receive_msg()
    if response != "":
        print("Received: ")
        print(response)
    # save mac params
    LoRaWAN.write_cmd("AT+CSAVE\r\n")        
    await asyncio.sleep(0.1)
    response = LoRaWAN.wait_msg(1000)
    # enter sleep mode
    print("Entering Sleep Mode...")
    LoRaWAN.write_cmd("AT+CLPM=1\r\n")
    await asyncio.sleep(0.1)
    response = LoRaWAN.wait_msg(1000)

    return

    await asyncio.sleep(20*60)
    #await asyncio.sleep(1*60)
    # restore from sleep
    print("Restoring from Sleep Mode...")
    #LoRaWAN.write_cmd("\x00\x00")
    LoRaWAN.write_cmd("AT+CLPM=0\r\n")
    #LoRaWAN.write_cmd("\x00\x00\x00\x00\x00\x00\r\n")
    await asyncio.sleep(0.1)
    response = LoRaWAN.wait_msg(1000)
    print("Response:", response)
    
async def main():
    if machine.reset_cause() == machine.DEEPSLEEP_RESET:
        print("Woke from deep sleep")
        await setup()
    else:
        print("Fresh boot or other reset")
        await setup(True)
    while True:
        await loop()
        ds = 10 * 60 * 1000  # 20 seconds
        machine.deepsleep(ds)
        
asyncio.run(main())

# element backend receives a:
# a = "34643335353335343431343334620000000000000000000000000000"
# device sends b:
# b = "4d35535441434b"
# decode at backend:
# bytes.fromhex(a)[:14] == b.encode()
# True
