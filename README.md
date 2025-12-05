# OpenOCD Python Flasher

Version: 0.001

A Python script for managing OpenOCD connections and performing common embedded development operations on STM32 microcontrollers.

## Features

- Automatic OpenOCD process management
- Telnet connection to OpenOCD
- Interactive menu-driven interface
- Common operations:
  - Halt/Reset MCU
  - Erase flash memory
  - Flash firmware
  - Verify firmware
  - Read/Write memory locations
  - Send custom OpenOCD commands

## Requirements

- Python 3.6+
- OpenOCD installed and in PATH
- Target hardware connected via debug probe (ST-Link, J-Link, etc.)

## Installation

1. Install OpenOCD:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install openocd

   # macOS
   brew install openocd

   # Windows
   # Download from https://openocd.org/
   ```

2. Clone or download this script

3. Make the script executable:
   ```bash
   chmod +x main.py
   ```

## Configuration

The script is pre-configured for ST-Link debug probe and supports the following STM32 targets:

- **STM32L0** series (target/stm32l0.cfg)
- **STM32L4** series (target/stm32l4x.cfg)

No additional configuration files are needed. Simply select your target when prompted during script startup.

## Usage

Run the script:
```bash
python3 main.py
```

Or:
```bash
./main.py
```

You'll be prompted to select your target:
```
Select target:
1. L0 (target/stm32l0.cfg)
2. L4 (target/stm32l4x.cfg)
Enter your choice (1 or 2):
```

After selecting your target, you'll see an interactive menu with the following options:

1. **Halt MCU** - Stop the microcontroller
2. **Reset and Halt MCU** - Reset and immediately halt
3. **Reset and Run MCU** - Reset and let it run
4. **Erase Flash** - Erase the flash memory
5. **Flash Firmware** - Program firmware to the device
6. **Verify Firmware** - Verify programmed firmware
7. **Read Memory** - Read from memory address
8. **Write Memory** - Write to memory address
9. **Get Target Info** - Display target information
10. **Send Custom Command** - Send any OpenOCD command
11. **Reconnect to OpenOCD** - Reconnect telnet session
12. **Exit** - Clean up and exit

## Example Workflow

### Flashing Firmware

1. Start the script: `python3 main.py`
2. Select target: `1` (for L0) or `2` (for L4)
3. Select option `4` to erase flash
4. Select option `5` to flash firmware
5. Enter firmware path: `build/firmware.bin`
6. Select option `6` to verify
7. Select option `3` to reset and run

### Reading Memory

1. Select option `7` (Read Memory)
2. Enter address: `0x08000000` (flash start on STM32)
3. Enter count: `16` (read 16 words)

### Writing to Memory

1. Select option `8` (Write Memory)
2. Enter address: `0x20000000` (RAM address)
3. Enter value: `0x12345678`

## Troubleshooting

### OpenOCD fails to start

- Check that OpenOCD is installed: `openocd --version`
- Ensure your ST-Link debug probe is connected
- Verify you selected the correct target for your MCU

### Cannot connect via telnet

- Check that OpenOCD started successfully
- Verify the telnet port (default: 4444)
- Try connecting manually: `telnet localhost 4444`

### Flash/Programming errors

- Ensure the MCU is halted before flashing
- Check that the firmware file path is correct
- Verify the firmware is compatible with your target

## Python Version Note

This script uses `telnetlib` which is deprecated in Python 3.11+ and removed in Python 3.13+. If you're using Python 3.13+, you may need to:
- Use Python 3.12 or earlier, or
- Replace `telnetlib` with an alternative like `socket` or a third-party library

## License

GPL-3.0
