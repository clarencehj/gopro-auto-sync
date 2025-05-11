#!/usr/bin/env python3
"""
GoPro Auto Sync Tool

This script detects when a GoPro camera is connected to an Ubuntu system,
verifies the mount, and either copies or moves new files to a specified
directory, organized by the file's modification date.
"""

import os
import sys
import time
import shutil
import logging
import subprocess
import re
from pathlib import Path
from datetime import datetime
import argparse
import gi
gi.require_version('Notify', '0.7')
from gi.repository import Notify

# Configuration
DEST_DIR = "/Zdir/GoPro"
LOG_FILE = "~/gopro_sync.log"
CHECK_INTERVAL = 5  # seconds
# Sound file to play when operation completes successfully
SUCCESS_SOUND = "/usr/share/sounds/freedesktop/stereo/complete.oga"

# GoPro specific constants based on your logs
GOPRO_VENDOR_ID = "2672"
GOPRO_PRODUCT_ID = "0059"
GOPRO_MODEL = "HERO12 Black"

# Set up argument parsing
parser = argparse.ArgumentParser(description="GoPro Auto Sync Tool")
parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
parser.add_argument("--move", action="store_true", help="Move files instead of copying")
parser.add_argument("--sound", type=str, default=SUCCESS_SOUND, help="Path to sound file to play on success")
parser.add_argument("--no-notify", action="store_true", help="Disable desktop notifications")
args = parser.parse_args()

# Set up logging based on verbosity
log_level = logging.DEBUG if args.verbose else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("gopro_sync")

def find_gopro_gvfs_mount():
    """Find the GoPro mount point under GVFS by listing its contents."""
    user_id = os.getuid()
    gvfs_path = Path(f"/run/user/{user_id}/gvfs")
    if gvfs_path.exists():
        if args.verbose:
            logger.debug(f"Listing contents of {gvfs_path}")
        for item in gvfs_path.iterdir():
            if args.verbose:
                logger.debug(f"Found item in GVFS: {item}")
            if "gopro" in str(item).lower() or GOPRO_VENDOR_ID in str(item).lower() or GOPRO_PRODUCT_ID in str(item).lower() or "mtp" in str(item).lower():
                potential_mount_point = gvfs_path / item
                if potential_mount_point.is_dir():
                    if args.verbose:
                        logger.info(f"Potential GoPro GVFS mount found: {potential_mount_point}")
                    return str(potential_mount_point)
                else:
                    # It might be a gvfs control file, so we continue searching
                    if args.verbose:
                        logger.debug(f"{potential_mount_point} is not a directory.")
    return None

def is_gopro_connected():
    """Check if a GoPro camera is connected and return its mount point if found."""
    # Method 1: Check USB devices for GoPro VENDOR_ID and PRODUCT_ID
    result = subprocess.run(['lsusb'], capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if GOPRO_VENDOR_ID in line and GOPRO_PRODUCT_ID in line:
            if args.verbose:
                logger.info(f"GoPro camera detected via lsusb: {line.strip()}")
            # If detected, now try to find the mount point via GVFS
            mount_point = find_gopro_gvfs_mount()
            if mount_point:
                return mount_point
            else:
                if args.verbose:
                    logger.info("GoPro detected, attempting to find mount point...")
                found_mount = find_gopro_mount_point()
                if found_mount:
                    return found_mount
                else:
                    return None
    return None

def find_gopro_mount_point():
    """Find the GoPro mount point."""
    mount_point = find_gopro_gvfs_mount()
    if mount_point:
        return mount_point
    return None

def get_device_info():
    """Get more detailed information about the connected device."""
    if not args.verbose:
        return {}
        
    try:
        mount_info = subprocess.run(['mount'], capture_output=True, text=True).stdout
        usb_info = subprocess.run(['lsusb'], capture_output=True, text=True).stdout
        df_info = subprocess.run(['df', '-h'], capture_output=True, text=True).stdout

        # Check if GoPro is connected via MTP
        mtp_info = subprocess.run(['lsusb', '-v'], capture_output=True, text=True).stdout
        gvfs_info_gio = ""
        gvfs_list = ""
        user_id = os.getuid()
        gvfs_path_str = f"/run/user/{user_id}/gvfs/"
        gvfs_path = Path(gvfs_path_str)
        if gvfs_path.exists():
            try:
                gvfs_list_output = subprocess.run(['ls', '-la', gvfs_path_str], capture_output=True, text=True).stdout
                gvfs_list = f"Contents of {gvfs_path_str}:\n{gvfs_list_output}"
            except Exception as e:
                gvfs_list = f"Error listing {gvfs_path_str}: {e}"
        else:
            gvfs_list = f"{gvfs_path_str} does not exist."

        try:
            gvfs_info_gio = subprocess.run(['gio', 'mount', '-l'], capture_output=True, text=True).stdout
            gvfs_info_gio = f"gio mount -l output:\n{gvfs_info_gio}"
        except Exception as e:
            gvfs_info_gio = f"Error running gio mount -l: {e}"

        # Get the latest dmesg logs related to GoPro
        dmesg_logs = subprocess.run(['dmesg', '|', 'grep', '-i', 'gopro', '|', 'tail', '-n', '20'],
                                     shell=True, capture_output=True, text=True).stdout

        return {
            'mount': mount_info,
            'usb': usb_info,
            'disk_space': df_info,
            'mtp': mtp_info,
            'gvfs_gio': gvfs_info_gio,
            'gvfs_list': gvfs_list,
            'dmesg': dmesg_logs
        }
    except Exception as e:
        logger.error(f"Error getting device info: {e}")
        return {}

def send_desktop_notification(summary, body, icon="camera-photo"):
    """Send a desktop notification to the Ubuntu notification system."""
    try:
        # Initialize the notification system
        Notify.init("GoPro Auto Sync Tool")
        
        # Create the notification
        notification = Notify.Notification.new(
            summary,
            body,
            icon  # Using standard icon - could be replaced with a custom one
        )
        
        # Show the notification
        notification.show()
        logger.debug("Desktop notification sent")
        
        # Clean up
        Notify.uninit()
        return True
    except Exception as e:
        logger.warning(f"Failed to send desktop notification: {e}")
        return False

def play_success_sound():
    """Play a sound to indicate successful completion."""
    if os.path.exists(args.sound):
        try:
            # Try to play using various common audio players
            players = [
                ['paplay', args.sound],  # PulseAudio
                ['aplay', args.sound],   # ALSA
                ['play', args.sound],    # SoX
                ['mpg123', args.sound],  # MPG123
                ['mplayer', args.sound]  # MPlayer
            ]
            
            for player in players:
                try:
                    subprocess.run(player, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    logger.debug(f"Successfully played sound using {player[0]}")
                    return
                except (subprocess.SubprocessError, FileNotFoundError):
                    continue
                    
            logger.warning(f"Could not play success sound: No suitable audio player found")
        except Exception as e:
            logger.warning(f"Failed to play success sound: {e}")
    else:
        logger.warning(f"Success sound file not found: {args.sound}")

def copy_or_move_files(source_dir):
    """Copy or move new files from the GoPro to the destination directory,
    organized by the file's modification date (MM-DD-YYYY)."""
    try:
        # Make sure the destination directory exists
        os.makedirs(DEST_DIR, exist_ok=True)

        files_to_process = []
        for root, _, files in os.walk(source_dir):
            for file in files:
                src_path = os.path.join(root, file)
                mtime = os.path.getmtime(src_path)
                date_obj = datetime.fromtimestamp(mtime)
                date_subdir_name = date_obj.strftime("%m-%d-%Y")
                dest_subdir = os.path.join(DEST_DIR, date_subdir_name)
                dest_path = os.path.join(dest_subdir, os.path.basename(src_path))
                if not os.path.exists(dest_path):
                    files_to_process.append(src_path)

        total_new_files = len(files_to_process)
        if args.verbose:
            logger.info(f"Found {sum([len(f) for r, d, f in os.walk(source_dir)])} files to process.") # Show total in source
        logger.info(f"### {total_new_files} new files found ###")

        processed_new_files = 0
        total_size_processed = 0

        for i, src_path in enumerate(files_to_process):
            try:
                mtime = os.path.getmtime(src_path)
                date_obj = datetime.fromtimestamp(mtime)
                date_subdir_name = date_obj.strftime("%m-%d-%Y")
                dest_subdir = os.path.join(DEST_DIR, date_subdir_name)
                os.makedirs(dest_subdir, exist_ok=True)
                dest_path = os.path.join(dest_subdir, os.path.basename(src_path))

                if args.move:
                    if args.verbose:
                        logger.debug(f"Moving: {os.path.basename(src_path)} to {dest_subdir}")
                    shutil.move(src_path, dest_path)
                else:
                    if args.verbose:
                        logger.debug(f"Copying: {os.path.basename(src_path)} to {dest_subdir}")
                    shutil.copy2(src_path, dest_path)

                file_size = os.path.getsize(dest_path)
                total_size_processed += file_size
                processed_new_files += 1

                if ((i + 1) % 10 == 0 or (i + 1) == total_new_files):
                    action = "Moved" if args.move else "Copied"
                    logger.info(f"Progress: {processed_new_files}/{total_new_files} files {action} ({total_size_processed / (1024*1024):.2f} MB)")

            except Exception as e:
                logger.error(f"Error processing {src_path}: {e}")

        action_done = "moved" if args.move else "copied"
        logger.info(f"Successfully {action_done} {processed_new_files} new files ({total_size_processed / (1024*1024):.2f} MB) to {DEST_DIR}, organized by date (MM-DD-YYYY).")
        return True, processed_new_files, total_new_files, total_size_processed
    except Exception as e:
        logger.error(f"Error during file processing: {e}")
        return False, 0, 0, 0

def check_mtp_connection():
    """Check if GoPro is connected via MTP using specific GoPro identifiers."""
    try:
        # Check for GoPro in lsusb output
        lsusb_result = subprocess.run(['lsusb'], capture_output=True, text=True)
        for line in lsusb_result.stdout.split('\n'):
            if GOPRO_VENDOR_ID in line and GOPRO_PRODUCT_ID in line:
                if args.verbose:
                    logger.debug(f"GoPro camera found in USB devices (lsusb): {line.strip()}")
                return True
        return False
    except Exception as e:
        logger.error(f"Error checking MTP connection: {e}")
        return False

def try_access_gopro_mtp():
    """Try to access GoPro via MTP and list its contents using gio mount."""
    try:
        user_id = os.getuid()

        # List currently mounted GVFS mounts
        gio_list_cmd = "gio mount -l"
        gio_list_result = subprocess.run(gio_list_cmd, shell=True, capture_output=True, text=True)
        if args.verbose:
            logger.debug(f"gio mount -l output:\n{gio_list_result.stdout}")
        for line in gio_list_result.stdout.split('\n'):
            if "GoPro" in line or GOPRO_VENDOR_ID in line or GOPRO_PRODUCT_ID in line:
                # Try to find the mount path from the URI
                match = re.search(r"at (.*)", line)
                if match:
                    mount_path = match.group(1)
                    if Path(mount_path).exists():
                        if args.verbose:
                            logger.info(f"Found GoPro mount path from gio list: {mount_path}")
                        return mount_path
                # If no explicit mount path, try to find it in the GVFS directory
                gvfs_mount = find_gopro_gvfs_mount()
                if gvfs_mount:
                    return gvfs_mount

        # If not found in the list, we might need to explicitly mount it (though usually it auto-mounts)
        # We can't reliably get the MTP URI to mount without it being listed first.

        return None
    except Exception as e:
        logger.error(f"Error accessing GoPro via gio: {e}")
        return None

def main():
    """Main function to detect GoPro connection and process files with a timeout."""
    action_type = "moving" if args.move else "copying"
    logger.info("GoPro Auto Sync Tool started (udev triggered)")
    logger.info(f"Looking for GoPro {GOPRO_MODEL} (VendorID={GOPRO_VENDOR_ID}, ProductID={GOPRO_PRODUCT_ID})")
    logger.info(f"Will be {action_type} new files to {DEST_DIR}, organized by date (MM-DD-YYYY)")

    timeout = time.time() + 7  # Set a 7-second timeout

    while time.time() < timeout:
        if check_mtp_connection():
            if args.verbose:
                logger.info("GoPro camera detected on USB bus")

            # Try to find the mount point
            gopro_mount = is_gopro_connected()

            if not gopro_mount:
                if args.verbose:
                    logger.info("Trying to find GoPro mount point...")
                gopro_mount = find_gopro_mount_point()

            if not gopro_mount:
                if args.verbose:
                    logger.info("Trying to access GoPro via gio...")
                gopro_mount = try_access_gopro_mtp()

            if gopro_mount:
                if args.verbose:
                    logger.info(f"GoPro camera detected at mount point: {gopro_mount}")

                # Get more device info for debugging
                device_info = get_device_info()
                if args.verbose:
                    logger.debug(f"USB devices: {device_info.get('usb', 'Not available')}")
                    logger.debug(f"Mount info: {device_info.get('mount', 'Not available')}")
                    logger.debug(f"GVFS info (gio mount -l): {device_info.get('gvfs_gio', 'Not available')}")
                    logger.debug(f"GVFS directory contents: {device_info.get('gvfs_list', 'Not available')}")

                # Check if the mount point exists and is readable
                if os.path.exists(gopro_mount) and os.access(gopro_mount, os.R_OK):
                    if args.verbose:
                        logger.info(f"Mount point {gopro_mount} is accessible")

                    # List contents to verify
                    try:
                        contents = os.listdir(gopro_mount)
                        if args.verbose:
                            logger.info(f"Found {len(contents)} items in {gopro_mount}")

                        # Look for DCIM directory and process files
                        source_to_process = gopro_mount
                        if 'DCIM' in contents:
                            source_to_process = os.path.join(gopro_mount, 'DCIM')
                            if args.verbose:
                                logger.info(f"Processing files from DCIM directory: {source_to_process}")
                        else:
                            if args.verbose:
                                logger.info(f"Processing files from the root of the mount: {source_to_process}")

                        success, processed_files, total_files, total_size = copy_or_move_files(source_to_process)
                        if success:
                            # Play success sound
                            play_success_sound()
                            
                            # Generate notification message with the specific format requested
                            action_done = "moved" if args.move else "copied"
                            summary = f"Status: Successful"
                            body = f"Progress: {processed_files}/{total_files} files {action_done}\n" \
                                  f"Total {total_size / (1024*1024):.2f} MB transferred to {DEST_DIR}"
                            
                            # Send desktop notification
                            if not args.no_notify:
                                send_desktop_notification(summary, body)
                                
                            logger.info("File processing completed successfully. Exiting.")
                            sys.exit(0)
                        else:
                            # Send failure notification
                            if not args.no_notify:
                                send_desktop_notification(
                                    "Status: Failed", 
                                    "Progress: 0/0 files processed\n" \
                                    "Error occurred during file transfer", 
                                    "dialog-error"
                                )
                            logger.error("Failed to process files. Exiting with error.")
                            sys.exit(1)

                    except Exception as e:
                        # Send failure notification with error details
                        if not args.no_notify:
                            send_desktop_notification(
                                "Status: Failed", 
                                f"Progress: 0/0 files processed\n" \
                                f"Error listing contents: {str(e)}", 
                                "dialog-error"
                            )
                        logger.error(f"Error listing contents: {e}. Exiting with error.")
                        sys.exit(1)
                else:
                    # Send failure notification for inaccessible mount
                    if not args.no_notify:
                        send_desktop_notification(
                            "Status: Failed", 
                            f"Progress: 0/0 files processed\n" \
                            f"Mount point {gopro_mount} is not accessible", 
                            "dialog-error"
                        )
                    logger.error(f"Mount point {gopro_mount} is not accessible. Exiting with error.")
                    sys.exit(1)
            else:
                if args.verbose:
                    logger.info("GoPro detected but mount point not found. Continuing to wait briefly...")
                time.sleep(1) # Small delay before next check
        else:
            if args.verbose:
                logger.info("No GoPro camera detected. Continuing to wait briefly...")
            time.sleep(1) # Small delay before next check

    logger.info("Timeout reached. Exiting.")
    sys.exit(0)

if __name__ == "__main__":
    main()
