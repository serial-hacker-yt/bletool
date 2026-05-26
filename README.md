# bletool
A Python-based BLE (Bluetooth Low Energy) research and interaction tool designed for security researchers, reverse engineers, and developers working with BLE devices.

This tool provides an interactive CLI for:
- BLE device discovery
- GATT enumeration
- Characteristic read/write operations
- Notification monitoring
- Replay testing
- Keep-alive functionality
- BLE device information dumping

---

# Features

- Interactive BLE CLI
- BLE scanning
- Connect/disconnect support
- Read/write GATT characteristics
- Replay previously sent commands
- Notification monitoring
- Keep-alive task support
- GATT/service dumping to JSON
- Handle ↔ UUID mapping
- Characteristic selection shortcuts
- Tab completion
- Colored interactive prompt

## Disclaimer

This tool is intended for authorized BLE security research, testing, and educational purposes only.

Only use this tool against devices you own or have explicit permission to test.

---

# Installation

## Clone the repository

```bash
git clone https://github.com/serial-hacker-yt/bletool.git
cd bletool
```

## Install dependencies

```bash
pip install -r requirements.txt
```
# Usage

## Start Interactive Mode

Launch the interactive BLE CLI:

```bash
python3 bletool.py -I
```
You can optionally pre-load a target MAC address:

```bash
python3 bletool.py -I -b AA:BB:CC:DD:EE:FF
```

## Scanning

Scan for nearby BLE devices:

```bash
python3 bletool.py -S
```

Or in interactive mode:

```bash
scan
```

Example output:

Device: DeviceName | Address: AA:BB:CC:DD:EE:FF


## Connecting

Connect to a BLE device:

```bash
connect AA:BB:CC:DD:EE:FF
```

Or if you preloaded the MAC:

```bash
connect
```

## Disconnect from the current device:
```bash
disconnect
```

## Enumerating Services and Characteristics

### List all discovered characteristics:
```bash
characteristics
```
### Show handle → UUID mappings:
```bash
handles
```
Example:

Handle: 43 -> UUID: 0000ff02-0000-1000-8000-00805f9b34fb | Properties: ['read', 'notify']

### Selecting Characteristics

Select a characteristic for future commands:
```bash
select 43
```
or:
```bash
select 0000ff02-0000-1000-8000-00805f9b34fb
```
### Deselect the current characteristic:
```bash
deselect
```

### Reading Characteristics

Read a characteristic directly:
```bash
read-char 43
```
or using a UUID:
```bash
read-char 0000ff02-0000-1000-8000-00805f9b34fb
```
If a characteristic is already selected:
```bash
select 43
read-char
```
## Writing Characteristics

Write With Response
```bash
char-write-req 41 0100
```
Write Without Response
```bash
char-write-cmd 41 0100
```

Write To Selected Characteristic
```bash
select 41
char-write-cmd 0100
```
### Replay Attacks

Replay the last write operation:
```bash
replay
```
Useful for:

protocol testing
replay validation
reverse engineering workflows
Notifications

## Start notifications on a characteristic:
```bash
notify 43 start
```
Stop notifications:
```bash
notify 43 stop
```
Notification data will automatically appear in the CLI:

[NOTIFY] 43: 01020304

## Keep Alive

Some BLE devices disconnect if no traffic is sent.
The keep-alive feature continuously writes a value to a characteristic to maintain the connection.

Start keep-alive:
```bash
keep-alive start 41 <hex data>
```
Stop keep-alive:
```bash
keep-alive stop
```
Check status:
```bash
keep-alive status
```
Device Information Dumping

## Dump advertisement and GATT information to JSON:
```bash
dump mydevice
```
This creates:

mydevice.json

The dump includes:

advertisement data
RSSI
manufacturer data
services
characteristics
descriptors
Session Information

## Display current session state:
```bash
info
```
Example:

MAC: AA:BB:CC:DD:EE:FF
Connected: True
Selected Char: 41
Last write: {'uuid': '0000ff01...', 'data': b'\x01\x00'}

## Help

Display command help:
```bash
help
```

## Exit

Exit the interactive session:
```bash
exit
```
or:
```bash
quit
```
