<<<<<<< HEAD
# gopro-auto-sync
Automatically sync files from your GoPro 12 camera on Ubuntu.
=======
GoPro Auto Sync Tool
Description
This Python script, gopro_sync.py, automates the process of transferring files from a connected GoPro camera to your Ubuntu system. It detects the camera connection, locates the mount point, and then either copies or moves the new files to a destination directory, organizing them into subdirectories based on their modification date (MM-DD-YYYY).
This is particularly useful for quickly and easily backing up your GoPro footage without manual file management.
Features
** Automatic GoPro Detection:** Detects GoPro camera connection via USB.
** File Transfer:** Copies or moves files from the GoPro to a specified destination directory.
** Date-Based Organization:** Organizes transferred files into subdirectories by their modification date (MM-DD-YYYY).
** Logging:** Logs all operations to ~/gopro_sync.log.
** Verbose Output:** Provides detailed output to the console when enabled.
** Move or Copy:** Supports either moving or copying files (move removes files from the GoPro).
** Success Notification:** Plays a sound and/or sends a desktop notification upon successful transfer.
** Customizable:**
Destination directory
Logging
Sound file
Notification
** GVFS Support:** Automatically finds the GoPro mount point
Requirements
Ubuntu Linux
Python 3
gi (GObject Introspection) and Notify for desktop notifications (sudo apt install python3-gi gir1.2-notify-0.7)
systemd (for automatic execution)
Audio player for success sound (e.g., paplay, aplay, play, mpg123, mplayer)
Installation
** Save the script:**
Save the python script (e.g., gopro_sync.py) to a directory, for example /usr/local/bin/.
Make the script executable:
sudo chmod +x /usr/local/bin/gopro_sync.py


Dependencies:
Install the required dependencies:
sudo apt update
sudo apt install python3-gi gir1.2-notify-0.7


Usage
gopro_sync.py [-h] [-v] [--move] [--sound SOUND] [--no-notify]


Options
-h, --help: Show the help message and exit.
-v, --verbose: Enable verbose output to the console and log file.
--move: Move files from the GoPro camera instead of copying them. This will delete the files from the GoPro after they are successfully transferred.
--sound SOUND: Specify the path to a sound file to play upon successful transfer. Defaults to /usr/share/sounds/freedesktop/stereo/complete.oga.
--no-notify: Disable desktop notifications.
Examples
Copy files from the GoPro to the default destination directory, with logging:
gopro_sync.py


Move files and enable verbose output:
gopro_sync.py --move -v


Copy files and use a custom sound file:
gopro_sync.py --sound /path/to/your/sound.ogg


Copy files without desktop notifications
gopro_sync.py --no-notify


Automatic Execution with udev and systemd
To automatically run the script when you connect your GoPro, you can use udev to detect the device and systemd to run the script as your user.
1. Create a udev rule
Create a new file in the /etc/udev/rules.d/ directory (e.g., 99-gopro.rules) with the following content:
ACTION=="add", SUBSYSTEM=="usb", ATTRS{idVendor}=="2672", ATTRS{idProduct}=="0059", RUN+="/usr/local/bin/gopro_trigger.sh"


This rule tells udev to execute the /usr/local/bin/gopro_trigger.sh script when a USB device with the specified Vendor ID (2672) and Product ID (0059) (GoPro HERO12) is connected. You may need to adjust the Vendor and Product IDs for other GoPro models.
2. Create a trigger script
Create a new executable script, for example, /usr/local/bin/gopro_trigger.sh, with the following content:
#!/bin/bash
USER_ID=$(id -u your_user_name)
/usr/bin/systemd-run --user --scope --uid="$USER_ID" /usr/bin/python3 /usr/local/bin/gopro_sync.py

Replace your_user_name with your actual username (e.g., hartcl1).
Make the script executable:
sudo chmod +x /usr/local/bin/gopro_trigger.sh


3. Reload udev rules
Reload the udev rules and trigger an event:
sudo udevadm control --reload-rules
sudo udevadm trigger


Systemd User Service (Alternative to udev)
As an alternative to udev rules, you can create a systemd user service to run the script on login. This approach might be simpler for some users.
1. Create the systemd service file
Create the file ~/.config/systemd/user/gopro-sync.service with the following content:
[Unit]
Description=GoPro Auto Sync Service
After=graphical.target # Or another appropriate target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/local/bin/gopro_sync.py # Adjust the paths
WorkingDirectory=/home/your_user_name # Set this
StandardOutput=file:/home/your_user_name/gopro_sync.log
StandardError=file:/home/your_user_name/gopro_sync_error.log
User=your_user_name
Group=your_user_name

[Install]
WantedBy=default.target


Replace your_user_name with your actual username.
Adjust the ExecStart and WorkingDirectory paths if necessary to match where you've stored the script.
2. Enable the service
Enable the service:
systemctl --user daemon-reload
systemctl --user enable gopro-sync.service
systemctl --user start gopro-sync.service


3. Check the service status
Check the status of the service:
systemctl --user status gopro-sync.service


You can view the log with:
tail -f /home/your_user_name/gopro_sync.log


Configuration
** Destination Directory:** The default destination directory is /Zdir/GoPro. You can change this by modifying the DEST_DIR variable in the script.
** Log File:** The default log file is ~/gopro_sync.log.
** Check Interval:** The script checks for a connected GoPro every 5 seconds. This is defined by the CHECK_INTERVAL variable.
** Success Sound:** The default sound file is /usr/share/sounds/freedesktop/stereo/complete.oga. You can change this using the --sound argument.
** Desktop Notifications:** Desktop notifications are enabled by default. Use the --no-notify argument to disable them.
** File Action:** The script copies files by default. Use the --move argument to move them.
Logging
The script logs all activities to ~/gopro_sync.log. You can review this file to check for errors or verify that files have been transferred successfully.
Troubleshooting
** GoPro Not Detected:**
Ensure the GoPro is properly connected via USB.
Check the output of lsusb to see if the GoPro is listed. Verify the Vendor and Product IDs.
Check the log file (~/gopro_sync.log) for any errors.
Make sure the udev rule is correctly configured (if using).
Make sure the systemd service is correctly configured and running (if using).
** Permission Errors:**
Ensure the script has the necessary permissions to write to the destination directory.
If using the udev rule, ensure the script is executed as your user.
** Mount Point Not Found:**
The script relies on the GoPro being mounted as a removable drive. Ensure your system is configured to automount removable media.
Check if the GoPro is mounted using the mount command.
If you are having problems with the script finding the mount point, try to mount the GoPro manually and then run the python script.
** No New Files Transferred:**
The script only transfers files that do not already exist in the destination directory. If you have previously transferred the files, they will not be transferred again.
** Desktop Notifications Not Working:**
Ensure that the Notify library is installed and that your desktop environment supports notifications.
Check the log file for any errors related to sending notifications.
** Sound Not Playing:**
Ensure that the specified sound file exists and is readable.
Ensure that you have a compatible audio player installed (e.g., paplay, aplay, play, mpg123, mplayer).
Check the log file for any errors related to playing the sound.

>>>>>>> b39e3b6 (Initial commit)
