#!/usr/bin/env python3
"""
Footer Checksum Verification Tool for Sonix SN9C292B Firmware
Phase F: Verifies that all patched firmware files have correct checksums
"""

import struct
import hashlib
import json
import os

def calculate_word_sum(data):
    """Calculate 16-bit word sum of firmware data"""
    if len(data) % 2 != 0:
        print("[WARNING] Firmware size is odd, padding with 0x00")
        data += b'\x00'
    
    words = struct.unpack(f"<{len(data)//2}H", data)
    total = sum(words) & 0xFFFF
    return total

def verify_firmware_checksum(firmware_path):
    """Verify a single firmware file's checksum"""
    
    try:
        with open(firmware_path, 'rb') as f:
            firmware = f.read()
        
        print(f"[INFO] Verifying: {os.path.basename(firmware_path)}")
        print(f"[INFO] File size: {len(firmware)} bytes")
        
        # Calculate current word sum
        current_sum = calculate_word_sum(firmware)
        
        # Check footer bytes
        footer_bytes = firmware[-2:]
        footer_value = struct.unpack("<H", footer_bytes)[0]
        
        print(f"[INFO] Current word sum: 0x{current_sum:04X}")
        print(f"[INFO] Footer bytes: 0x{footer_value:04X}")
        
        # Verify checksum
        if current_sum == 0:
            print(f"[SUCCESS] ✅ Checksum is correct (0x0000)")
            status = "VALID"
        else:
            print(f"[ERROR] ❌ Checksum is incorrect (0x{current_sum:04X})")
            status = "INVALID"
        
        # Calculate file hash
        file_hash = hashlib.sha256(firmware).hexdigest()
        
        return {
            "file": os.path.basename(firmware_path),
            "size_bytes": len(firmware),
            "word_sum": f"0x{current_sum:04X}",
            "footer_value": f"0x{footer_value:04X}",
            "checksum_status": status,
            "sha256": file_hash
        }
        
    except Exception as e:
        print(f"[ERROR] Error verifying {firmware_path}: {e}")
        return None

def verify_all_patches():
    """Verify all generated patch files"""
    
    print("[INFO] ========================================")
    print("[INFO] PHASE F - FOOTER CHECKSUM VERIFICATION")
    print("[INFO] ========================================")
    
    # List of files to verify
    files_to_verify = [
        "../../IDA Live fw files/firmware_backup.bin",  # Original
        "patches/fw_osd_off_plan_d.bin",              # Plan D
        "patches/fw_osd_off_plan_s.bin"               # Plan S
    ]
    
    verification_results = []
    
    for file_path in files_to_verify:
        if os.path.exists(file_path):
            result = verify_firmware_checksum(file_path)
            if result:
                verification_results.append(result)
            print()  # Empty line for readability
        else:
            print(f"[WARNING] File not found: {file_path}")
    
    # Create verification report
    verification_report = {
        "phase": "F",
        "step": "checksum_verification",
        "timestamp": "2025-08-18T17:08:47",
        "status": "completed",
        "files_verified": len(verification_results),
        "verification_results": verification_results
    }
    
    # Save verification report
    with open("phase_f_checksum_verification.json", "w") as f:
        json.dump(verification_report, f, indent=2)
    
    print(f"[SUCCESS] Checksum verification report saved to phase_f_checksum_verification.json")
    
    # Summary
    print("\n[INFO] ========================================")
    print("[INFO] CHECKSUM VERIFICATION SUMMARY")
    print("[INFO] ========================================")
    
    valid_count = sum(1 for r in verification_results if r["checksum_status"] == "VALID")
    total_count = len(verification_results)
    
    print(f"[INFO] Files verified: {total_count}")
    print(f"[INFO] Valid checksums: {valid_count}")
    print(f"[INFO] Invalid checksums: {total_count - valid_count}")
    
    if valid_count == total_count:
        print(f"[SUCCESS] ✅ All firmware files have valid checksums!")
        print(f"[INFO] Ready for firmware flashing")
    else:
        print(f"[ERROR] ❌ Some firmware files have invalid checksums")
        print(f"[INFO] Review verification results before flashing")
    
    return verification_results

def demonstrate_checksum_fixing():
    """Demonstrate the checksum fixing process"""
    
    print("\n[INFO] ========================================")
    print("[INFO] CHECKSUM FIXING DEMONSTRATION")
    print("[INFO] ========================================")
    
    # Read original firmware
    original_path = "../../IDA Live fw files/firmware_backup.bin"
    
    try:
        with open(original_path, 'rb') as f:
            original_firmware = bytearray(f.read())
        
        print(f"[INFO] Original firmware: {len(original_firmware)} bytes")
        
        # Calculate original checksum
        original_sum = calculate_word_sum(original_firmware)
        original_footer = original_firmware[-2:]
        
        print(f"[INFO] Original word sum: 0x{original_sum:04X}")
        print(f"[INFO] Original footer: 0x{original_footer[0]:02X} 0x{original_footer[1]:02X}")
        
        # Demonstrate fixing process
        print(f"\n[INFO] Checksum fixing process:")
        print(f"1. Zero footer bytes: 0x00 0x00")
        
        # Zero footer
        original_firmware[-2:] = b'\x00\x00'
        zeroed_sum = calculate_word_sum(original_firmware)
        
        print(f"2. Sum with zeroed footer: 0x{zeroed_sum:04X}")
        
        # Calculate required footer
        required_footer = (-zeroed_sum) & 0xFFFF
        print(f"3. Required footer value: 0x{required_footer:04X}")
        
        # Apply fix
        original_firmware[-2:] = struct.pack("<H", required_footer)
        final_sum = calculate_word_sum(original_firmware)
        
        print(f"4. Final word sum: 0x{final_sum:04X}")
        
        if final_sum == 0:
            print(f"[SUCCESS] ✅ Checksum fix verified!")
        else:
            print(f"[ERROR] ❌ Checksum fix failed")
        
        print(f"\n[INFO] This process is automatically applied to all patches")
        
    except Exception as e:
        print(f"[ERROR] Error demonstrating checksum fixing: {e}")

def main():
    """Main function for Phase F checksum verification"""
    
    # Verify all patches
    verification_results = verify_all_patches()
    
    # Demonstrate checksum fixing
    demonstrate_checksum_fixing()
    
    print(f"\n[INFO] ========================================")
    print(f"[INFO] PHASE F COMPLETED - CHECKSUM VERIFICATION DONE!")
    print(f"[INFO] ========================================")

if __name__ == "__main__":
    main()
