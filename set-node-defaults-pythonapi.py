from asyncio import sleep
from copy import deepcopy
from enum import Enum
import os
import subprocess
import sys
import time
from types import SimpleNamespace
import meshtastic
import meshtastic.ble_interface
import meshtastic.serial_interface
import meshtastic.tcp_interface


class LALO_ENUM(Enum):
    COM = 1
    IP = 2
    BLE = 3
    MOBILE = 4
    STATIONARY = 5

##################################################################################
# # example use from CLI, params are optional
# python set-my-defaults-pythonapi -tgt=COM4 -ln=JB_MOB_4 -sn=JBM4
# python set-my-defaults-pythonapi -tgt=ip:192.168.1.171 -ln=JB_MOB_Tak4 -sn=JBM4
# if no params defaults form below are used
##################################################################################
# targetName = "COM3"  # options: COM1 | COM2 | COM3 ... etc
# targetName = "IP:192.168.1.172" # options: IP:xxx.xxx.xxx.xxx
# targetName = "BLE:JBR2_54f4"  # options: BLE:nodename
# targetName = "BLE:Meshtastic_54f4"  # options: BLE:nodename or MAC


targetName = "COM4"  # options: COM1 | COM2 | COM3 ... etc or IP:192.168.1.171
# targetName = "IP:192.168.1.174" # options: IP:xxx.xxx.xxx.xxx
# targetName = "BLE:JBM4_7e68"  # options: BLE:nodename or MAC

customSettings = SimpleNamespace(
    longName="JB_MOB_TAK4@2.5.7",
    shortName="JBM4",
    # options: ENABLED | DISABLED | NOT_PRESENT
    gpsMode=meshtastic.config_pb2.Config.PositionConfig.GpsMode.ENABLED,
    # longName="JB_RZE_TAK2@2.5.7",
    # shortName="JBR2",
    # gpsMode=LALO_ENUM.STATIONARY.name,
    # gpsMode=meshtastic.config_pb2.Config.PositionConfig.GpsMode.DISABLED,
    # !!!SENSITIVE_DATA!!! # it this link is embedded lora settings which are overrided below
    channelUrl=r'https://meshtastic.org/e/#-',
    bluetoothPIN=111999,  # !!!SENSITIVE_DATA!!! # max 6 digits
    # options: ['CLIENT', 'CLIENT_MUTE', 'ROUTER', 'ROUTER_CLIENT', 'REPEATER', 'TRACKER', 'SENSOR', 'TAK', 'CLIENT_HIDDEN', 'LOST_AND_FOUND', 'TAK_TRACKER']
    nodeRole=meshtastic.config_pb2.Config.DeviceConfig.Role.TAK,
    fixedLatitude=55.060981,
    fixedLongitude=23.982287,
    fixedAltitude=170,  # integers only
)

wifiNetworkParams = SimpleNamespace(
    enabled=False,
    dns=16885952,  # "192.168.1.1"
    gateway=16885952,  # "192.168.1.1"
    # you can get this from online calculators but enter like 172.1.168.192
    ip=2885789888,  # "192.168.1.172"
    # ip=2919344320,  # "192.168.1.174"
    subnet=16777215,  # "255.255.255.0"
    wifi_ssid="",  # !!!SENSITIVE_DATA!!!
    wifi_psk="",  # !!!SENSITIVE_DATA!!!
)


#####################################
########### BEGIN SCRIPT DATA ############


OKlbl = f"\033[30m\033[42mOK:\033[0m "
SUCCESSlbl = f"\033[30m\033[42mSUCCESS:\033[0m "
INFOlbl = f"\033[30m\033[44mINFO:\033[0m "
ERRORlbl = f"\033[30m\033[41mERROR:\033[0m "


def ExtractParams(argv):
    if len(argv) > 1:
        argv = argv[1:]

        tgt = list(filter(lambda s: s.startswith('-tgt='), argv))
        tgt = tgt[0].split('=')[1] if len(tgt) > 0 else targetName

        ln = list(filter(lambda s: s.startswith('-ln='), argv))
        customSettings.longName = ln[0].split('=')[1] if len(
            ln) > 0 else customSettings.longName

        sn = list(filter(lambda s: s.startswith('-sn='), argv))
        customSettings.shortName = sn[0].split('=')[1][:4] if len(
            sn) > 0 else customSettings.shortName


def ConnectToNode(targetName):
    try:
        print(f"{INFOlbl}lookin for interface at: {targetName}")
        if targetName.startswith(LALO_ENUM.COM.name):
            interface = meshtastic.serial_interface.SerialInterface(
                devPath=targetName)
        elif targetName.startswith(LALO_ENUM.IP.name):
            ip = targetName.split(':')[1]
            interface = meshtastic.tcp_interface.TCPInterface(hostname=ip)
        elif targetName.startswith(LALO_ENUM.BLE.name):
            name = targetName.split(':')[1]
            interface = meshtastic.ble_interface.BLEInterface(address=name)
        else:
            raise
        print(f"{OKlbl}interface found at: {targetName}")
        return interface
    except:
        print(f"{ERRORlbl} interface not found, exiting")
        exit(1)


#####################################
########### SCRIPT START ############
vno = 0  # debugonly, otherwise set to 0

# extract params
ExtractParams(sys.argv)


loopNo = 1
while True:
    loopDirty = False

    interface = ConnectToNode(targetName)

    ourNode = interface.getNode('^local')
    # print(f'{INFOlbl}Our node existing localConfig {vno}:{ourNode.localConfig}')
    # print(f'{INFOlbl}Our node existing moduleConfig {vno}:{ourNode.moduleConfig}')

    # localConfigs
    print(f'{INFOlbl}start loop {loopNo} of updating preferences {vno}')
    print(f'{INFOlbl}\tupdate localConfig...')
    # ourNode.beginSettingsTransaction()

    # bluetooth
    if not (targetName.startswith('BLE')):
        # False if wifiNetworkParams.enabled else True
        prev = deepcopy(ourNode.localConfig.bluetooth)
        ourNode.localConfig.bluetooth.enabled = True
        ourNode.localConfig.bluetooth.fixed_pin = int(  # max 6 digits , add trail zeros if less
            str(customSettings.bluetoothPIN)[:6].ljust(6, '0'))
        ourNode.localConfig.bluetooth.mode = ourNode.localConfig.bluetooth.FIXED_PIN
        if prev != ourNode.localConfig.bluetooth:
            loopDirty = True
            print(f'{INFOlbl}\t\tupdate bluetooth...')
            ourNode.writeConfig("bluetooth")
    else:
        print(f'{INFOlbl}\t\tconnected by BLE - bluetooth cant be changed...')

    # device
    prev = deepcopy(ourNode.localConfig.device)
    ourNode.localConfig.device.node_info_broadcast_secs = 3600 + vno
    ourNode.localConfig.device.rebroadcast_mode = ourNode.localConfig.device.LOCAL_ONLY
    ourNode.localConfig.device.role = customSettings.nodeRole
    ourNode.localConfig.device.serial_enabled = True
    if prev != ourNode.localConfig.device:
        loopDirty = True
        print(f'{INFOlbl}\t\tupdate device...')
        ourNode.writeConfig("device")

    # display
    prev = deepcopy(ourNode.localConfig.display)
    ourNode.localConfig.display.gps_format = ourNode.localConfig.display.MGRS
    ourNode.localConfig.display.screen_on_secs = 60 + vno
    ourNode.localConfig.display.units = ourNode.localConfig.display.METRIC
    if prev != ourNode.localConfig.display:
        loopDirty = True
        print(f'{INFOlbl}\t\tupdate display...')
        ourNode.writeConfig("display")

    # interface.close()
    # exit(0)
    # lora
    prev = deepcopy(ourNode.localConfig.lora)
    ourNode.localConfig.lora.hop_limit = 7
    ourNode.localConfig.lora.override_duty_cycle = True
    ourNode.localConfig.lora.region = ourNode.localConfig.lora.NZ_865
    ourNode.localConfig.lora.sx126x_rx_boosted_gain = True
    ourNode.localConfig.lora.tx_enabled = True
    ourNode.localConfig.lora.tx_power = 20
    ourNode.localConfig.lora.use_preset = True
    ourNode.localConfig.lora.override_frequency = 433.625
    if prev != ourNode.localConfig.lora:
        print(f'{INFOlbl}\t\tupdate lora...')
        ourNode.writeConfig("lora")

    # network
    prev = deepcopy(ourNode.localConfig.network)
    ourNode.localConfig.network.address_mode = ourNode.localConfig.network.STATIC
    ourNode.localConfig.network.ipv4_config.dns = wifiNetworkParams.dns
    ourNode.localConfig.network.ipv4_config.gateway = wifiNetworkParams.gateway
    ourNode.localConfig.network.ipv4_config.ip = wifiNetworkParams.ip
    ourNode.localConfig.network.ipv4_config.subnet = wifiNetworkParams.subnet
    ourNode.localConfig.network.wifi_psk = wifiNetworkParams.wifi_psk
    ourNode.localConfig.network.wifi_ssid = wifiNetworkParams.wifi_ssid
    ourNode.localConfig.network.wifi_enabled = wifiNetworkParams.enabled  # True | False
    if prev != ourNode.localConfig.network:
        loopDirty = True
        print(f'{INFOlbl}\t\tupdate network...')
        ourNode.writeConfig("network")

    # position
    prev = deepcopy(ourNode.localConfig.position)
    if customSettings.gpsMode == ourNode.localConfig.position.GpsMode.ENABLED:
        # mobile node
        ourNode.localConfig.position.gps_mode = ourNode.localConfig.position.GpsMode.ENABLED
        ourNode.localConfig.position.position_broadcast_secs = 3600 + vno
        ourNode.localConfig.position.position_broadcast_smart_enabled = True
        ourNode.localConfig.position.broadcast_smart_minimum_distance = 100 + vno
        ourNode.localConfig.position.broadcast_smart_minimum_interval_secs = 30 + vno
        ourNode.localConfig.position.fixed_position = False
        ourNode.localConfig.position.gps_update_interval = 120 + vno
    elif (customSettings.gpsMode == ourNode.localConfig.position.GpsMode.DISABLED
          ) or (customSettings.gpsMode == ourNode.localConfig.position.GpsMode.NOT_PRESENT):
        # stationary node
        ourNode.localConfig.position.gps_mode = ourNode.localConfig.position.GpsMode.DISABLED
        ourNode.localConfig.position.position_broadcast_secs = 86400 + vno
        ourNode.localConfig.position.fixed_position = True

    if prev != ourNode.localConfig.position:
        loopDirty = True
        print(f'{INFOlbl}\t\tupdate position {LALO_ENUM.MOBILE.name}...')
        ourNode.writeConfig("position")

    # moduleConfigs
    print(f'{INFOlbl}\tupdate moduleConfigs...')

    # neighbor_info
    prev = deepcopy(ourNode.moduleConfig.neighbor_info)
    ourNode.moduleConfig.neighbor_info.enabled = True
    ourNode.moduleConfig.neighbor_info.update_interval = 600 + vno
    if prev != ourNode.moduleConfig.neighbor_info:
        loopDirty = True
        print(f'{INFOlbl}\t\tupdate neighbor_info...')
        ourNode.writeConfig("neighbor_info")

    print(f'{INFOlbl}update owner... {vno}')
    ourNode.setOwner(customSettings.longName,
                     customSettings.shortName[:4],
                     is_licensed=False)

    # # it this link is embedded lora settings which are overrided below
    prev = ourNode.getURL()
    if prev != customSettings.channelUrl:
        loopDirty = True
        print(f'{INFOlbl}update channelUrl...')
        ourNode.setURL(customSettings.channelUrl)

    if customSettings.gpsMode == ourNode.localConfig.position.GpsMode.DISABLED:
        # dont move it to config position - it crashed there
        print(f'{INFOlbl}update STATIONARY fixedPosition...')
        ourNode.setFixedPosition(customSettings.fixedLatitude +
                                 vno, customSettings.fixedLongitude + vno,
                                 int(customSettings.fixedAltitude) + vno)

    # ourNode.commitSettingsTransaction()

    print(f'{INFOlbl}... finished loop {loopNo} of updating preferences {vno}')

    if loopDirty:
        print(f'{INFOlbl} there were differences, for check next loop is needed')
        print(f'{INFOlbl} node should reboots now, wait for reconnect...', end='')
        loopNo += 1
        interface.close()
    else:
        print(f'{SUCCESSlbl} compared, and all settings are up to date now')
        print(f'{INFOlbl} node should reboots now')
        print(f'\n{INFOlbl}  It’s now safe to turn off your computer\n')
        break

# print(f'{INFOlbl}Our node updated localConfig {vno}:{ourNode.localConfig}')
# print(f'{INFOlbl}Our node updated moduleConfig {vno}:{ourNode.moduleConfig}')

# time.sleep(20)
# print(f'{INFOlbl} get setting from node...')
# os.popen("meshtastic --port COM4 --export-config > TBEAM-MOB-config.yaml")
# print(f'{INFOlbl} ... and save them')
# uncomment it to prevent immediately closing console window
# os.system("pause")
