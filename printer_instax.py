import os
import subprocess


class InstaxPrinter:
    def __init__(self, command_template=None, mode=None, device_name=None):
        env_template = os.environ.get("INSTAX_PRINT_CMD")
        env_mode = os.environ.get("INSTAX_MODE")
        env_device = os.environ.get("INSTAX_DEVICE_NAME")
        env_address = os.environ.get("INSTAX_DEVICE_ADDRESS")
        self.command_template = command_template or env_template
        self.mode = mode or env_mode or ("ble" if env_device else "cmd")
        self.device_name = device_name or env_device
        self.device_address = env_address

    def print_image(self, image_path):
        if self.mode == "ble":
            if not self.device_name and not self.device_address:
                return False, "Set INSTAX_DEVICE_NAME or INSTAX_DEVICE_ADDRESS for BLE printing."
            try:
                from instax_ble_printer import print_image as ble_print

                ble_print(
                    image_path,
                    device_name=self.device_name,
                    device_address=self.device_address,
                )
            except Exception as exc:
                return False, f"BLE print failed: {exc}"
            return True, "Print job sent over BLE."

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
