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

# enum systemstate {
#     kIdel = 0,
#     kJoined,
#     kSending,
#     kWaitSend,
#     kEnd,
# };
system_fsm = 0 # idle
loraWanSendNUM = -1
loraWanSendCNT = -1

# use join or not
useJoin = True

wait_cnt = 0


async def setup(uartCfg):
    global system_fsm
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
    recvStr = await waitRevice()
    print(recvStr)

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
    recvStr = await waitRevice()
    print(recvStr)

    # 869.525 - SF9BW125 (RX2)              | 869525000
    LoRaWAN.set_rx_window("869525000")
    recvStr = await waitRevice()
    print(recvStr)
    
    if useJoin:    
        LoRaWAN.start_join()
    else:
        LoRaWAN.flush()
        print("Try to continue without join")
        LoRaWAN.write_cmd(f"AT+CDEVADDR={pr.devAddr}\r\n")
        recvStr = await waitRevice()
        print(recvStr)
        LoRaWAN.write_cmd(f"AT+CNWKSKEY={pr.nwkSkey}\r\n")
        recvStr = await waitRevice()
        print(recvStr)
        LoRaWAN.write_cmd(f"AT+CAPPSKEY={pr.appSkey}\r\n")
        recvStr = await waitRevice()
        print(recvStr)
        await asyncio.sleep(1)
        system_fsm = 2 # start into send


async def waitRevice():
    recvStr = ""
    loops = 10
    while (len(recvStr) == 0) or (recvStr.find("\n") == -1):
        #recvStr = LoRaWAN.read_string_until('\n')
        recvStr += LoRaWAN.wait_msg()
        loops -= 1
        if loops == 0:
            break 
    print(recvStr)
    return recvStr

async def loop():
    global system_fsm, loraWanSendCNT, loraWanSendNUM
    global wait_cnt
    print("Starting loop in state: " + str(system_fsm))
    recvStr = await waitRevice()
    # recvStr = LoRaWAN.wait_msg(2000)
    if recvStr.find("+CJOIN:") != -1:
        if recvStr.find("OK") != -1:
            print("LoraWan JOIN")
            system_fsm = 1  # joined
        else:
            print("LoraWan JOIN FAIL")
            system_fsm = 0  #  idle 
            
    elif recvStr.find("OK+RECV") != -1:
        if system_fsm == 1: # joined
            system_fsm = 2  # sending
        elif system_fsm == 3:   # wait send
            #system_fsm = 2  # sending
            print("RX in State 3, CNT: " + str(loraWanSendCNT))

    # note SEND and SENT !!!
    # OK+SEND:TX_LEN, send success,TX_LEN:1Byte,represent the length of data sent.
    # OK-SENT:TX_CNT, send success,TX_CNT:1Byte,represent the times of data sent
    elif recvStr.find("OK+SEND") != -1:
        sendnum = recvStr.split("OK+SEND:")[1]
        print(" [ INFO ] SEND NUM " + sendnum)
        loraWanSendNUM = int(sendnum)

    elif recvStr.find("OK+SENT") != -1:
        sendcnt = recvStr.split("OK+SENT:")[1]
        print(" [ INFO ] SEND CNT " + sendcnt)
        loraWanSendCNT = int(sendcnt)
        if system_fsm == 2: # sending
            system_fsm = 3
            wait_cnt = 0
            print("LoraWan Wait Send")

    if system_fsm == 2: # sending
        print("LoraWan Sending")
        LoRaWAN.write_cmd("AT+DTRX=1,15,7,4c4f5645204d35\r\n")
        system_fsm = 3
        wait_cnt = 0
        print("LoraWan Wait Send")

    if system_fsm == 3: # wait send
        wait_cnt += 1
        if wait_cnt % 100:
            print("... " + str(wait_cnt))
        if wait_cnt >= 10: #0 * 1 * 60:
            wait_cnt = 0
            system_fsm = 2
           
        
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
