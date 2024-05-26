import asyncio
import machine
from M5_LoraWan import M5_LoRaWAN

import json
import os
import sys

_CONF_FILE = "config.json"

# import euis and key 
import private as pr 
# euis same order as in element platform

LoRaWAN = M5_LoRaWAN()

response = ""

system_fsm = 0
loraWanSendNUM = -1
loraWanSendCNT = -1


async def setup(uartCfg):
    uart = machine.UART(2, tx=uartCfg[0], rx=uartCfg[1], baudrate=115200, bits=8, parity=None, stop=1, timeout=1000)
    LoRaWAN.init(uart)
    await asyncio.sleep(0.1)

    print("Module Connect.....")
    while not LoRaWAN.check_device_connect():
        pass
    LoRaWAN.write_cmd("AT\r\n")
    await asyncio.sleep(0.1)
    LoRaWAN.flush()

    # Disable Log Information
    LoRaWAN.write_cmd("AT+ILOGLVL=0\r\n")
    # Enable  Log Information
    LoRaWAN.write_cmd("AT+CSAVE\r\n")
    LoRaWAN.write_cmd("AT+IREBOOT=0\r\n")
    print("LoraWan Rebooting")
    await asyncio.sleep(1)

    print("LoraWan config")
    # Set Join Mode OTAA.
    
    
    LoRaWAN.config_otta(pr.devEui, # Device EUI
                       pr.appEui,  # APP EUI
                       pr.appKey,  # APP KEY
                       "2"  # Upload Download Mode
    )
    response = LoRaWAN.wait_msg(1000)
    print(response)
    # Set ClassC mode
    # LoRaWAN.set_class("2")
    LoRaWAN.set_class("0")
    LoRaWAN.write_cmd("AT+CWORKMODE=2\r\n")

    # LoRaWAN868
    # TX Freq
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
    LoRaWAN.start_join()

async def waitRevice():
    recvStr = ""
    while (len(recvStr) == 0) or (recvStr.find("\n") == -1):
        #recvStr = LoRaWAN.read_string_until('\n')
        recvStr += LoRaWAN.wait_msg() 
    print(recvStr)
    return recvStr

async def loop():
    global system_fsm, loraWanSendCNT, loraWanSendNUM
    recvStr = await waitRevice()
    # recvStr = LoRaWAN.wait_msg(2000)
    if recvStr.find("+CJOIN:") != -1:
        if recvStr.find("OK") != -1:
            print("LoraWan JOIN")
            system_fsm = 1
        else:
            print("LoraWan JOIN FAIL")
            system_fsm = 0
    elif recvStr.find("OK+RECV") != -1:
        if system_fsm == 1:
            system_fsm = 2
        elif system_fsm == 3:
            system_fsm = 2
            strbuff = ""
            if loraWanSendCNT < 5 and loraWanSendNUM == 8:
                strbuff = "TSET OK CNT: " + str(loraWanSendCNT)
                print(strbuff)
            else:
                strbuff = "FAILD NUM:" + str(loraWanSendNUM) + " CNT:" + str(loraWanSendCNT)
                print(strbuff)
    elif recvStr.find("OK+SEND") != -1:
        sendnum = recvStr[8:]
        print(" [ INFO ] SEND NUM " + sendnum)
        loraWanSendNUM = int(sendnum)
    elif recvStr.find("OK+SENT") != -1:
        sendcnt = recvStr[8:]
        print(" [ INFO ] SEND CNT " + sendcnt)
        loraWanSendCNT = int(sendcnt)

    if system_fsm == 2:
        print("LoraWan Sending")
        LoRaWAN.write_cmd("AT+DTRX=1,8,8,4c4f5645204d35\r\n")
        system_fsm = 3
    await asyncio.sleep(0.01)

async def main():
    try:
        with open(_CONF_FILE) as f:
            cfdata = json.load(f)
        print(cfdata)
        uartCfg = cfdata["io"]["grove"]
        #print("uartCfg:",uartCfg)
    except:
        print("Config problem")
        sys.exit()
    await setup(uartCfg)
    while True:
        await loop()

asyncio.run(main())
