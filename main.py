#!/usr/bin/env python3
"""
OpenOCD Python Flasher
Main entry point for the application
"""

import sys
import argparse
from openocd_manager import OpenOCDManager
from ui import select_target, run_interactive_loop
from colors import header, error, success, info
from config_parser import ConfigParser

VERSION = "0.007"


def execute_config_commands(manager, commands):
    """Execute commands from config file

    Args:
        manager: OpenOCDManager instance
        commands: List of command dictionaries

    Returns:
        int: 0 on success, 1 on failure
    """
    print(info(f"\nExecuting {len(commands)} commands from config file...\n"))

    failed = False
    error_message = None

    for i, cmd in enumerate(commands, 1):
        cmd_type = cmd['type']

        # Build display message
        display_parts = [cmd_type]
        if 'filepath' in cmd and cmd['filepath']:
            display_parts.append(cmd['filepath'])
            if cmd.get('address'):
                display_parts.append(f"at {cmd['address']}")
        elif 'address' in cmd and cmd['address']:
            display_parts.append(cmd['address'])
            if cmd.get('count'):
                display_parts.append(f"count:{cmd['count']}")
            elif cmd.get('value'):
                display_parts.append(cmd['value'])
        elif 'param' in cmd and cmd['param']:
            display_parts.append(cmd['param'])

        print(info(f"[{i}/{len(commands)}] Executing: {' '.join(display_parts)}"))

        try:
            if cmd_type == 'halt':
                manager.halt()

            elif cmd_type == 'reset_halt':
                manager.reset_halt()

            elif cmd_type == 'reset_run':
                manager.reset_run()

            elif cmd_type == 'erase_flash':
                manager.erase_flash()

            elif cmd_type == 'flash':
                filepath = cmd.get('filepath')
                address = cmd.get('address')
                # Convert address string to int if provided
                if address:
                    address = int(address, 16) if address.startswith('0x') else int(address, 16)
                manager.flash_firmware(filepath, address)

            elif cmd_type == 'verify':
                filepath = cmd.get('filepath')
                address = cmd.get('address')
                # Convert address string to int if provided
                if address:
                    address = int(address, 16) if address.startswith('0x') else int(address, 16)
                manager.verify_firmware(filepath, address)

            elif cmd_type == 'read_memory':
                address_str = cmd.get('address')
                count_str = cmd.get('count')
                if address_str:
                    address = int(address_str, 16) if address_str.startswith('0x') else int(address_str, 16)
                    count = int(count_str) if count_str else 1
                    manager.read_memory(address, count)
                else:
                    error_message = "Invalid read_memory parameters"
                    print(error(error_message))
                    failed = True
                    break

            elif cmd_type == 'write_memory':
                address_str = cmd.get('address')
                value_str = cmd.get('value')
                if address_str and value_str:
                    address = int(address_str, 16) if address_str.startswith('0x') else int(address_str, 16)
                    value = int(value_str, 16) if value_str.startswith('0x') else int(value_str, 16)
                    manager.write_memory(address, value)
                else:
                    error_message = "Invalid write_memory parameters"
                    print(error(error_message))
                    failed = True
                    break

            elif cmd_type == 'custom':
                manager.custom_command(cmd.get('param'))

            else:
                error_message = f"Unknown command type: {cmd_type}"
                print(error(error_message))
                failed = True
                break

        except Exception as e:
            error_message = f"Error executing command: {e}"
            print(error(error_message))
            failed = True
            break

        print()  # Add blank line between commands

    # If any command failed, perform flash erase
    if failed:
        remaining = len(commands) - i
        if remaining > 0:
            print(error(f"\nSkipping {remaining} remaining command(s) due to failure"))
        print(error("\nPerforming flash erase due to command failure..."))
        try:
            manager.erase_flash()
            print(success("Flash erase completed"))
        except Exception as erase_error:
            print(error(f"Flash erase failed: {erase_error}"))
        print(error("\nTask Failed"))
        return 1

    print(success("All commands executed successfully!"))
    return 0


def main():
    """Main application entry point"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='OpenOCD Manager - Flash and manage STM32 microcontrollers',
        epilog='Example: python main.py config.txt'
    )
    parser.add_argument(
        'config',
        nargs='?',
        help='Path to configuration file for automated operation'
    )

    args = parser.parse_args()

    print(header(f"OpenOCD Manager v{VERSION}"))
    print(header("="*50))

    # Hardcoded interface configuration
    interface_cfg = "interface/stlink.cfg"
    port = 4444
    target_cfg = None
    commands = None

    # Determine mode: config file or interactive
    if args.config:
        # Config file mode
        print(info(f"Loading config file: {args.config}\n"))
        config_parser = ConfigParser(args.config)
        target_cfg, commands = config_parser.parse()

        if not target_cfg:
            return 1

        print(success(f"Target: {target_cfg}"))
        if commands:
            print(info(f"Commands to execute: {len(commands)}"))
    else:
        # Interactive mode
        target_cfg = select_target()
        if not target_cfg:
            return 1

    # Initialize manager
    manager = OpenOCDManager(interface_cfg=interface_cfg, target_cfg=target_cfg, port=port)

    # Start OpenOCD
    if not manager.start_openocd():
        print(error("Failed to start OpenOCD. Exiting..."))
        return 1

    # Connect via telnet
    if not manager.connect_telnet():
        print(error("Failed to connect to OpenOCD. Stopping..."))
        manager.stop_openocd()
        return 1

    # Execute based on mode
    try:
        if commands is not None:
            # Config file mode - execute commands
            result = execute_config_commands(manager, commands)
            return_code = result
        else:
            # Interactive mode
            run_interactive_loop(manager)
            return_code = 0
    finally:
        print(header("\nCleaning up..."))
        manager.stop_openocd()
        print(success("Goodbye!"))

    return return_code


if __name__ == "__main__":
    sys.exit(main())
