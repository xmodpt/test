# snapshot_trigger/__init__.py
from datetime import datetime
import octoprint.plugin
import RPi.GPIO as GPIO
import requests
import os
import threading

class SnapshotTriggerPlugin(octoprint.plugin.StartupPlugin, octoprint.plugin.SettingsPlugin, octoprint.plugin.TemplatePlugin, octoprint.plugin.AssetPlugin):
    def on_after_startup(self):
        # Initialize GPIO and register the callback
        self._setup_gpio()

    def _setup_gpio(self):
        gpio_pin = self._settings.get_int(["gpio_pin"])
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(gpio_pin, GPIO.BOTH, callback=self.handle_ldr_state, bouncetime=300)
        self.snapshot_timer = None

    def handle_ldr_state(self, channel):
        if GPIO.input(channel):  # LDR Deactivated
            self._logger.info("LDR Deactivated... waiting for photo in {} seconds".format(self._settings.get_int(["snapshot_delay"])))
            t = threading.Timer(self._settings.get_int(["snapshot_delay"]), self.take_snapshot)
            t.start()
        else:  # LDR Activated
            self._logger.info("LDR Activated")

    def take_snapshot(self):
        # Create a timestamp for the filename (including date and time)
        photo_timestamp = datetime.now().strftime("%d-%m-%Y_%H:%M:%S")
        photo_path = self.get_plugin_data_folder()
        photo_file = os.path.join(photo_path, f"{photo_timestamp}.jpg")

        try:
            response = requests.get("http://localhost:8080/?action=snapshot", timeout=20)
            if response.status_code == 200:
                with open(photo_file, "wb") as f:
                    f.write(response.content)
                self._logger.info(f"Photo saved at {photo_file}")

        except Exception as e:
            self._logger.info(f"Error capturing photo: {e}")

    def get_settings_defaults(self):
        return dict(gpio_pin=21, snapshot_delay=5)  # Default GPIO pin and snapshot delay (you can change these)

    def on_settings_changed(self, data):
        old_gpio = self._settings.get_int(["gpio_pin"])
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        if old_gpio != self._settings.get_int(["gpio_pin"]):
            self._setup_gpio()


    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False, template="sla_timelapse_settings.jinja2")
        ]

    def get_assets(self):
        return {"js": ["js/Sla_Timelapse.js.js"]}

__plugin_name__ = "Sla_timelapse Plugin"
__plugin_pythoncompat__ = ">=3.7,<4"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = SnapshotTriggerPlugin()


