import shutil
import time
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

import cv2
import numpy as np
from PIL import Image, ImageTk

from camera import Camera
from collage import make_collage
from printer_instax import InstaxPrinter


class PhotoBoothApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pi Photo Booth")
        self.root.geometry("980x760")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.camera = Camera()
        self.camera.open()
        self.printer = InstaxPrinter(
            mode="ble", device_address="FA:AB:BC:87:88:26"
        )

        self.session_dir = self._new_session_dir()
        self.latest_path = Path("sessions") / "latest.jpg"
        self.captured_paths = []
        self.collage_path = None
        self.preview_mode = "live"
        self.flash_until = 0.0
        self.last_frame = None
        self.preview_image = None

        self.status_var = tk.StringVar(value="Ready")

        self.preview_label = ttk.Label(self.root)
        self.preview_label.pack(padx=16, pady=16)

        controls = ttk.Frame(self.root)
        controls.pack(fill="x", padx=16)

        self.capture_button = ttk.Button(
            controls, text="Capture", command=self.start_capture
        )
        self.capture_button.pack(side="left")

        self.print_button = ttk.Button(
            controls, text="Print", command=self.print_collage, state="disabled"
        )
        self.print_button.pack(side="left", padx=8)

        self.reset_button = ttk.Button(controls, text="Reset", command=self.reset_session)
        self.reset_button.pack(side="left")

        status_label = ttk.Label(self.root, textvariable=self.status_var)
        status_label.pack(fill="x", padx=16, pady=(8, 16))

        self.root.after(0, self.update_preview)

    def _new_session_dir(self):
        base = Path("sessions")
        base.mkdir(parents=True, exist_ok=True)
        session = base / datetime.now().strftime("%Y%m%d_%H%M%S")
        session.mkdir(parents=True, exist_ok=True)
        return session

    def update_preview(self):
        if self.preview_mode == "live":
            frame = self.camera.read_frame()
            if frame is not None:
                self.last_frame = frame
                if time.monotonic() < self.flash_until:
                    white = np.full_like(frame, 255)
                    self._show_frame(white)
                else:
                    self._show_frame(frame)

        self.root.after(30, self.update_preview)

    def _show_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        self._show_pil_image(image)

    def _show_pil_image(self, image):
        display_size = (920, 600)
        image = image.resize(display_size, Image.LANCZOS)
        self.preview_image = ImageTk.PhotoImage(image)
        self.preview_label.configure(image=self.preview_image)

    def start_capture(self):
        if len(self.captured_paths) >= 4:
            return

        self.capture_button.configure(state="disabled")
        self.status_var.set("Flashing...")
        self.flash_until = time.monotonic() + 0.45
        self.root.after(500, self.finish_capture)

    def finish_capture(self):
        frame = self.camera.capture_frame()
        if frame is None:
            self.status_var.set("Capture failed")
            self.capture_button.configure(state="normal")
            return

        index = len(self.captured_paths) + 1
        filename = f"photo_{index:02d}.jpg"
        path = self.session_dir / filename
        cv2.imwrite(str(path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        self.captured_paths.append(path)
        self._update_latest(path)

        if len(self.captured_paths) == 4:
            self.build_collage()
        else:
            self.status_var.set(f"Captured {len(self.captured_paths)}/4")
            self.capture_button.configure(state="normal")

    def build_collage(self):
        output_path = self.session_dir / "collage.jpg"
        make_collage([str(p) for p in self.captured_paths], str(output_path))
        self.collage_path = output_path
        self._update_latest(output_path)
        self.preview_mode = "image"
        image = Image.open(output_path)
        self._show_pil_image(image)
        self.print_button.configure(state="normal")
        self.status_var.set("Collage ready")

    def _update_latest(self, image_path):
        try:
            self.latest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(image_path, self.latest_path)
        except OSError:
            pass

    def print_collage(self):
        if not self.collage_path:
            return

        ok, message = self.printer.print_image(str(self.collage_path))
        if ok:
            messagebox.showinfo("Print", message)
        else:
            messagebox.showwarning("Print", message)

    def reset_session(self):
        self.session_dir = self._new_session_dir()
        self.captured_paths = []
        self.collage_path = None
        self.preview_mode = "live"
        self.print_button.configure(state="disabled")
        self.capture_button.configure(state="normal")
        self.status_var.set("Ready")

    def on_close(self):
        self.camera.release()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = PhotoBoothApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
