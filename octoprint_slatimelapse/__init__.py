from octoprint.plugin import StartupPlugin, TemplatePlugin, SettingsPlugin
import RPi.GPIO as GPIO
import threading
import datetime
import logging
import os
import time
import requests

PHOTO_DELAY = 5  # seconds

log = logging.getLogger("octoprint.plugins.sla_timelapse")

class SlaTimelapsePlugin(StartupPlugin, TemplatePlugin, SettingsPlugin):
    def __init__(self):
        self.photo_in_progress = False

    def get_settings_defaults(self):
        return dict(
            gpio_pin=21,
            photo_delay=PHOTO_DELAY,
            snapshot_folder="/home/pi/timelapse"
        )

    def on_after_startup(self):
        self._setup_gpio()

    def _setup_gpio(self):
        gpio_pin = self._settings.get_int(["gpio_pin"])
        log.info(f"GPIO Pin retrieved from settings: {gpio_pin}")
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(gpio_pin, GPIO.BOTH, callback=self._ldr_changed, bouncetime=300)

    def _ldr_changed(self, channel):
        if GPIO.input(channel) and not self.photo_in_progress:
            log.info("LDR deactivated - Waiting to take photo")
            self.photo_in_progress = True
            threading.Timer(self._settings.get_float(["photo_delay"]), self._take_snapshot).start()
        elif not GPIO.input(channel) and self.photo_in_progress:
            log.info("LDR activated - Canceling snapshot")
            self.photo_in_progress = False

    def _take_snapshot(self):
        try:
            response = requests.get("http://localhost:8080/webcam/?action=snapshot")
            if response.status_code == 200:
                timestamp = datetime.datetime.now().strftime("%H:%M:%S_%d-%m-%Y")
                filename = f"snapshot_{timestamp}.jpg"
                with open(os.path.join(self._settings.get(["snapshot_folder"]), filename), "wb") as f:
                    f.write(response.content)
                log.info(f"Saved snapshot to {filename}")
            else:
                log.warning(f"Failed taking snapshot - status {response.status_code}")
        except Exception as e:
            log.exception(f"Failed to save snapshot: {e}")
        finally:
            self.photo_in_progress = False

    def get_template_vars(self):
        # Get the default template variables
        template_vars = super(SlaTimelapsePlugin, self).get_template_vars()

        # Add the GPIO pin setting to the template variables
        template_vars["gpio_pin"] = self._settings.get_int(["gpio_pin"])

        return template_vars

__plugin_name__ = "Sla Timelapse"
__plugin_pythoncompat__ = ">=3.7,<4"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = SlaTimelapsePlugin()
