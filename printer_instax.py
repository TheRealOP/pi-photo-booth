import os
import subprocess


class InstaxPrinter:
    def __init__(self, command_template=None):
        env_template = os.environ.get("INSTAX_PRINT_CMD")
        self.command_template = command_template or env_template

    def print_image(self, image_path):
        if not self.command_template:
            return False, (
                "Set INSTAX_PRINT_CMD or pass command_template to enable printing. "
                "Example: 'bluetooth-instax --print {image}'."
            )

        command = self.command_template.format(image=image_path)
        try:
            subprocess.run(command, shell=True, check=True)
        except subprocess.CalledProcessError as exc:
            return False, f"Print command failed: {exc}"

        return True, "Print job sent."
