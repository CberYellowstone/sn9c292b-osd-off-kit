#!/usr/bin/env python3
"""
Footer Checksum Fixer for Sonix SN9C292B Firmware
Implements 16-bit word-sum footer scheme to make total = 0
"""

import struct
import sys
import hashlib

def calculate_word_sum(data):
    """Calculate 16-bit word sum of firmware data"""
    if len(data) % 2 != 0:
        print("[WARNING] Firmware size is odd, padding with 0x00")
        data += b'\x00'
    
    words = struct.unpack(f"<{len(data)//2}H", data)
    total = sum(words) & 0xFFFF
    return total

def implement_boot_stub_patch(firmware):
    """Implement the boot stub OSD disable patch"""
    
    # Hook point: replace 4 NOPs at 0x0A516 with LJMP 0x0A800
    hook_address = 0x0A516
    code_cave_start = 0x0A800  # Well within firmware boundary
    
    # Verify we have NOPs at hook point
    original_hook = firmware[hook_address:hook_address+4]
    if original_hook != b'\x00\x00\x00\x00':  # 4 NOPs
        print(f"[WARNING] Expected 4 NOPs at 0x{hook_address:05X}, found: {original_hook.hex()}")
        return False
    
    # Create LJMP instruction to code cave
    ljmp_instruction = bytes([
        0x02,  # LJMP opcode
        (code_cave_start >> 8) & 0xFF,  # High byte of address
        code_cave_start & 0xFF          # Low byte of address
    ])
    
    # 8051 stub code that clears OSD quartet (0xE24-0xE27)
    stub_code = bytes([
        # Save registers
        0xC0, 0xD0,  # PUSH PSW
        0xC0, 0xE0,  # PUSH ACC
        0xC0, 0x83,  # PUSH DPH
        0xC0, 0x82,  # PUSH DPL
        0xC0, 0xF0,  # PUSH B
        
        # Clear OSD quartet (0xE24-0xE27)
        0x90, 0x0E, 0x24,  # MOV DPTR,#0x0E24
        0xE4,                # CLR A
        0xF0,                # MOVX @DPTR,A
        0xA3,                # INC DPTR
        0xF0,                # MOVX @DPTR,A
        0xA3,                # INC DPTR
        0xF0,                # MOVX @DPTR,A
        0xA3,                # INC DPTR
        0xF0,                # MOVX @DPTR,A
        
        # Restore registers
        0xD0, 0xF0,  # POP B
        0xD0, 0x82,  # POP DPL
        0xD0, 0x83,  # POP DPH
        0xD0, 0xE0,  # POP ACC
        0xD0, 0xD0,  # POP PSW
        
        # Return to original flow (LJMP to next instruction after hook)
        0x02, 0x0A, 0x1A   # LJMP 0x0A1A (next instruction after 0x0A516+4)
    ])
    
    print(f"[INFO] Stub size: {len(stub_code)} bytes")
    print(f"[INFO] Code cave start: 0x{code_cave_start:05X}")
    print(f"[INFO] Hook point: 0x{hook_address:05X}")
    
    # Verify code cave is available (should be unused space)
    cave_end = code_cave_start + len(stub_code)
    if cave_end > 0x1FFFF:  # Firmware is 0x20000 bytes, last valid address is 0x1FFFF
        print(f"[ERROR] Code cave extends beyond firmware boundary")
        print(f"[ERROR] Code cave end: 0x{cave_end:05X}, firmware boundary: 0x1FFFF")
        print("[ERROR] Need to find a different code cave location")
        return False
    
    # Check if code cave area is free (should be 0xFF or 0x00)
    cave_area = firmware[code_cave_start:cave_end]
    if any(b != 0xFF and b != 0x00 for b in cave_area):
        print(f"[WARNING] Code cave area may contain data: {cave_area.hex()}")
    
    # Apply the patch
    # 1. Insert LJMP at hook point
    firmware[hook_address:hook_address+4] = ljmp_instruction + b'\x00'  # 4 bytes total
    
    # 2. Insert stub code at code cave
    firmware[code_cave_start:cave_end] = stub_code
    
    print("[SUCCESS] Boot stub patch applied successfully")
    return True

def fix_footer(input_file, output_file):
    """Fix firmware footer checksum to make total word sum = 0"""
    
    try:
        # Read firmware
        with open(input_file, 'rb') as f:
            firmware = bytearray(f.read())
        
        print(f"[INFO] Firmware loaded: {len(firmware)} bytes")
        
        # Calculate current checksum
        current_sum = calculate_word_sum(firmware)
        print(f"[INFO] Current word sum: 0x{current_sum:04X}")
        
        # Zero the footer area (last 2 bytes)
        original_footer = firmware[-2:]
        firmware[-2:] = b'\x00\x00'
        print(f"[INFO] Original footer: {[hex(x) for x in original_footer]}")
        
        # Calculate new sum with zeroed footer
        new_sum = calculate_word_sum(firmware)
        print(f"[INFO] Sum with zeroed footer: 0x{new_sum:04X}")
        
        # Calculate required footer value to make total = 0
        required_footer = (-new_sum) & 0xFFFF
        print(f"[INFO] Required footer value: 0x{required_footer:04X}")
        
        # Apply footer fix
        firmware[-2:] = struct.pack("<H", required_footer)
        
        # Verify the fix
        final_sum = calculate_word_sum(firmware)
        print(f"[INFO] Final word sum: 0x{final_sum:04X}")
        
        if final_sum == 0:
            print("[SUCCESS] Footer checksum fixed successfully!")
        else:
            print(f"[ERROR] Footer fix failed, sum = 0x{final_sum:04X}")
            return False
        
        # Calculate file hashes
        input_hash = hashlib.sha256(open(input_file, 'rb').read()).hexdigest()
        output_hash = hashlib.sha256(firmware).hexdigest()
        
        print(f"[INFO] Input file SHA256:  {input_hash}")
        print(f"[INFO] Output file SHA256: {output_hash}")
        
        # Write patched firmware
        with open(output_file, 'wb') as f:
            f.write(firmware)
        
        print(f"[SUCCESS] Patched firmware saved to: {output_file}")
        print(f"[INFO] Footer bytes: 0x{required_footer:04X}")
        
        return True
        
    except FileNotFoundError:
        print(f"[ERROR] Input file not found: {input_file}")
        return False
    except Exception as e:
        print(f"[ERROR] Error processing firmware: {e}")
        return False

def main():
    """Main function"""
    if len(sys.argv) != 3:
        print("Usage: python fix_footer.py <input_firmware.bin> <output_firmware.bin>")
        print("Example: python fix_footer.py firmware_backup.bin firmware_patched.bin")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    print("[INFO] Sonix SN9C292B OSD Disable + Footer Checksum Fixer")
    print(f"[INFO] Input:  {input_file}")
    print(f"[INFO] Output: {output_file}")
    print("-" * 50)
    
    try:
        # Read firmware
        with open(input_file, 'rb') as f:
            firmware = bytearray(f.read())
        
        print(f"[INFO] Firmware loaded: {len(firmware)} bytes")
        
        # Apply boot stub patch first
        print("[INFO] Applying boot stub OSD disable patch...")
        if not implement_boot_stub_patch(firmware):
            print("[ERROR] Boot stub patch failed")
            sys.exit(1)
        
        # Then fix footer checksum
        print("[INFO] Fixing footer checksum...")
        
        # Calculate current checksum
        current_sum = calculate_word_sum(firmware)
        print(f"[INFO] Current word sum: 0x{current_sum:04X}")
        
        # Zero the footer area (last 2 bytes)
        original_footer = firmware[-2:]
        firmware[-2:] = b'\x00\x00'
        print(f"[INFO] Original footer: {[hex(x) for x in original_footer]}")
        
        # Calculate new sum with zeroed footer
        new_sum = calculate_word_sum(firmware)
        print(f"[INFO] Sum with zeroed footer: 0x{new_sum:04X}")
        
        # Calculate required footer value to make total = 0
        required_footer = (-new_sum) & 0xFFFF
        print(f"[INFO] Required footer value: 0x{required_footer:04X}")
        
        # Apply footer fix
        firmware[-2:] = struct.pack("<H", required_footer)
        
        # Verify the fix
        final_sum = calculate_word_sum(firmware)
        print(f"[INFO] Final word sum: 0x{final_sum:04X}")
        
        if final_sum == 0:
            print("[SUCCESS] Footer checksum fixed successfully!")
        else:
            print(f"[ERROR] Footer fix failed, sum = 0x{final_sum:04X}")
            sys.exit(1)
        
        # Write patched firmware
        with open(output_file, 'wb') as f:
            f.write(firmware)
        
        print(f"[SUCCESS] Patched firmware saved to: {output_file}")
        print(f"[INFO] Footer bytes: 0x{required_footer:04X}")
        
        success = True
        
        if success:
            print("-" * 50)
            print("[SUCCESS] OSD disable patch and footer checksum fix completed")
            print("[INFO] Ready for firmware flashing")
            sys.exit(0)
        else:
            print("-" * 50)
            print("[ERROR] Footer checksum fix failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"[ERROR] Error processing firmware: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
