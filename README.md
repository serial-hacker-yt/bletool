# bletool

A Python-based Bluetooth Low Energy (BLE) research, scripting, and interaction tool designed for security researchers, reverse engineers, and developers working with BLE devices.

bletool provides both an interactive CLI and a scripting engine for:

- BLE device discovery
- GATT enumeration
- Characteristic read/write operations
- Notification monitoring and analysis
- Protocol replay testing
- Automated BLE workflows
- Keep-alive functionality
- BLE device information dumping
---

### Features

- Interactive BLE CLI
- BLE scripting engine
- Script output logging
- Verbose script execution
- BLE device scanning
- Connect/disconnect support
- GATT service and characteristic enumeration
- Read characteristics by:
  - Handle
  - Hex handle
  - Estimated characteristic value handle
  - UUID
  - Selected characteristic
- Write characteristics with and without response
- Characteristic selection shortcuts
- Handle ↔ UUID abstraction
- Notification monitoring and management
- Notification display customization
- Notification timestamp support
- Notification diff highlighting for protocol analysis
- Replay previously sent write operations
- Keep-alive task support
- GATT and advertisement data dumping to JSON
- Session status and device information reporting
- Tab completion
- Colored interactive prompt
- Automated integration testing with pytest
---

## Disclaimer

This tool is intended for authorized BLE security research, testing, and educational purposes only.

Only use this tool against devices you own or have explicit permission to test.

---

## Installation

### Clone the Repository

```bash
git clone https://github.com/serial-hacker-yt/bletool.git
cd bletool
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Usage

### Start Interactive Mode

Launch the interactive BLE CLI:

```bash
python3 bletool.py -I
```

Optionally preload a target MAC address:

```bash
python3 bletool.py -I -b AA:BB:CC:DD:EE:FF
```

---


### Script Mode

#### Example Scripts

The `examples/` directory contains several example workflows:

| Script | Description |
|---------|-------------|
| enumerate.bts | Device enumeration and dumping |
| notification_capture.bts | Capture BLE notifications |

bletool supports executing BLE workflows from scripts.

Execute a script:

```bash
python3 bletool.py -sc myscript.bts
```

Enable verbose execution:

```bash
python3 bletool.py -sc myscript.bts -v
```

Save output to a file:

```bash
python3 bletool.py -sc myscript.bts -o output.log
```

Example script:

```text
connect 48:27:E2:08:B4:CE
notify 49 start
sleep 10
notify 49 stop
disconnect
```

Example verbose output:

```text
[1] connect 48:27:E2:08:B4:CE
Attempting to connect...
[+] Connected!

[2] notify 49 start
Notifications started for 70d51002-2c7f-4e75-ae8a-d758951ce4e0

70d51002-2c7f-4e75-ae8a-d758951ce4e0 (Handle: 49):
1eff020907304c420c031ae800...

[4] notify 49 stop
Notifications stopped
```

### Scanning

Scan for nearby BLE devices:

```bash
python3 bletool.py -S
```

Or from interactive mode:

```bash
scan
```

Example output:

```text
Device: DeviceName | Address: AA:BB:CC:DD:EE:FF
```

---

### Connecting

Connect to a BLE device:

```bash
connect AA:BB:CC:DD:EE:FF
```

If a MAC address was preloaded:

```bash
connect
```

Disconnect from the current device:

```bash
disconnect
```

---

### Enumerating Services and Characteristics

List all discovered characteristics:

```bash
characteristics
```

Show handle-to-UUID mappings:

```bash
handles
```

Example:

```text
Handle: 43 (0x002B) | Estimated Char value handle: 44 (0x002C) -> UUID: 0000ff02-0000-1000-8000-00805f9b34fb | Properties: ['read', 'notify']
```

Hex Handle Support

bletool supports decimal handles, hexadecimal handles, and estimated characteristic value handles.

Examples:

```bash
read-char 47
read-char 0x2F
read-char 48
read-char 0x30
```

All handle formats are automatically normalized to the correct BLE characteristic UUID.

---

### Selecting Characteristics

Once a characteristic is selected, commands such as `read-char`, `char-write-cmd`, and `char-write-req` can be executed without specifying the handle again.

Select a characteristic by handle:

```bash
select 43
```

Or by UUID:

```bash
select 0000ff02-0000-1000-8000-00805f9b34fb
```

Deselect the current characteristic:

```bash
deselect
```

Example workflow:

```bash
select 47
read-char

select 47
char-write-cmd 0100
```

---

### Reading Characteristics

Read by handle:

```bash
read-char 43
```

Read by UUID:

```bash
read-char 0000ff02-0000-1000-8000-00805f9b34fb
```

Read the currently selected characteristic:

```bash
select 43
read-char
```

---

### Writing Characteristics

#### Write With Response

```bash
char-write-req <handle> <hex-data>
```

Example:

```bash
char-write-req 43 0100
```

#### Write Without Response

```bash
char-write-cmd <handle> <hex-data>
```

Example:

```bash
char-write-cmd 43 0100
```

#### Write to Selected Characteristic

```bash
select 43
char-write-cmd 0100
```

---

### Replay Testing

Replay the last write operation:

```bash
replay
```

Useful for:

- Protocol testing
- Replay validation
- Reverse engineering workflows
- Device state analysis

---

### Notifications

Start notifications:

```bash
notify <handle> start
```

Example:

```bash
notify 43 start
```

Stop notifications:

```bash
notify <handle> stop
```

Example:

```bash
notify 43 stop
```

Stop all active notifications:

```bash
notify stop
```

View notification status:

```bash
notify status
```

Example status output:

```text
Handle 43: Running
Handle 49: Stopped
```

Example notification output:

```text
[NOTIFY] 43: 01020304
```

---

### Notification Display Settings

Control how incoming notification data is displayed.

Show current settings:

```bash
notify-display status
```

Enable timestamps:

```bash
notify-display timestamps on
```

Disable timestamps:

```bash
notify-display timestamps off
```

Enable packet counters:

```bash
notify-display counters on
```

Disable packet counters:

```bash
notify-display counters off
```

Enable alternating row colors:

```bash
notify-display colors on
```

Disable alternating row colors:

```bash
notify-display colors off
```

Enable byte-level diff highlighting:

```bash
notify-display diffs on
```

Disable diff highlighting:

```bash
notify-display diffs off
```

Example status output:

```text
{
    'timestamps': False,
    'counters': False,
    'diffs': False,
    'colors': False
}
```

Example notification output with timestamps and counters enabled:

```text
[19:55:37.191] [22] 70d51002-2c7f-4e75-ae8a-d758951ce4e0 (Handle: 49): 1eff0209073000420c0c182000be00000001f0000000ffff0002f00000003db80602f0000080ffff0008f0000080ffff0008f0000000
```

When diff highlighting is enabled, changed bytes between consecutive notifications are visually highlighted, making it easier to identify protocol fields that change in response to device activity.

---

### Keep Alive

Some BLE devices disconnect when idle. The keep-alive feature periodically writes data to a characteristic to maintain the connection.

Start keep-alive:

```bash
keep-alive <handle> <hex-data> start
```

Example:

```bash
keep-alive 43 0100 start
```

Stop keep-alive:

```bash
keep-alive stop
```

Check keep-alive status:

```bash
keep-alive status
```



---

### Device Information Dumping

Dump advertisement and GATT information to JSON:

```bash
dump mydevice
```

Creates:

```text
mydevice.json
```

The dump includes:

- Advertisement data
- RSSI
- Manufacturer data
- Services
- Characteristics
- Descriptors

---

### Session Information

Display current session information:

```bash
info
```

Example output:

```text
MAC: AA:BB:CC:DD:EE:FF
Connected: True
Selected Char: 43
Last Write:
{
    'uuid': '0000ff01-0000-1000-8000-00805f9b34fb',
    'data': b'\x01\x00'
}
```

---

### Help

Display command help:

```bash
help
```

---

### Exit

Exit the interactive session:

```bash
exit
```

or

```bash
quit
```

---

## Intended Use

bletool is intended for:

- BLE security research
- BLE reverse engineering
- Protocol analysis
- Device interoperability testing
- BLE automation and scripting
- Device fuzzing and experimentation
- Educational use
- Authorized security assessments

Always obtain permission before testing devices you do not own.

---

## License

This project is licensed under the MIT License.
