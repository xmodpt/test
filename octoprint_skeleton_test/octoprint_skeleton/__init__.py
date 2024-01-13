# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin

class SkeletonPlugin(octoprint.plugin.StartupPlugin,
                     octoprint.plugin.SettingsPlugin,
                     octoprint.plugin.AssetPlugin,
                     octoprint.plugin.TemplatePlugin):


    
def
 
__init__(self):
        super().__init__()

        self.pump_state = False

    def on_after_startup(self):
        self.plugin_manager.register_link(
            name="Pump: Activated",
            url="plugins/skeleton/pump",
            category="System Tools",
            visible=False
        )

    def on_click(self, url):
        if self.pump_state is True:
            self.pump_state = False
            self.printer.commands.print("Pump: Off\n")
        else:
            self.pump_state = True
            self.printer.commands.print("Pump: On\n")

        self.update_button()

    def update_button(self):
        if self.pump_state is True:
            label = "Pump: Activated"
        else:
            label = "Pump: Off"

        self.plugin_manager.update_links([
            {
                "url": "plugins/skeleton/pump",
                "name": label,
                "visible": True
            }
        ])

    def get_settings_defaults(self):
        return {
            "pump_state": False
        }

    def get_settings(self):
        settings = super().get_settings()
        settings.update({
            "pump_state": self.pump_state
        })
        return settings

    def set_settings(self, settings):
        self.pump_state = settings["pump_state"]
        self.update_button()

    def get_assets(self):
        return {
            "js": ["js/skeleton.js"],
            "css": ["css/skeleton.css"],
            "less": ["less/skeleton.less"]
        }

    def get_template_configs(self):
        return [
            {
                "type": "generic",
                "template": "hello_world.jinja2",
                "custom_bindings": False
            }
        ]

    def get_update_information(self):
        return {
            "skeleton": {
                "displayName": "Skeleton Plugin",
                "displayVersion": self._plugin_version,

                "type": "github_release",
                "user": "you",
                "repo": "OctoPrint-Skeleton",
                "current": self._plugin_version,

                "pip": "https://github.com/you/OctoPrint-Skeleton/archive/{target_version}.zip",
            }
        }

__plugin_name__ = "Skeleton Plugin"
__plugin_pythoncompat__ = ">=3.7,<4"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = SkeletonPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }