## Tool with the goal of aiding researchers
## with BLE replay attacks


import argparse
import asyncio


import os
import json

from bleak import BleakClient
from bleak import BleakScanner
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.completion import Completer, Completion


parser = argparse.ArgumentParser(
    description="BLE replay and interaction tool"
)

parser.add_argument(
    "-b",
    "--mac",
    help="MAC address of target"
)

parser.add_argument(
    "-v",
    "--value",
    help="Hex value of write request/command"
)

parser.add_argument(
    "-S",
    "--scan",
    action="store_true",
    help="Scan for BLE devices"
)

parser.add_argument(
    "-I",
    "--interactive",
    action="store_true",
    help="Interactive mode"
)

args = parser.parse_args()


class Session:

    def __init__(self):

        self.mac = None
        self.client = None
        self.connected = False
        self.char = None
        self.last_write = None
        self.keepAliveTask = None
        self.notifications = []
        self.notification_status = {}

class CommandCompleter(Completer):

    def get_completions(self, document, complete_event):

        text = document.text_before_cursor

        for cmd in commands.keys():
            if cmd.startswith(text):
                yield Completion(cmd, start_position=-len(text))


## Helper Functions

def uuidMap(session, parts):
        
    try:

        addresses = {}

        for service in session.client.services:
            for hnd in service.characteristics:

                addresses[hnd.handle] = hnd.uuid

        if session.char and session.char.isdigit():
            uuid = addresses.get(int(session.char))

        elif session.char and not session.char.isdigit():
            uuid = session.char

        elif not session.char and parts[1].isdigit():
            uuid = addresses.get(int(parts[1]))


        else:
            uuid = parts[1]

        return uuid
    
    except Exception as e:
        print(f"Error: {e}")


## BLE Command functions

async def scan():



    try:
        print("Scanning for BLE devices...\n")

        devices = await BleakScanner.discover()

        for device in devices:

            print(
                f"Device: {device.name} | "
                f"Address: {device.address}"
            )

    except Exception as e:
        print(f"Error: {e}")
        print("Ensure BLE adpater is connected")

def handle_disconnect(session):
    print("[-] Device was disconnected")
    session.connected = False




async def connect_device(session, mac):

    print(f"Attempting to connect to: {mac}")

    try:

        client = BleakClient(mac,  disconnected_callback=lambda cli: handle_disconnect(session))

        await client.connect()

        for service in client.services:
            pass

        if client.is_connected:

            session.client = client
            session.mac = mac
            session.connected = True
            session.char = None

            print("[+] Connected!")

        else:

            print("[-] Failed to connect")

    except Exception as e:

        print(f"Error: {e}")


async def disconnect_device(session):

    if session.keepAliveTask:

        session.keepAliveTask.cancel()
        session.keepAliveTask = None

    if session.client and session.connected:

        await session.client.disconnect()

        print("[-] Disconnected")

        session.client = None
        session.connected = False
        session.mac = None
        session.char = None

    else:

        print("[-] No active connection")


async def services_device(session):

    if session.connected:

        try:

            for service in session.client.services:
                for char in service.characteristics:

                    print(
                        f"UUID: {char.uuid} | "
                        f"Handle: {char.handle} | "
                        f"Properties: {char.properties}"
                    )
        except Exception as e:
            print(f"Error: {e}")

    else:

        print("Connect to device first.")


async def device_write_request(session, parts):

    try:
        if session.char:

            data = bytes.fromhex(parts[1])

        else:

            data = bytes.fromhex(parts[2])

        uuid = uuidMap(session, parts)

        await session.client.write_gatt_char(
            uuid,
            data,
            response=True
        )


        session.last_write = {
            "uuid": uuid,
            "data": data,
            "response": True
        }

        print("[+] Command sent")

    except Exception as e:
        print(f"Error: {e}")


async def device_write(session, parts):

    try:
        if session.char:

            data = bytes.fromhex(parts[1])

        else:

            data = bytes.fromhex(parts[2])

        uuid = uuidMap(session, parts)

        await session.client.write_gatt_char(
            uuid,
            data,
            response=False
        )

        session.last_write = {
            "uuid": uuid,
            "data": data,
            "response": False
        }

        print("[+] Command sent")
    except Exception as e:
        print(f"Error: {e}")


async def read_characteristics(session, parts):

    try:

        if session.char:

            uuid = uuidMap(session, parts)

            value = await session.client.read_gatt_char(
                uuid
            )

        else:

            uuid = uuidMap(session, parts)

            value = await session.client.read_gatt_char(
                uuid
            )

        print(f"Characteristic: {value.hex()}")

    except Exception as e:
        print(f"Error: {e}")


async def device_handles(session):
    
    try:

        if session.connected:

            for service in session.client.services:
                for char in service.characteristics:

                    print(
                        f"Handle: {char.handle} -> "
                        f"UUID: {char.uuid} | "
                        f"Properties: {char.properties}"
                    )

        else:

            print("Connect to device first.")

    except Exception as e:
        print(f"Error: {e}")


async def dump_device_info(session, parts):
        
    try:

        dump_data = {
            "mac": session.mac,
            "advertisement": {},
            "gatt": {
                "services": []
            }
        }

        devices_and_adv = await BleakScanner.discover(
            return_adv=True
        )

        for address, (device, adv_data) in devices_and_adv.items():

            if address.upper() == session.mac.upper():

                dump_data["advertisement"] = {

                    "name": device.name,
                    "rssi": adv_data.rssi,

                    "manufacturer_data": {

                        str(k): v.hex()

                        for k, v in adv_data.manufacturer_data.items()

                    } if adv_data.manufacturer_data else {}
                }

                break

        for service in session.client.services:

            service_entry = {
                "uuid": service.uuid,
                "handle": service.handle,
                "characteristics": []
            }

            for char in service.characteristics:

                char_entry = {
                    "uuid": char.uuid,
                    "handle": char.handle,
                    "properties": list(char.properties),
                    "descriptors": []
                }

                for desc in char.descriptors:

                    char_entry["descriptors"].append({
                        "uuid": desc.uuid,
                        "handle": desc.handle
                    })

                service_entry["characteristics"].append(
                    char_entry
                )

            dump_data["gatt"]["services"].append(
                service_entry
            )

        if len(parts) < 2:

            filename = "dump_" + session.mac

        else:

            filename = parts[1]

        with open(f"{filename}.json", "w") as f:

            json.dump(dump_data, f, indent=4)

        print(f"[+] Dump saved to {filename}.json")

    except Exception as e:
        print(f"Error: {e}")


async def keep_alive_loop(session, parts):

    data = bytes.fromhex(parts[2])

    uuid = uuidMap(session, parts)

    try:

        while True:

            await session.client.write_gatt_char(
                uuid,
                data,
                response=False
            )


            await asyncio.sleep(3)

    except asyncio.CancelledError:

        print("[-] Keep alive stopped")

    except Exception as e:

        print(f"[-] Keepalive error: {e}")

def notify_callback(sender, data, session):

    session.notifications.append(
        f"[NOTIFY] {sender}: {data.hex()}"
    )


## Commands

async def connect_command(session, parts):

    if not session.mac:

        if len(parts) < 2:
            print("Usage: connect <mac>")
            return

        mac = parts[1]

        await connect_device(session, mac)

    else:

        await connect_device(session, session.mac)


async def scan_command(session, parts):

    await scan()


async def disconnect_command(session, parts):

    await disconnect_device(session)


async def services_command(session, parts):

    await services_device(session)


async def write_req(session, parts):

    if len(parts) < 2:

        print("Usage: char-write-req <hnd/uuid> <data>")

    else:

        await device_write_request(session, parts)


async def write(session, parts):

    if len(parts) < 2:

        print("Usage: char-write-cmd <hnd/uuid> <data>")

    else:

        await device_write(session, parts)


async def select_char(session, parts):

    if len(parts) < 2:

        print("Usage: select <uuid/hnd>")
        return

    session.char = parts[1]

    print(f"[+] Selected: {session.char}")


async def deselect_char(session, parts):

    session.char = None

    print("[+] Deselected characteristic")


async def replay_attack(session, parts):

    if not session.last_write:

        print("Send a command first before replaying it")
        return

    await session.client.write_gatt_char(

        session.last_write["uuid"],
        session.last_write["data"],
        response=session.last_write["response"]

    )

    print("[+] Replay sent")


async def read_char(session, parts):

    if not session.char and len(parts) < 2:

        print("Usage: read-char <uuid/handle>")
        return

    await read_characteristics(session, parts)


async def session_info(session, parts):

    print(f"""
MAC: {session.mac}
Connected: {session.connected}
Selected Char: {session.char}
Last write: {session.last_write}
Notifications: {session.notification_status}
""")


async def handle(session, parts):

    await device_handles(session)


async def dump_info(session, parts):

    await dump_device_info(session, parts)


async def keepAlive(session, parts):

    if (
        len(parts) < 2 or
        (len(parts) < 4 and parts[1] not in ["stop", "status"])
    ):
        print(
            "Usage:\n" 
            "keep-alive <handle> <value> <start>\n"
            "keep-alive <status/stop>"
        )
        return


    if parts[1] == "stop":

        if not session.keepAliveTask:

            print("[-] Keep alive not running")
            return

        session.keepAliveTask.cancel()

        session.keepAliveTask = None

    elif parts[1] == "status":

        if session.keepAliveTask:

            print("[+] Keep alive running")

        else:

            print("[-] Keep alive stopped")
    
    elif parts[3] == "start":

        if session.keepAliveTask:

            print("[-] Keep alive already running")
            return

        session.keepAliveTask = asyncio.create_task(
            keep_alive_loop(session, parts)
        )

        print("[+] Keep alive started")
    
    else:
        print("Usage: keep-alive <handle> <value> <start> \nkeep-alive <status/stop>")

async def notify(session, parts):

    if len(parts) < 3:
        print("Usage: notify <handle/uuid> <start/stop>")

    elif parts[2] == "start":

        uuid = uuidMap(session, parts)

        await session.client.start_notify(
            uuid,
            lambda sender, data: 
                notify_callback(sender, data, session)
        )

        print(f"Notifications started for {uuid}")

        session.notification_status[parts[1]] = "Running"

    elif parts[2] == "stop":

        uuid = uuidMap(session, parts)

        await session.client.stop_notify(uuid)

        print(f"Notifications stopped for {uuid}")

        session.notification_status[parts[1]] = "Stopped"

    else:
        print("Unknown Command")
    
async def notification_loop(session):

    while True:

        while session.notifications:
            print(session.notifications.pop(0))

        await asyncio.sleep(0.05)




async def help_command(session, parts):

    print("""

Available commands:
-------------------

connect <mac>
    Connect to BLE device

disconnect
    Disconnect from current device

scan
    Scan for nearby BLE devices

characteristics
    List UUIDs, handles, and properties

handles
    Show handle -> UUID mapping

select <handle|uuid>
    Select characteristic

deselect
    Clear selected characteristic

read-char <handle|uuid>
    Read characteristic

char-write-req <handle|uuid> <hex>
    Write with response

char-write-cmd <handle|uuid> <hex>
    Write without response

char-write-req <hex>
    Write to selected characteristic

char-write-cmd <hex>
    Write to selected characteristic

replay
    Replay last write command

dump <filename>
    Dump BLE device information to JSON

keep-alive <handle> <value> start
keep-alive stop
keep-alive status 
    Keep connection active
          
notify <handle> <start>
notify <handle> <stop>
    Get data being sent from the device

info
    Show current session info

clear
    Clear screen

help
    Show help menu

exit
quit
    Exit interactive mode

""")


async def clear_screen(session, parts):

    if os.name == "nt":

        os.system("cls")

    else:

        os.system("clear")


## Command registry

commands = {

    "connect": connect_command,
    "scan": scan_command,
    "disconnect": disconnect_command,
    "help": help_command,
    "characteristics": services_command,
    "char-write-req": write_req,
    "char-write-cmd": write,
    "select": select_char,
    "deselect": deselect_char,
    "clear": clear_screen,
    "replay": replay_attack,
    "read-char": read_char,
    "info": session_info,
    "handles": handle,
    "dump": dump_info,
    "keep-alive": keepAlive,
    "notify": notify

}


## Tab completion

def completer(text, state):

    options = [

        cmd for cmd in commands

        if cmd.startswith(text)

    ]

    if state < len(options):

        return options[state]

    else:

        return None


## Interactive mode

async def interactive():
    print("bletool v1.0 - BLE Research Utility")
    session = Session()
    session.loop = asyncio.get_running_loop()

    session_ui = PromptSession(completer=CommandCompleter())

    if args.mac:
        session.mac = args.mac

    notif_task = asyncio.create_task(notification_loop(session))

    with patch_stdout(): 

        while True:

            prompt_mac = session.mac if session.mac else ""
            prompt_char = session.char if session.char else ""

            prompt = HTML(
                f"[ <ansiblue>{prompt_mac}</ansiblue> {prompt_char} ][LE]> "
                if session.connected else
                f"[ <ansired>{prompt_mac}</ansired> {prompt_char} ][LE]> "
            )

            command = await session_ui.prompt_async(prompt)
            command = command.strip()

            if not command:
                continue

            parts = command.split()
            cmd = parts[0]

            if cmd in ["quit", "exit"]:

                if session.connected:
                    await disconnect_device(session)

                break
            
            elif not session.connected and cmd not in ["connect", "scan", "help", "exit", "quit"]:
                print("No device connected")
                continue


            elif cmd in commands:
                await commands[cmd](session, parts)

            else:
                print("[-] Unknown command")

    notif_task.cancel()


## Main function

async def main():

    if args.scan:

        await scan()

    elif args.interactive:

        await interactive()

    elif args.mac:

        session = Session()

        await connect_device(session, args.mac)

    else:

        print("Use -h for help")

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Exiting...")
