"""
OctoPrint plugin to automatically take timelapse snapshots  
using a light dependent resistor (LDR) sensor.
"""

import threading
import datetime
import logging
import os

import requests 
import RPi.GPIO as GPIO
from octoprint.plugin import StartupPlugin, TemplatePlugin, SettingsPlugin, AssetPlugin

# Module constants
LDR_PIN = 21  
PHOTO_DELAY = 5 # seconds

# Setup logging
log = logging.getLogger("octoprint.plugins." + __name__)

# Import Settings
from octoprint.settings import settings

class SlaTimelapsePlugin(StartupPlugin, TemplatePlugin, 
                          SettingsPlugin, AssetPlugin):
    """
    OctoPrint plugin to take timelapse snapshots using a LDR sensor.
    """
    
    def __init__(self):
        self.photo_in_progress = False

        # Initialize settings dictionary
        self.settings = dict(
            ldr_pin=LDR_PIN,
            photo_delay=PHOTO_DELAY,
            snapshot_folder="/home/pi/timelapse"
        )
    
    
    def on_after_startup(self):
        self._setup_gpio()


    def get_settings_defaults(self):
        return self.settings
        
    def on_settings_save(self, data):
        if "timelapse_option" in data.keys():
            self.settings["timelapse_option"] = data["timelapse_option"]
        if "gpio_pin" in data.keys():
            self.settings["gpio_pin"] = int(data["gpio_pin"])

        # Save the settings
        self.save_settings()

    def save_settings(self):
        try:
            settings = {
                "timelapse_option": self.settings["timelapse_option"],
                "gpio_pin": self.settings["gpio_pin"]
            }

            # Update the plugin settings in the config file
            self._settings.set(["timelapse", "timelapse_option"], settings["timelapse_option"])
            self._settings.set_int(["timelapse", "gpio_pin"], settings["gpio_pin"])
            self._settings.save()
            self._logger.info("SLA Timelapse settings saved successfully.")
        except Exception as e:
            self._logger.error("Failed to save SLA Timelapse settings: {}".format(str(e)))
        

    def _setup_gpio(self):
        """Initialize GPIO sensor pin."""
        GPIO.setmode(GPIO.BCM) 
        GPIO.setup(self.settings['ldr_pin'], GPIO.IN, GPIO.PUD_UP)
        GPIO.add_event_detect(self.settings['ldr_pin'], 
            GPIO.BOTH, callback=self._ldr_changed, bouncetime=300)


    def _ldr_changed(self, channel):
        """Take snapshot when LDR state changes."""
        if GPIO.input(channel) and not self.photo_in_progress:
            log.info("LDR deactivated - Waiting to take photo")   
            self.photo_in_progress = True
            threading.Timer(self.settings['photo_delay'], self._take_snapshot).start()

        elif not GPIO.input(channel) and self.photo_in_progress:
            log.info("LDR activated - Canceling snapshot")
            self.photo_in_progress = False 


    def _take_snapshot(self):
        """Capture and save snapshot image."""
        try:
            response = requests.get("http://localhost:8080/webcam/?action=snapshot")
            if response.status_code == 200:
                timestamp = datetime.datetime.now().strftime("%H:%M:%S_%d-%m-%Y")
                filename = f"snapshot_{timestamp}.jpg"
                
                # Use context manager to save snapshot 
                with open(os.path.join(self.settings['snapshot_folder'], filename), "wb") as f:
                    f.write(response.content)
                
                log.info(f"Saved snapshot to {filename}")
            else:
                log.warning(f"Failed taking snapshot - status {response.status_code}")

        except Exception as e:
            log.exception(f"Failed to save snapshot: {e}")
        
        finally:
            self.photo_in_progress = False
    
    def get_timelapse_files():
        timelapse_path = "~/timelapse"
        files = [f for f in os.listdir(os.path.expanduser(timelapse_path))
                 if os.path.isfile(os.path.join(timelapse_path, f)) and f.endswith(".jpg")]
        return files
    
    
__plugin_name__ = "Sla Timelapse"
__plugin_pythoncompat__ = ">=3.7,<4"  

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = SlaTimelapsePlugin()
