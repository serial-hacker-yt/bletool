import argparse
import asyncio


import os
import sys
import json

from bleak import BleakClient
from bleak import BleakScanner
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit import print_formatted_text


from datetime import datetime

dt = datetime.now()
timestamp = dt.timestamp()


parser = argparse.ArgumentParser(
    description="Bluetooth Low Energy (BLE) research utility for device interaction, scripting, protocol analysis, and security testing"
)

parser.add_argument(
    "-b",
    "--mac",
    help="MAC address of target"
)

parser.add_argument(
    "-n",
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

parser.add_argument(
    "-sc",
    "--script",
    help="Select a script file to run"
)

parser.add_argument(
    "-o",
    "--output",
    help="Ouput script results into a file"
)

parser.add_argument(
    "-v",
    "--verbose",
    action="store_true",
    help="Verbose logging for scripts"
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
        self.previous_notification = None
        self.notification_status = {}
        self.notify_settings = {
                                "timestamps": False,
                                "counters": False,
                                "diffs": False,
                                "colors": False,
                                }
        self.notificationCounter = 0
        self.scriptMode = False

class CommandCompleter(Completer):

    def get_completions(self, document, complete_event):

        text = document.text_before_cursor

        for cmd in commands.keys():
            if cmd.startswith(text):
                yield Completion(cmd, start_position=-len(text))

class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)

    def flush(self):
        for stream in self.streams:
            stream.flush()

    def isatty(self):
        return self.streams[0].isatty()
    
    def fileno(self):
        return self.streams[0].fileno()

    @property
    def encoding(self):
        return self.streams[0].encoding


## Helper Functions

def parseHandle(value):
    try:
        return int(value, 0)
    except (ValueError, TypeError):
        try:
            return int(value, 16)
        except (ValueError, TypeError):
            return None


def uuidMap(session, parts):
    try:
        addresses = {}

        for service in session.client.services:
            for hnd in service.characteristics:
                addresses[hnd.handle] = hnd.uuid
                addresses[hnd.handle + 1] = hnd.uuid

        if isinstance(parts, str):
            parts = [parts]

        if len(parts) > 1:
            value = parts[1]
        elif session.char:
            value = session.char
        else:
            value = parts[0]

        handle = parseHandle(value)

        if handle is not None:
            return addresses.get(handle)

        return value

    except Exception as e:
        print(f"Error: {e}")
        return None

def format_notification(session):

    notification = session.notifications.pop(0)

    parts = []

    if session.notify_settings["timestamps"]:
        parts.append(
            f"[{notification['timestamp']}]"
        )

    if session.notify_settings["counters"]:
        parts.append(
            f"[{notification['counter']}]"
        )

    data = notification["data"].hex()
    sender = notification['sender']

    if session.notify_settings["colors"]:

        color = (
            "ansicyan"
            if notification["counter"] % 2 == 0
            else "ansiwhite"
        )

        sender = (
            f"<{color}>{notification['sender']}</{color}>"
        )


    if session.notify_settings["diffs"]:

        if session.previous_notification is not None:

            previous = session.previous_notification
            current = notification["data"]


            diff_output = []

            for old, new in zip(previous, current):

                if old != new:
                    diff_output.append(
                        f"<ansired>{new:02x}</ansired>"
                    )
                else:
                    diff_output.append(
                        f"{new:02x}"
                    )

            data_str = "".join(diff_output)

            session.previous_notification = notification["data"]

            parts.append(
                f"{sender}: {data_str}"
            )


        else:
            parts.append(
                f"{sender}: {data}"
            )

            session.previous_notification = notification["data"]

    else:

        parts.append(
            f"{sender}: {data}"
        )

    return HTML(" ".join(parts))

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

        print("[-] Disconnecting...")

        await session.client.disconnect()


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

                    value_handle = char.handle + 1

                    print(
                        f"Handle: {char.handle} (0x{char.handle:04X}) | Estimated Char value handle: {value_handle} (0x{value_handle:04X}) -> "
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

    timestamp = datetime.now().strftime(
        "%H:%M:%S.%f"
    )[:-3]
    session.notificationCounter += 1

    session.notifications.append({
        "counter": session.notificationCounter,
        "timestamp": timestamp,
        "sender": sender,
        "data": data
    })


## Commands

async def connect_command(session, parts):

    if session.connected:
        print("Device already connected")
    else:

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

    if len(parts) <= 2 and not session.char:

        print("Usage: char-write-req <hnd/uuid> <data>")

    else:

        await device_write_request(session, parts)


async def write(session, parts):

    if len(parts) <= 2 and not session.char:

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


    if len(parts) < 2:
        print("Usage: notify <stop/status>"
              "Usage: notify <handle/uuid> <start/stop>")
        return
        
    if parts[1] == "status":
        print(f'Notification status: {session.notification_status}')
        return
    
    if parts[1] == "stop":

        handles = list(session.notification_status.keys())

        for handle in handles:

            uuid = uuidMap(session, handle)

            if session.notification_status[handle] != "Stopped":

                session.notification_status[handle] = "Stopped"

                await session.client.stop_notify(uuid)
            

        print("All notifications stopped")

        return


    if len(parts) < 3:
        print("Usage: notify <stop/status>"
              "Usage: notify <handle/uuid> <start/stop>")
        return

    elif parts[2] == "start":

        session.notificationCounter = 0 

        if session.notification_status.get(parts[1]) == "Running":
            print("Notifications already running")
            return

        else:
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

        if session.notification_status.get(parts[1], "Stopped") == "Stopped":
            print(f"Notifications are off for handle {parts[1]}")
        else:

            await session.client.stop_notify(uuid)

            print(f"Notifications stopped for {uuid}")

            session.notification_status[parts[1]] = "Stopped"

    else:
        print("Unknown Command")
    
async def notification_loop(session):

    while True:

        while session.notifications:
            try:
                print_formatted_text(
                    format_notification(session)
                )
            except Exception as e:
                print(f"Notification formatting error: {e}")

        await asyncio.sleep(0.05)

async def notify_display_settings(session, parts):


    if len(parts) < 2:
        print(
            "Usage:\n"
            "notify-display status\n"
            "notify-display <setting> on/off"
        )
        return

    if parts[1] == "status":
        print(session.notify_settings)
        return

    if len(parts) < 3:
        print(
            "Usage:\n"
            "notify-display status\n"
            "notify-display <setting> on/off"
        )
        return
    
    setting = parts[1]
    value = parts[2]

    if setting not in session.notify_settings:
        print(f"Unknown setting: {setting}")
        return

    if value not in ["on", "off"]:
        print("Value must be on or off")
        return

    session.notify_settings[setting] = (value == "on")

    print(f"{setting} {value}")

  
async def scriptEngine(session, file):
    
    lineNum = 0

    with open(file, "r") as script:
        for line in script:


            lineNum += 1


            line = line.strip()

            if not line or line.startswith("#"):
                continue

            command = line.split() 
            try:

                if not line.strip():
                    continue

                elif command[0] in commands:

                    if args.verbose:
                        print(f'[{lineNum}]> {line}')
                    
                    await commands[command[0]](session, command)


                elif line[0] == "#":
                    continue

                elif command[0] == "sleep":
                    
                    await asyncio.sleep(int(command[1]))
                    
                else:
                    print(f"Error on line {lineNum}")
                    break

            except Exception as e:
                print(f"{e} on {lineNum}")

    if session.connected:
        await disconnect_command(session, [])


async def help_command(session, parts):

    print("""

BLETool Commands
================

Connection
----------
connect <mac>
    Connect to BLE device

disconnect
    Disconnect from current device

scan
    Scan for nearby BLE devices


GATT Enumeration
----------------
characteristics
    List UUIDs, handles, and properties

handles
    Show handle -> UUID mapping
    Handle: Characteristic declaration handle.
    Char Value Handle: The ATT handle typically used for reads, writes, and notifications, shown in both decimal and hexadecimal.

info
    Show current session information

dump <filename>
    Dump BLE device information to JSON


Characteristic Selection
------------------------
select <handle|uuid>
    Select characteristic

deselect
    Clear selected characteristic


Characteristic Operations
-------------------------
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


Notifications
-------------
notify <handle> start
    Start notifications

notify <handle> stop
    Stop notifications

notify stop
    Stop all notifications

notify status
    Show active notification subscriptions


Notification Display
--------------------
notify-display timestamps on/off
    Toggle notification timestamps

notify-display counters on/off
    Toggle notification counters

notify-display colors on/off
    Alternate notification row colors

notify-display diffs on/off
    Highlight changed bytes

notify-display status
    Show current display settings


Keep Alive
----------
keep-alive <handle> <value> start
    Start keep-alive task

keep-alive stop
    Stop keep-alive task

keep-alive status
    Show keep-alive status


Miscellaneous
-------------
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
    "notify": notify,
    "notify-display": notify_display_settings

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
    print("bletool v1.2 - BLE Research Utility")
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
            
            elif not session.connected and cmd not in ["connect", "scan", "help", "exit", "quit", "notify-display"]:
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

    elif args.script:

        path = args.script
        session = Session()

        session.scriptMode = True
        notif_task = asyncio.create_task(notification_loop(session))



        if os.path.isfile(path):

            print(f"Running script: {path}")

            if args.output:

                logfile = open(args.output, "w")

                original_stdout = sys.stdout

                sys.stdout = Tee(
                    original_stdout,
                    logfile
                )

                try:
                    await scriptEngine(session, path)

                finally:
                    notif_task.cancel()



                    try:
                        await notif_task
                    except asyncio.CancelledError:
                        pass

                    sys.stdout = original_stdout
                    logfile.close()

            else:
                await scriptEngine(session, path)

    else:

        print("Use -h for help")

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Exiting...")
