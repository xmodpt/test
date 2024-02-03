# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from gpiozero import Button
import time
import subprocess
from datetime import datetime
import os
import zipfile
import shutil
import octoprint.plugin

class Sla_timelapsePlugin(octoprint.plugin.StartupPlugin,
                          octoprint.plugin.SettingsPlugin,
                          octoprint.plugin.AssetPlugin,
                          octoprint.plugin.TemplatePlugin,
                          octoprint.plugin.SimpleApiPlugin
):
    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return dict()

    ##~~ AssetPlugin mixin

    def get_assets(self):
        return {
            "js": ["js/Sla_Timelapse.js"],
            "css": ["css/Sla_Timelapse.css"],
            "less": ["less/Sla_Timelapse.less"]
        }

    ##~~ Softwareupdate hook

    def get_update_information(self):
        return {
            "Sla_Timelapse": {
                "displayName": "Sla_timelapse Plugin",
                "displayVersion": self._plugin_version,
                "type": "github_release",
                "user": "https://github.com/xmodpt",
                "repo": "Octoprint-Sla_Timelapse",
                "current": self._plugin_version,
                "pip": "https://github.com/https://github.com/xmodpt/Octoprint-Sla_Timelapse/archive/{target_version}.zip",
            }
        }

    def print_with_timestamp(self, message):
        print(f"{datetime.now().strftime('%d-%m-%Y %H:%M:%S')} - {message}")

    def button_pressed(self):
        self.trigger_count += 1
        self.last_active_time = time.time()
        if self.trigger_count <= self.triggers_to_ignore:
            self.print_with_timestamp(f"Ignoring {self.trigger_count}/{self.triggers_to_ignore}")
        else:
            self.print_with_timestamp("LDR Activated!")

    def button_released(self):
        if self.trigger_count > self.triggers_to_ignore:
            self.print_with_timestamp("LDR Off... waiting to take photo!")
            time.sleep(self.t)
            photo_timestamp = datetime.now().strftime("%d-%m-%Y_%H:%M:%S")
            photo_path = f"{self.new_folder}/timelapse_{photo_timestamp}.jpg"
            try:
                subprocess.run(["wget", f"http://localhost:8080/?action=snapshot", "-O", photo_path])
                self.print_with_timestamp(f"Photo saved at {photo_path}")
            except Exception as e:
                self.print_with_timestamp(f"Error capturing photo: {e}")

    def on_after_startup(self):
        self.t = 5
        self.it = 25
        self.ignore = 0
        self.nozip = False
        self.nodel = False
        self.home_dir = os.path.expanduser('~')
        self.timelapse_folder = f"{self.home_dir}/timelapse"
        if not os.path.exists(self.timelapse_folder):
            os.makedirs(self.timelapse_folder)
            self.print_with_timestamp(f"Created {self.timelapse_folder}")
        self.timestamp = datetime.now().strftime("%d-%m-%Y")
        self.job_number = 1
        while os.path.exists(f"{self.timelapse_folder}/timelapse_{self.timestamp}_Job{self.job_number}") or os.path.exists(f"{self.timelapse_folder}/timelapse_{self.timestamp}_Job{self.job_number}.zip"):
            self.job_number += 1
        self.new_folder = f"{self.timelapse_folder}/timelapse_{self.timestamp}_Job{self.job_number}"
        os.makedirs(self.new_folder)
        self.print_with_timestamp(f"Created {self.new_folder}")
        self.button = Button(21)
        self.triggers_to_ignore = self.ignore
        self.trigger_count = 0
        self.last_active_time = time.time()
        self.button.when_pressed = self.button_pressed
        self.button.when_released = self.button_released
        start_time = time.time()
        try:
            while True:
                if time.time() - self.last_active_time > self.it:
                    self.print_with_timestamp("Inactive for too long. Ending the script...")
                    break
        except KeyboardInterrupt:
            self.print_with_timestamp("\nInterrupted by user.")
        end_time = time.time()
        runtime = end_time - start_time
        if not self.nozip:
            with zipfile.ZipFile(f"{self.new_folder}.zip", 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(self.new_folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, arcname=os.path.relpath(file_path, start=self.timelapse_folder))
            self.print_with_timestamp(f"\nZipped the contents of {self.new_folder}.")
        if not self.nodel and not self.nozip:
            shutil.rmtree(self.new_folder)
            self.print_with_timestamp(f"The original folder {self.new_folder} has been deleted.")
        self.print_with_timestamp(f"\nExiting... The script ran for {runtime} seconds.")
        self.button.close()

__plugin_name__ = "Sla_timelapse Plugin"
__plugin_pythoncompat__ = ">=3,<4"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = Sla_timelapsePlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
