# pi-photo-booth
This is a little photobooth app that runs on the raspberry pi!

## Run the MVP
1. Install dependencies: `pip install -r requirements.txt`
2. Launch the app: `python app.py`

Captured photos and collages are saved under `sessions/`.

## Printing stub
Set `INSTAX_PRINT_CMD` to a command template that accepts `{image}` to enable printing.
Example: `INSTAX_PRINT_CMD='bluetooth-instax --print {image}'`

## Instax Mini Link 3 kiosk printing
This project includes a local web kiosk page that uses Web Bluetooth and Instax Link Web logic to print the latest captured photo.

### Install (Raspberry Pi OS)
1. `sudo apt update`
2. `sudo apt install -y python3 python3-venv chromium bluetooth bluez`
3. `python3 -m venv env`
4. `source env/bin/activate`
5. `pip install -r requirements.txt`

### Run
1. Start the photo booth capture app: `python app.py`
2. Start the kiosk web server: `python server.py`
3. Open the kiosk UI at `http://localhost:3000`

The kiosk always loads the latest image from `sessions/latest.jpg`.

### Chromium kiosk command
```
chromium --kiosk --app=http://localhost:3000 --enable-web-bluetooth --enable-experimental-web-platform-features --noerrdialogs --disable-pinch
```

## Native BLE printing (no browser)
If Web Bluetooth is unreliable, you can print directly over BLE with `bleak`.

Install dependencies (already in `requirements.txt`) and run:
```
python instax_ble_print.py --device-name INSTAX-XXXX --image sessions/latest.jpg
```

To use BLE printing from the app, set:
```
export INSTAX_MODE=ble
export INSTAX_DEVICE_NAME=INSTAX-XXXX
```

### Optional autostart (systemd)
Create `~/.config/systemd/user/pi-photo-booth.service`:
```
[Unit]
Description=Pi Photo Booth (capture + kiosk)

[Service]
WorkingDirectory=/home/pi/pi-photo-booth
ExecStart=/bin/bash -c "source env/bin/activate && python app.py"
Restart=on-failure

[Install]
WantedBy=default.target
```

Create `~/.config/systemd/user/pi-photo-booth-kiosk.service`:
```
[Unit]
Description=Pi Photo Booth Kiosk Server

[Service]
WorkingDirectory=/home/pi/pi-photo-booth
ExecStart=/bin/bash -c "source env/bin/activate && python server.py"
Restart=on-failure

[Install]
WantedBy=default.target
```

Enable and start:
```
systemctl --user daemon-reload
systemctl --user enable pi-photo-booth.service pi-photo-booth-kiosk.service
systemctl --user start pi-photo-booth.service pi-photo-booth-kiosk.service
```
