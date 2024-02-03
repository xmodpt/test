import argparse
from gpiozero import Button
import time
import subprocess
from datetime import datetime
import os
import zipfile
import shutil

# Function to print with timestamp
def print_with_timestamp(message):
    print(f"{datetime.now().strftime('%d-%m-%Y %H:%M:%S')} - {message}")

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Timelapse script.')
parser.add_argument('-i', '--ignore', type=int, default=0, help='Number of triggers to ignore before starting to save files.')
parser.add_argument('-nodel', '--no-delete', action='store_true', help='Do not delete the files after zipping.')
parser.add_argument('-nozip', '--no-zip', action='store_true', help='Do not zip and do not delete the files.')
parser.add_argument('-t', '--time', type=int, default=5, help='Time to sleep before taking a photo.')
parser.add_argument('-it', '--inactive-time', type=int, default=25, help='Inactive time before ending the script.')
args = parser.parse_args()

# Get the home directory of the current user
home_dir = os.path.expanduser('~')

# Check if the timelapse folder exists
timelapse_folder = f"{home_dir}/timelapse"
if not os.path.exists(timelapse_folder):
    os.makedirs(timelapse_folder)
    print_with_timestamp(f"Created {timelapse_folder}")

# Create a timestamp for the folder name
timestamp = datetime.now().strftime("%d-%m-%Y")
job_number = 1

# Find the next available job number
while os.path.exists(f"{timelapse_folder}/timelapse_{timestamp}_Job{job_number}") or os.path.exists(f"{timelapse_folder}/timelapse_{timestamp}_Job{job_number}.zip"):
    job_number += 1

# Create the new folder
new_folder = f"{timelapse_folder}/timelapse_{timestamp}_Job{job_number}"
os.makedirs(new_folder)
print_with_timestamp(f"Created {new_folder}")

# Define the button on GPIO pin 21
button = Button(21)

# Get the number of triggers to ignore from the command-line argument
triggers_to_ignore = args.ignore
trigger_count = 0

# Initialize the last active time
last_active_time = time.time()

def button_pressed():
    global trigger_count, last_active_time
    trigger_count += 1
    last_active_time = time.time()  # Update the last active time
    if trigger_count <= triggers_to_ignore:
        print_with_timestamp(f"Ignoring {trigger_count}/{triggers_to_ignore}")
    else:
        print_with_timestamp("LDR Activated!")

def button_released():
    global trigger_count
    if trigger_count > triggers_to_ignore:
        print_with_timestamp("LDR Off... waiting to take photo!")
        time.sleep(args.time)  # Sleep for the specified time

        # Create a timestamp for the filename (including date and time)
        photo_timestamp = datetime.now().strftime("%d-%m-%Y_%H:%M:%S")
        photo_path = f"{new_folder}/timelapse_{photo_timestamp}.jpg"

        try:
            # Capture a photo using wget
            subprocess.run(["wget", f"http://localhost:8080/?action=snapshot", "-O", photo_path])

            print_with_timestamp(f"Photo saved at {photo_path}")

        except Exception as e:
            print_with_timestamp(f"Error capturing photo: {e}")

# Attach event handlers
button.when_pressed = button_pressed
button.when_released = button_released

start_time = time.time()

try:
    while True:
        # Check if the LDR has been inactive for too long
        if time.time() - last_active_time > args.inactive_time:
            print_with_timestamp("Inactive for too long. Ending the script...")
            break  # Break the loop to end the script
except KeyboardInterrupt:
    print_with_timestamp("\nInterrupted by user.")

end_time = time.time()
runtime = end_time - start_time

if not args.no_zip:
    # Zip the contents of the folder
    with zipfile.ZipFile(f"{new_folder}.zip", 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(new_folder):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, arcname=os.path.relpath(file_path, start=timelapse_folder))

    print_with_timestamp(f"\nZipped the contents of {new_folder}.")

if not args.no_delete and not args.no_zip:
    # Delete the folder and its contents
    shutil.rmtree(new_folder)
    print_with_timestamp(f"The original folder {new_folder} has been deleted.")

print_with_timestamp(f"\nExiting... The script ran for {runtime} seconds.")

# Clean up GPIO
button.close()
