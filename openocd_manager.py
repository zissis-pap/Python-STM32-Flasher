"""OpenOCD Manager - Handles OpenOCD process and communication"""

import subprocess
import socket
import time
import os
from colors import error, success, info, warning


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
            print(info("OpenOCD is already running"))
            return True

        cmd = ["openocd"]
        if self.interface_cfg:
            cmd.extend(["-f", self.interface_cfg])
        if self.target_cfg:
            cmd.extend(["-f", self.target_cfg])

        try:
            print(info(f"Starting OpenOCD with command: {' '.join(cmd)}"))
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            time.sleep(2)  # Give OpenOCD time to start

            if self.process.poll() is not None:
                _, stderr = self.process.communicate()
                print(error(f"OpenOCD failed to start: {stderr}"))
                return False

            print(success("OpenOCD started successfully"))
            return True
        except FileNotFoundError:
            print(error("Error: openocd command not found. Please install OpenOCD."))
            return False
        except Exception as e:
            print(error(f"Error starting OpenOCD: {e}"))
            return False

    def connect_telnet(self):
        """Connect to OpenOCD via telnet"""
        if self.connected:
            print(info("Already connected to OpenOCD"))
            return True

        try:
            print(info(f"Connecting to OpenOCD on localhost:{self.port}..."))
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect(("localhost", self.port))

            # Read initial prompt
            self._read_until(b">", timeout=2)
            self.connected = True
            print(success("Connected to OpenOCD successfully"))
            return True
        except Exception as e:
            print(error(f"Error connecting to OpenOCD: {e}"))
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

    def _send_command_raw(self, command):
        """Send command to OpenOCD without retry logic"""
        if not self.connected:
            print(error("Not connected to OpenOCD"))
            return None

        try:
            self.socket.sendall(f"{command}\n".encode('ascii'))
            response = self._read_until(b">", timeout=5).decode('ascii')
            # Remove the prompt from response
            response = response.rsplit('>', 1)[0].strip()
            return response
        except Exception as e:
            print(error(f"Error sending command: {e}"))
            return None

    def _check_if_halted(self):
        """Check if MCU is halted"""
        # Try to read a register - this will indicate if target is halted
        response = self._send_command_raw("targets")
        if response:
            response_lower = response.lower()
            # Check for halted state indicators
            if "halted" in response_lower:
                return True
            # If it says "running", it's definitely not halted
            if "running" in response_lower:
                return False

        # If unclear, assume not halted to be safe
        return False

    def _ensure_halted(self):
        """Ensure MCU is halted, halt it if not"""
        if not self._check_if_halted():
            print(warning("MCU not halted, attempting to halt..."))
            self._send_command_raw("halt")
            time.sleep(0.5)

    def _is_command_failed(self, response):
        """Check if OpenOCD command failed based on response"""
        if response is None:
            return True

        response_lower = response.lower()

        # Common OpenOCD failure indicators
        failure_patterns = [
            "failed",
            "error",
            "target not halted",
            "cannot",
            "invalid"
        ]

        for pattern in failure_patterns:
            if pattern in response_lower:
                return True

        return False

    def send_command(self, command, max_retries=3, check_halt=True):
        """Send command to OpenOCD with retry logic

        Args:
            command: The OpenOCD command to send
            max_retries: Maximum number of retry attempts (default: 3)
            check_halt: Whether to check and ensure MCU is halted before retry (default: True)

        Raises:
            RuntimeError: If command fails after all retry attempts
        """
        last_response = None
        for attempt in range(max_retries):
            response = self._send_command_raw(command)
            last_response = response

            # Check if command succeeded
            if not self._is_command_failed(response):
                return response

            # Command failed
            if attempt < max_retries - 1:  # Don't retry on last attempt
                print(warning(f"Command failed, retrying ({attempt + 2}/{max_retries})..."))
                if response:
                    print(warning(f"OpenOCD response: {response}"))

                # Check if MCU is halted before retrying (except for halt/reset commands)
                if check_halt and command not in ["halt", "reset halt", "reset run"]:
                    self._ensure_halted()

                time.sleep(0.5)  # Brief delay before retry
            else:
                error_msg = f"Command '{command}' failed after {max_retries} attempts"
                if last_response:
                    error_msg += f"\nLast OpenOCD response: {last_response}"
                print(error(error_msg))
                raise RuntimeError(error_msg)

        return response

    def halt(self):
        """Halt the MCU"""
        print(info("Halting MCU..."))
        response = self.send_command("halt", check_halt=False)
        if response:
            print(success(response))
        return response

    def reset_halt(self):
        """Reset and halt the MCU"""
        print(info("Resetting and halting MCU..."))
        response = self.send_command("reset halt", check_halt=False)
        if response:
            print(success(response))
        return response

    def reset_run(self):
        """Reset and run the MCU"""
        print(info("Resetting and running MCU..."))
        response = self.send_command("reset run", check_halt=False)
        if response:
            print(success(response))
        return response

    def erase_flash(self):
        """Erase flash memory"""
        print(warning("Erasing flash memory..."))
        # Ensure MCU is halted before erasing
        self._ensure_halted()
        response = self.send_command("flash erase_sector 0 0 last")
        if response:
            print(success(response))
        return response

    def flash_firmware(self, firmware_path, address=0x08000000):
        """Flash firmware to MCU

        Args:
            firmware_path: Path to firmware file
            address: Optional memory address to program at (hex string or int)

        Raises:
            FileNotFoundError: If firmware file does not exist
        """
        if not os.path.exists(firmware_path):
            error_msg = f"Firmware file '{firmware_path}' not found"
            print(error(f"Error: {error_msg}"))
            raise FileNotFoundError(error_msg)

        # Build flash command
        if address is not None:
            # Convert address to hex string if it's an integer
            if isinstance(address, int):
                addr_str = f"0x{address:08x}"
            else:
                addr_str = address
            print(info(f"Flashing firmware: {firmware_path} at address {addr_str}"))
            flash_cmd = f"program {firmware_path} {addr_str}"
        else:
            print(info(f"Flashing firmware: {firmware_path}"))
            flash_cmd = f"program {firmware_path} 0x08000000"

        # Ensure MCU is halted before flashing
        self._ensure_halted()
        response = self.send_command(flash_cmd)
        if response:
            print(success(response))
        return response

    def verify_firmware(self, firmware_path, address=0x08000000):
        """Verify firmware

        Args:
            firmware_path: Path to firmware file
            address: Optional memory address offset for verification (hex string or int)

        Raises:
            FileNotFoundError: If firmware file does not exist
        """
        if not os.path.exists(firmware_path):
            error_msg = f"Firmware file '{firmware_path}' not found"
            print(error(f"Error: {error_msg}"))
            raise FileNotFoundError(error_msg)

        # Build verify command
        if address is not None:
            # Convert address to hex string if it's an integer
            if isinstance(address, int):
                addr_str = f"0x{address:08x}"
            else:
                addr_str = address
            print(info(f"Verifying firmware: {firmware_path} at address {addr_str}"))
            verify_cmd = f"verify_image {firmware_path} {addr_str}"
        else:
            print(info(f"Verifying firmware: {firmware_path}"))
            verify_cmd = f"verify_image {firmware_path}"

        # Ensure MCU is halted before verifying
        self._ensure_halted()
        response = self.send_command(verify_cmd)
        if response:
            print(success(response))
        return response

    def read_memory(self, address, count=1):
        """Read memory at address"""
        print(info(f"Reading memory at 0x{address:08x} (count: {count})..."))
        response = self.send_command(f"mdw 0x{address:08x} {count}")
        if response:
            print(info(response))
        return response

    def write_memory(self, address, value):
        """Write value to memory address"""
        print(info(f"Writing 0x{value:08x} to address 0x{address:08x}..."))
        # Ensure MCU is halted before writing to memory
        self._ensure_halted()
        response = self.send_command(f"mww 0x{address:08x} 0x{value:08x}")
        if response:
            print(success(response))
        return response

    def get_target_info(self):
        """Get target information"""
        print(info("Getting target information..."))
        response = self.send_command("targets")
        if response:
            print(info(response))
        return response

    def custom_command(self, command):
        """Send custom OpenOCD command"""
        print(info(f"Sending command: {command}"))
        response = self.send_command(command)
        if response:
            print(info(response))
        return response

    def disconnect(self):
        """Disconnect socket connection"""
        if self.socket:
            try:
                self.socket.close()
                print(success("Disconnected from OpenOCD"))
            except:
                pass
            self.connected = False
            self.socket = None
            self.buffer = b""

    def stop_openocd(self):
        """Stop OpenOCD process"""
        self.disconnect()

        if self.process and self.process.poll() is None:
            print(info("Stopping OpenOCD..."))
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print(success("OpenOCD stopped"))
        self.process = None
