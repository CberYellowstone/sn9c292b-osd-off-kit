#!/usr/bin/env python
# IDAPython script to patch SN9C292B firmware to disable OSD
# Created for Windsurf AI Assistant

import idaapi
import idc
import os
import struct

def calculate_checksum(firmware_data):
    """Calculate the 16-bit checksum for the firmware.
    
    The checksum is a 16-bit sum of all words in the firmware (0x0000-0x1FFD),
    with the result stored as a two's complement value at 0x1FFE-0x1FFF.
    
    Args:
        firmware_data: Bytes object containing the firmware data
        
    Returns:
        int: The calculated checksum value
    """
    # Initialize checksum to 0
    checksum = 0
    
    # Process all words from 0x0000 to 0x1FFD (inclusive)
    for i in range(0, 0x1FFE, 2):
        # Get the current word (little-endian)
        if i + 1 < len(firmware_data):
            word = (firmware_data[i+1] << 8) | firmware_data[i]
        else:
            # Handle case where firmware_data length is odd
            word = 0
        
        # Add to checksum (16-bit addition with wrap-around)
        checksum = (checksum + word) & 0xFFFF
    
    # Calculate two's complement
    checksum = ((~checksum) + 1) & 0xFFFF
    
    return checksum

def update_checksum(firmware_data):
    """Update the checksum in the firmware data.
    
    Args:
        firmware_data: Mutable bytearray containing the firmware data
        
    Returns:
        tuple: (old_checksum, new_checksum) if successful, (None, None) otherwise
    """
    if len(firmware_data) < 0x2000:
        print("Error: Firmware is too small (must be at least 8KB)")
        return None, None
    
    # Extract the old checksum (little-endian)
    old_checksum = (firmware_data[0x1FFF] << 8) | firmware_data[0x1FFE]
    
    # Calculate the new checksum
    new_checksum = calculate_checksum(firmware_data)
    
    # Update the checksum in the firmware data (little-endian)
    firmware_data[0x1FFE] = new_checksum & 0xFF
    firmware_data[0x1FFF] = (new_checksum >> 8) & 0xFF
    
    return old_checksum, new_checksum

def patch_osd_off():
    """Patch OSD enable sequences in SN9C292B firmware and update checksum."""
    
    # Dictionary of OSD enable sequences to patch
    # Format: {address: (original_bytes, patched_bytes, description)}
    patches = {
        0x04D0: (b"\x90\x0B\x77\x74\x01", b"\x90\x0B\x77\x74\x00", "OSD enable sequence 1 (0x0B77)"),
        0x0AC4: (b"\x90\x0B\x76\x74\x01", b"\x90\x0B\x76\x74\x00", "OSD enable sequence 2 (0x0B76)"),
        0x0AFE: (b"\x90\x0B\x77\x74\x01", b"\x90\x0B\x77\x74\x00", "OSD enable sequence 3 (0x0B77)"),
        0x4522: (b"\x90\x0B\x75\x74\x01", b"\x90\x0B\x75\x74\x00", "OSD enable sequence 4 (0x0B75)")
    }
    
    # Get the entire firmware image
    firmware_size = 0x20000  # 128KB
    firmware_data = bytearray(idaapi.get_bytes(0, firmware_size))
    
    if len(firmware_data) != firmware_size:
        print(f"Error: Could not read firmware (expected {firmware_size} bytes, got {len(firmware_data)})")
        return
    
    print("Patching OSD enable sequences...")
    print("-" * 50)
    
    # Apply patches
    patched = 0
    for addr, (orig_bytes, patched_bytes, desc) in patches.items():
        # Check if the original bytes match
        current_bytes = firmware_data[addr:addr+len(orig_bytes)]
        if bytes(current_bytes) == orig_bytes:
            # Apply the patch
            firmware_data[addr:addr+len(patched_bytes)] = patched_bytes
            print(f"Patched {desc} at 0x{addr:04X}")
            patched += 1
        else:
            print(f"Warning: Unexpected bytes at 0x{addr:04X}, skipping patch")
    
    print("\nUpdating checksum...")
    print("-" * 50)
    
    # Update the checksum
    old_checksum, new_checksum = update_checksum(firmware_data)
    
    if old_checksum is not None and new_checksum is not None:
        print(f"Checksum updated: 0x{old_checksum:04X} -> 0x{new_checksum:04X}")
    else:
        print("Error: Failed to update checksum")
        return
    
    # Save the patched firmware
    output_path = os.path.join(os.path.dirname(idaapi.get_input_file_path()), "fw_osd_off.bin")
    
    try:
        with open(output_path, 'wb') as f:
            f.write(firmware_data)
        
        print("\nPatch complete!")
        print("-" * 50)
        print(f"Successfully patched {patched} OSD enable sequences")
        print(f"Patched firmware saved to: {output_path}")
        print("\nVerification steps:")
        print("1. Flash the patched firmware to the device")
        print("2. Power cycle the device")
        print("3. Verify that the OSD does not appear")
        print("4. Test all device functions")
        
    except Exception as e:
        print(f"Error saving patched firmware: {e}")

if __name__ == '__main__':
    patch_osd_off()
