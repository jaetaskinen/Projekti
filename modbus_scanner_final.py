# -*- coding: utf-8 -*-
"""
Created on Sat Apr 25 18:23:19 2026

@author: jaeta
"""

import pymodbus
import argparse
import time
import re # Import the regular expression module
from pymodbus.client import ModbusSerialClient

def parse_baudrates_input(s: str) -> list[int]:
    """Parse comma-separated baudrates from user input."""
    valid_baudrates = [9600, 19200, 38400]
    try:
        parsed = [int(x.strip()) for x in s.split(",") if x.strip()]
        if not parsed:
            return valid_baudrates # Default if empty
        for baud in parsed:
            if baud not in valid_baudrates:
                raise ValueError(f"Invalid baudrate '{baud}'. Must be one of {valid_baudrates}")
        return parsed
    except ValueError:
        raise ValueError("Invalid baudrate format. Please enter comma-separated numbers (e.g., 9600, 19200, 38400).")

def parse_parities_input(s: str) -> list[str]:
    """Parse comma-separated parities from user input."""
    valid_parities = ["N", "E", "O"]
    parsed = [x.strip().upper() for x in s.split(",") if x.strip()]
    if not parsed:
        return valid_parities # Default if empty
    for p in parsed:
        if p not in valid_parities:
            raise ValueError(f"Invalid parity '{p}'. Must be one of {valid_parities}")
    return parsed

def parse_stopbits_input(s: str) -> list[int]:
    """Parse comma-separated stopbits from user input."""
    valid_stopbits = [1, 2]
    try:
        parsed = [int(x.strip()) for x in s.split(",") if x.strip()]
        if not parsed:
            return valid_stopbits # Default if empty
        for sb in parsed:
            if sb not in valid_stopbits:
                raise ValueError(f"Invalid stopbit '{sb}'. Must be one of {valid_stopbits}")
        return parsed
    except ValueError:
        raise ValueError("Invalid stopbit format. Please enter comma-separated numbers (1 or 2).")

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Modbus RTU Auto-Scanner: Brute-force unknown slave ID and baudrate",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=0.1,
        help="Timeout in seconds per request (lower = faster scan, but risk of missing slow devices)",
    )
    parser.add_argument(
        "--test-count",
        type=int,
        default=1,
        help="Number of registers to read",
    )
    parser.add_argument(
        "--stop-on-first",
        action="store_true",
        help="Stop after finding the first working combination",
    )

    args = parser.parse_args()

    # Get interactive input for serial port
    while True:
        port = input("Enter serial port (e.g., COM3 on Windows, /dev/ttyUSB0 on Linux): ")
        if not port.strip():
            print("Error: Serial port cannot be empty.")
        elif re.match(r"^COM([1-9]|[1-9][0-9])$", port.upper()) or port.startswith('/dev/ttyUSB'):
            break
        else:
            print("Error: Invalid serial port format. For Windows, use COM1-99 (e.g., COM3). For Linux, use /dev/ttyUSBx (e.g., /dev/ttyUSB0).")

    # Get interactive input for baudrates, parities, and stopbits
    while True:
        baudrate_input = input("Enter baudrates to test (e.g., 9600, 19200, 38400, or leave empty for default): ")
        try:
            baudrates = parse_baudrates_input(baudrate_input or "9600, 19200, 38400")
            break
        except ValueError as e:
            print(f"Error: {e}")

    while True:
        parity_input = input("Enter parities to test (N, E, O; e.g., N,E,O, or leave empty for default): ")
        try:
            parities = parse_parities_input(parity_input or "N,E,O")
            break
        except ValueError as e:
            print(f"Error: {e}")

    while True:
        stopbits_input = input("Enter stopbits to test (1, 2; e.g., 1,2, or leave empty for default): ")
        try:
            stopbits_options = parse_stopbits_input(stopbits_input or "1,2")
            break
        except ValueError as e:
            print(f"Error: {e}")

    # Get interactive input for min and max slave IDs
    while True:
        min_slave_input = input("Enter minimum slave ID to test (default: 1): ")
        try:
            min_slave = int(min_slave_input) if min_slave_input.strip() else 1
            if not (1 <= min_slave <= 247):
                raise ValueError("Slave ID must be between 1 and 247.")
            break
        except ValueError as e:
            print(f"Error: {e}")

    while True:
        max_slave_input = input("Enter maximum slave ID to test (default: 247): ")
        try:
            max_slave = int(max_slave_input) if max_slave_input.strip() else 247
            if not (1 <= max_slave <= 247):
                raise ValueError("Slave ID must be between 1 and 247.")
            if max_slave < min_slave:
                raise ValueError("Maximum slave ID cannot be less than minimum slave ID.")
            break
        except ValueError as e:
            print(f"Error: {e}")

    # Get interactive input for test address
    while True:
        test_address_input = input("Enter holding register address to test read (default: 793): ")
        try:
            test_address = int(test_address_input) if test_address_input.strip() else 793
            if test_address < 0:
                raise ValueError("Register address must be non-negative.")
            break
        except ValueError as e:
            print(f"Error: {e}")


    print(f"Starting Modbus RTU scanner on port {port}")
    print(f"Testing baudrates: {baudrates}")
    print(f"Testing parities: {parities}")
    print(f"Testing stopbits: {stopbits_options}")
    print(f"Slave IDs: {min_slave} to {max_slave}")
    print(f"Test: read holding register {test_address} (count={args.test_count})")
    print(f"Timeout per request: {args.timeout}s\n")

    found = []
    stop_scan = False # New flag to control overall scanning

    for baud in baudrates:
        if stop_scan:
            break # Break outer loop if flag is set

        print(f"→ Testing baudrate {baud}...")
        for parity in parities:
            if stop_scan:
                break

            print(f"  → Testing parity {parity}...")
            for stopbits_val in stopbits_options:
                if stop_scan:
                    break

                print(f"    → Testing stopbits {stopbits_val}...")
                for slave in range(min_slave, max_slave + 1):
                    print(f"      → Trying slave ID {slave}...", end=" ")

                    client = ModbusSerialClient(
                        port=port,
                        baudrate=baud,
                        bytesize=8,
                        parity=parity,
                        stopbits=stopbits_val,
                        timeout=args.timeout,
                        retries=0,
                        # framer defaults to RTU in current pymodbus
                    )

                    if not client.connect():
                        print("Failed to open serial port")
                        client.close()
                        continue

                    try:
                        # Attempt to read - any response (success or exception response) means communication works
                        response = client.read_holding_registers(
                            address=test_address,
                            count=args.test_count,
                            device_id=slave,
                        )

                        # If we reach here, the device responded (correct baud + slave ID)
                        print("SUCCESS!")
                        if not response.isError():
                            print(f"        → Valid response: {response.registers}")
                        else:
                            print(f"        → Device responded with Modbus exception (still confirms connection)")

                        found.append((baud, parity, stopbits_val, slave, response))
                        stop_scan = True # Set flag to stop scanning
                        client.close()
                        if stop_scan:
                            break # Break slave loop

                    except Exception as e:
                        # Timeout, CRC error, no response, wrong baud, wrong slave, etc.
                        print(f"no response ({type(e).__name__})")
                    finally:
                        client.close()

                    # Only sleep if we haven't found a device and aren't stopping
                    if not stop_scan:
                        time.sleep(0.1)

                # Check again after slave loop completes (or breaks)
                if stop_scan:
                    break # Break stopbits loop
            # Check again after stopbits loop completes (or breaks)
            if stop_scan:
                break # Break parity loop
        # Check again after parity loop completes (or breaks)
        if stop_scan:
            break # Break baudrate loop

    print("\n" + "=" * 60)
    if found:
        print("✅ FOUND WORKING PARAMETER(S):")
        for baud, parity, stopbits_val, slave, resp in found:
            print(f"   • Baudrate = {baud}, Parity = {parity}, Stopbits = {stopbits_val}, Slave ID = {slave}")
            if not resp.isError():
                print(f"       Sample data: {resp.registers}")
    else:
        print("❌ No device found with the tested parameters.")

    print("=" * 60)

    # Keep console window open when run as an EXE
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()
