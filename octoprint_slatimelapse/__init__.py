##############################################
#                            V6.1
# the settigns all work
#
# added timout and reset
# added job folders
# added file numbering
# added timelapse FFmpeg file creation and output
# added copy timelpase video to main folder
# added octopring.log configs output
# added check to use any "~" folder other then "pi"
#
#
#also added to settings
# * Img for the printer delay
# * button "Make an LDR cable" with png of cable
# * "i" buttons for more info
#
#also added to navbar
# * SlaTimelapse On/OFF button <----------- WORKING
# 
##############################################
import os
import flask
from octoprint.plugin import StartupPlugin, TemplatePlugin, SettingsPlugin, AssetPlugin, SimpleApiPlugin
import RPi.GPIO as GPIO
import threading
import logging
import time
import requests
import subprocess
import shutil

PHOTO_DELAY = 5  # seconds
INACTIVE_TIMEOUT = 240  # seconds

log = logging.getLogger("octoprint.plugins.sla_timelapse")

class SlaTimelapsePlugin(StartupPlugin, TemplatePlugin, SettingsPlugin, AssetPlugin, SimpleApiPlugin):
    def __init__(self):
        super().__init__()
        self.photo_in_progress = False
        self.last_active_time = None
        self.job_folder = None  # Initialize job folder attribute
        self.stop_thread = threading.Event()  # Event to signal thread termination
        self._avi_files = []  # Initialize the list of AVI files
        self._avi_folder = None  # Path to the folder where AVI files are stored
        self.enabled = False  # Track whether the plugin is enabled or disabled

    def get_settings_defaults(self):
        return dict(
            gpio_pin=21,
            photo_delay=PHOTO_DELAY,
            snapshot_folder=os.path.expanduser("~/timelapse"),  # Dynamic folder path
            enabled=False,
            timeout=INACTIVE_TIMEOUT,
            avi_folder=os.path.expanduser("~/timelapse")  # Default path for AVI files
        )

    def on_after_startup(self):
        self.enabled = self._settings.get_boolean(["enabled"])
        if self.enabled:
            self._setup_gpio()

    def on_settings_save(self, data):
        old_enabled = self.enabled
        SettingsPlugin.on_settings_save(self, data)
        new_enabled = self._settings.get_boolean(["enabled"])
        if old_enabled != new_enabled:
            self.enabled = new_enabled
            if self.enabled:
                self._setup_gpio()
            else:
                self._cleanup()

    def _setup_gpio(self):
        gpio_pin = self._settings.get_int(["gpio_pin"])
        log.info(f"GPIO Pin retrieved from settings: {gpio_pin}")
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(gpio_pin, GPIO.BOTH, callback=self._ldr_changed, bouncetime=100)

    def _cleanup(self):
        # Clean up GPIO and any ongoing processes
        GPIO.cleanup()
        self.stop_thread.set()

    def _ldr_changed(self, channel):
        if not self.enabled:
            return

        if GPIO.input(channel) and not self.photo_in_progress:
            log.info("LDR deactivated - Waiting to take photo")
            self.photo_in_progress = True
            self.last_active_time = time.time()
            
            if not self.job_folder:
                self._create_job_folder()
            
            threading.Timer(self._settings.get_float(["photo_delay"]), self._take_snapshot).start()

            # Reset the stop flag when a new activity is detected
            self.stop_thread.clear()

            # Start a new timeout thread
            threading.Thread(target=self._timeout_check).start()
        elif not GPIO.input(channel) and self.photo_in_progress:
            log.info("LDR activated")
            self.photo_in_progress = False

    def _timeout_check(self):
        while not self.stop_thread.is_set():
            if time.time() - self.last_active_time > INACTIVE_TIMEOUT:
                self._handle_timeout()
                break
            time.sleep(1)

    def _handle_timeout(self):
        log.info("Timeout reached. Finishing the job and creating timelapse video.")
        self.photo_in_progress = False
        self._create_timelapse_video()
        self.job_folder = None
        if self.enabled:
            self._setup_gpio()  # Re-setup GPIO for new job

    def _create_job_folder(self):
        timestamp = time.strftime("%d-%m-%Y")
        job_number = 1

        default_folder = self._settings.get(["snapshot_folder"])

        # Check if the default folder exists, create it if it doesn't
        if not os.path.exists(default_folder):
            os.makedirs(default_folder)
            log.info(f"Created default folder: {default_folder}")

        while True:
            self.job_folder = f"{default_folder}/timelapse_{timestamp}_Job{job_number}"
            if not os.path.exists(self.job_folder):
                os.makedirs(self.job_folder)
                log.info(f"Created folder for job {job_number}")
                break
            else:
                job_number += 1

    def _take_snapshot(self):
        try:
            response = requests.get("http://localhost:8080/webcam/?action=snapshot", timeout=10)
            if response.status_code == 200:
                job_name = os.path.basename(self.job_folder)
                file_number = self._get_next_file_number(job_name)
                filename = f"snapshot_{job_name}_{file_number:06d}.jpg"
                with open(os.path.join(self.job_folder, filename), "wb") as f:
                    f.write(response.content)
                log.info(f"Saved snapshot to {self.job_folder}/{filename}")
            else:
                log.warning(f"Failed taking snapshot - status {response.status_code}")
        except requests.RequestException as e:
            log.exception(f"Failed to save snapshot: {e}")
        finally:
            self.photo_in_progress = False

    def _get_next_file_number(self, job_name):
        # Scan existing files in the job folder and return the next available file number
        files = os.listdir(self.job_folder)
        existing_numbers = []
        for file in files:
            if file.startswith(f"snapshot_{job_name}_"):
                try:
                    number = int(file.split("_")[-1].split(".")[0])
                    existing_numbers.append(number)
                except ValueError:
                    pass
        if existing_numbers:
            return max(existing_numbers) + 1
        else:
            return 1

    def _create_timelapse_video(self):
        try:
            if self.job_folder:
                job_name = os.path.basename(self.job_folder)
                input_pattern = os.path.join(self.job_folder, f"snapshot_{job_name}_%06d.jpg")

                job_number = job_name.split("_")[-1].split("Job")[-1]  # Extract job number

                output_file = os.path.join(self.job_folder, f"{job_name}.avi")

                # Run FFmpeg command to create the timelapse video
                cmd = [
                    "ffmpeg",
                    "-r", "60",  # Frame rate
                    "-i", input_pattern,
                    "-c:v", "libx264",  # Video codec
                    "-vf", "fps=60",  # Output frame rate
                    output_file
                ]

                subprocess.run(cmd, check=True)
                log.info("Timelapse video created successfully.")

                # Copy the video file to the main timelapse folder
                main_timelapse_folder = self._settings.get(["snapshot_folder"])
                if not os.path.exists(main_timelapse_folder):
                    os.makedirs(main_timelapse_folder)
                
                final_output_file = os.path.join(main_timelapse_folder, f"{job_name}_Job{job_number}.avi")
                shutil.copy(output_file, final_output_file)

                # Update the list of AVI files
                self._avi_files.append(final_output_file)

            else:
                log.warning("Job folder is not set. Cannot create timelapse video.")
        except Exception as e:
            log.exception(f"Failed to create timelapse video: {e}")

    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=True, template="slatimelapse_settings.jinja2"),
            dict(type="navbar", custom_bindings=True, template="slatimelapse_navbar.jinja2"),
            dict(type="tab", custom_bindings=True, template="slatimelapse_tab.jinja2", data_bind="allowBind: true")
        ]

    def get_assets(self):
        return dict(
            js=["js/slatimelapse.js"]
        )

        
__plugin_name__ = "Sla Timelapse"
__plugin_pythoncompat__ = ">=3.7,<4"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = SlaTimelapsePlugin()
