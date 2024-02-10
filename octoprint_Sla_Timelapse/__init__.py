# snapshot_trigger/__init__.py

import octoprint.plugin
import RPi.GPIO as GPIO
import time

class SnapshotTriggerPlugin(octoprint.plugin.StartupPlugin):
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
            self.snapshot_timer = time.time()
        else:  # LDR Activated
            self._logger.info("LDR Activated")

    def take_snapshot(self):
        # Check if the timer has elapsed configured seconds
        snapshot_delay = self._settings.get_int(["snapshot_delay"])
        if self.snapshot_timer is not None and time.time() - self.snapshot_timer >= snapshot_delay:
            self._printer.commands(["@OCTOLAPSE TAKE-SNAPSHOT"])
            self.snapshot_timer = None
            self._logger.info("Snapshot taken!")

    def get_settings_defaults(self):
        return dict(gpio_pin=17, snapshot_delay=5)  # Default GPIO pin and snapshot delay (you can change these)

    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False)
        ]

__plugin_name__ = "Sla_timelapse Plugin"
__plugin_pythoncompat__ = ">=3.7,<4"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = SnapshotTriggerPlugin()


