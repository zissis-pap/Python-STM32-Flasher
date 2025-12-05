#!/usr/bin/env python3

import subprocess
import socket
import time
import sys
import os

VERSION = "0.002"


class OpenOCDManager:
    def __init__(self, interface_cfg=None, target_cfg=None, port=4444):
        self.interface_cfg = interface_cfg
        self.target_cfg = target_cfg
        self.port = port
        self.process = None
        self.socket = None
        self.connected = False
        self.buffer = b""

    def start_openocd(self):
        """Start OpenOCD process"""
        if self.process and self.process.poll() is None:
            print("OpenOCD is already running")
            return True

        cmd = ["openocd"]
        if self.interface_cfg:
            cmd.extend(["-f", self.interface_cfg])
        if self.target_cfg:
            cmd.extend(["-f", self.target_cfg])

        try:
            print(f"Starting OpenOCD with command: {' '.join(cmd)}")
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            time.sleep(2)  # Give OpenOCD time to start

            if self.process.poll() is not None:
                _, stderr = self.process.communicate()
                print(f"OpenOCD failed to start: {stderr}")
                return False

            print("OpenOCD started successfully")
            return True
        except FileNotFoundError:
            print("Error: openocd command not found. Please install OpenOCD.")
            return False
        except Exception as e:
            print(f"Error starting OpenOCD: {e}")
            return False

    def connect_telnet(self):
        """Connect to OpenOCD via telnet"""
        if self.connected:
            print("Already connected to OpenOCD")
            return True

        try:
            print(f"Connecting to OpenOCD on localhost:{self.port}...")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect(("localhost", self.port))

            # Read initial prompt
            self._read_until(b">", timeout=2)
            self.connected = True
            print("Connected to OpenOCD successfully")
            return True
        except Exception as e:
            print(f"Error connecting to OpenOCD: {e}")
            self.connected = False
            if self.socket:
                self.socket.close()
                self.socket = None
            return False

    def _read_until(self, delimiter, timeout=5):
        """Read from socket until delimiter is found"""
        self.socket.settimeout(timeout)
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break
                self.buffer += data
                if delimiter in self.buffer:
                    result, self.buffer = self.buffer.split(delimiter, 1)
                    return result + delimiter
            except socket.timeout:
                break
            except Exception:
                break

        result = self.buffer
        self.buffer = b""
        return result

    def send_command(self, command):
        """Send command to OpenOCD and return response"""
        if not self.connected:
            print("Not connected to OpenOCD")
            return None

        try:
            self.socket.sendall(f"{command}\n".encode('ascii'))
            response = self._read_until(b">", timeout=5).decode('ascii')
            # Remove the prompt from response
            response = response.rsplit('>', 1)[0].strip()
            return response
        except Exception as e:
            print(f"Error sending command: {e}")
            return None

    def halt(self):
        """Halt the MCU"""
        print("Halting MCU...")
        response = self.send_command("halt")
        if response:
            print(response)
        return response

    def reset_halt(self):
        """Reset and halt the MCU"""
        print("Resetting and halting MCU...")
        response = self.send_command("reset halt")
        if response:
            print(response)
        return response

    def reset_run(self):
        """Reset and run the MCU"""
        print("Resetting and running MCU...")
        response = self.send_command("reset run")
        if response:
            print(response)
        return response

    def erase_flash(self):
        """Erase flash memory"""
        print("Erasing flash memory...")
        response = self.send_command("flash erase_sector 0 0 last")
        if response:
            print(response)
        return response

    def flash_firmware(self, firmware_path):
        """Flash firmware to MCU"""
        if not os.path.exists(firmware_path):
            print(f"Error: Firmware file '{firmware_path}' not found")
            return None

        print(f"Flashing firmware: {firmware_path}")
        self.halt()
        response = self.send_command(f"program {firmware_path} verify reset")
        if response:
            print(response)
        return response

    def verify_firmware(self, firmware_path):
        """Verify firmware"""
        if not os.path.exists(firmware_path):
            print(f"Error: Firmware file '{firmware_path}' not found")
            return None

        print(f"Verifying firmware: {firmware_path}")
        response = self.send_command(f"verify_image {firmware_path}")
        if response:
            print(response)
        return response

    def read_memory(self, address, count=1):
        """Read memory at address"""
        print(f"Reading memory at 0x{address:08x} (count: {count})...")
        response = self.send_command(f"mdw 0x{address:08x} {count}")
        if response:
            print(response)
        return response

    def write_memory(self, address, value):
        """Write value to memory address"""
        print(f"Writing 0x{value:08x} to address 0x{address:08x}...")
        response = self.send_command(f"mww 0x{address:08x} 0x{value:08x}")
        if response:
            print(response)
        return response

    def get_target_info(self):
        """Get target information"""
        print("Getting target information...")
        response = self.send_command("targets")
        if response:
            print(response)
        return response

    def custom_command(self, command):
        """Send custom OpenOCD command"""
        print(f"Sending command: {command}")
        response = self.send_command(command)
        if response:
            print(response)
        return response

    def disconnect(self):
        """Disconnect socket connection"""
        if self.socket:
            try:
                self.socket.close()
                print("Disconnected from OpenOCD")
            except:
                pass
            self.connected = False
            self.socket = None
            self.buffer = b""

    def stop_openocd(self):
        """Stop OpenOCD process"""
        self.disconnect()

        if self.process and self.process.poll() is None:
            print("Stopping OpenOCD...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print("OpenOCD stopped")
        self.process = None


def print_menu():
    """Print interactive menu"""
    print("\n" + "="*50)
    print("OpenOCD Manager - Interactive Menu")
    print("="*50)
    print("1.  Halt MCU")
    print("2.  Reset and Halt MCU")
    print("3.  Reset and Run MCU")
    print("4.  Erase Flash")
    print("5.  Flash Firmware")
    print("6.  Verify Firmware")
    print("7.  Read Memory")
    print("8.  Write Memory")
    print("9.  Get Target Info")
    print("10. Send Custom Command")
    print("11. Reconnect to OpenOCD")
    print("12. Exit")
    print("="*50)


def main():
    print(f"OpenOCD Manager v{VERSION}")
    print("="*50)

    # Configuration
    # config_file = input("Enter OpenOCD config file path (or press Enter to skip): ").strip()
    # if not config_file:
    #     config_file = None
    # port = input("Enter OpenOCD telnet port (default: 4444): ").strip()
    # port = int(port) if port else 4444

    # Hardcoded interface configuration
    interface_cfg = "interface/stlink.cfg"
    port = 4444

    # Ask for target configuration
    print("\nSelect STM32 target:")
    print("F Series:")
    print("  1.  STM32F0 (target/stm32f0x.cfg)")
    print("  2.  STM32F1 (target/stm32f1x.cfg)")
    print("  3.  STM32F2 (target/stm32f2x.cfg)")
    print("  4.  STM32F3 (target/stm32f3x.cfg)")
    print("  5.  STM32F4 (target/stm32f4x.cfg)")
    print("  6.  STM32F7 (target/stm32f7x.cfg)")
    print("G Series:")
    print("  7.  STM32G0 (target/stm32g0x.cfg)")
    print("  8.  STM32G4 (target/stm32g4x.cfg)")
    print("H Series:")
    print("  9.  STM32H7 (target/stm32h7x.cfg)")
    print("L Series:")
    print("  10. STM32L0 (target/stm32l0.cfg)")
    print("  11. STM32L1 (target/stm32l1.cfg)")
    print("  12. STM32L4 (target/stm32l4x.cfg)")
    print("  13. STM32L5 (target/stm32l5x.cfg)")
    print("Wireless Series:")
    print("  14. STM32WB (target/stm32wbx.cfg)")
    print("  15. STM32WL (target/stm32wlx.cfg)")

    target_choice = input("\nEnter your choice (1-15): ").strip()

    targets = {
        "1": "target/stm32f0x.cfg",
        "2": "target/stm32f1x.cfg",
        "3": "target/stm32f2x.cfg",
        "4": "target/stm32f3x.cfg",
        "5": "target/stm32f4x.cfg",
        "6": "target/stm32f7x.cfg",
        "7": "target/stm32g0x.cfg",
        "8": "target/stm32g4x.cfg",
        "9": "target/stm32h7x.cfg",
        "10": "target/stm32l0.cfg",
        "11": "target/stm32l1.cfg",
        "12": "target/stm32l4x.cfg",
        "13": "target/stm32l5x.cfg",
        "14": "target/stm32wbx.cfg",
        "15": "target/stm32wlx.cfg"
    }

    if target_choice in targets:
        target_cfg = targets[target_choice]
        print(f"Selected: {target_cfg}")
    else:
        print("Error: Invalid target selection")
        return 1

    # Initialize manager
    manager = OpenOCDManager(interface_cfg=interface_cfg, target_cfg=target_cfg, port=port)

    # Start OpenOCD
    if not manager.start_openocd():
        print("Failed to start OpenOCD. Exiting...")
        return 1

    # Connect via telnet
    if not manager.connect_telnet():
        print("Failed to connect to OpenOCD. Stopping...")
        manager.stop_openocd()
        return 1

    # Interactive loop
    try:
        while True:
            print_menu()
            choice = input("\nEnter your choice: ").strip()

            if choice == "1":
                manager.halt()

            elif choice == "2":
                manager.reset_halt()

            elif choice == "3":
                manager.reset_run()

            elif choice == "4":
                confirm = input("Are you sure you want to erase flash? (yes/no): ")
                if confirm.lower() == "yes":
                    manager.erase_flash()

            elif choice == "5":
                firmware_path = input("Enter firmware file path: ").strip()
                manager.flash_firmware(firmware_path)

            elif choice == "6":
                firmware_path = input("Enter firmware file path: ").strip()
                manager.verify_firmware(firmware_path)

            elif choice == "7":
                try:
                    addr_str = input("Enter memory address (hex, e.g., 0x08000000): ").strip()
                    address = int(addr_str, 16) if addr_str.startswith("0x") else int(addr_str, 16)
                    count_str = input("Enter number of words to read (default: 1): ").strip()
                    count = int(count_str) if count_str else 1
                    manager.read_memory(address, count)
                except ValueError:
                    print("Invalid address or count")

            elif choice == "8":
                try:
                    addr_str = input("Enter memory address (hex, e.g., 0x08000000): ").strip()
                    address = int(addr_str, 16) if addr_str.startswith("0x") else int(addr_str, 16)
                    val_str = input("Enter value to write (hex, e.g., 0x12345678): ").strip()
                    value = int(val_str, 16) if val_str.startswith("0x") else int(val_str, 16)
                    manager.write_memory(address, value)
                except ValueError:
                    print("Invalid address or value")

            elif choice == "9":
                manager.get_target_info()

            elif choice == "10":
                command = input("Enter OpenOCD command: ").strip()
                if command:
                    manager.custom_command(command)

            elif choice == "11":
                manager.disconnect()
                time.sleep(1)
                manager.connect_telnet()

            elif choice == "12":
                print("Exiting...")
                break

            else:
                print("Invalid choice. Please try again.")

            input("\nPress Enter to continue...")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")

    finally:
        print("\nCleaning up...")
        manager.stop_openocd()
        print("Goodbye!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
