import {
  INSTAX_PRINTER_NAME_PREFIX,
  INSTAX_PRINTER_SERVICES,
} from "./instax.config.js";

export class InstaxBluetooth {
  constructor() {
    this._characteristicRef = {
      server: null,
      notify: null,
      write: null,
    };
    this.isBusy = false;
  }

  async disconnect() {
    try {
      if (this._characteristicRef.notify) {
        await this._characteristicRef.notify.stopNotifications();
      }
      if (this._characteristicRef.server) {
        this._characteristicRef.server.disconnect();
      }
    } catch (error) {
      console.error("> error on manual disconnect: ",
        error
      );
    }
  }

  async send(command, response = true) {
    if (this.isBusy) return;
    this.isBusy = true;

    let timeout = null;
    let notificationHandle = null;
    let notificationPromise = null;
    let timeoutPromise = null;

    if (response === true) {
      notificationHandle = await this._characteristicRef.notify.startNotifications();

      notificationPromise = new Promise((resolve) => {
        notificationHandle.addEventListener(
          "characteristicvaluechanged",
          (event) => {
            if (timeout) clearTimeout(timeout);
            resolve(event);
          },
          { once: true }
        );
      });

      timeoutPromise = new Promise((_, reject) => {
        timeout = setTimeout(() => {
          notificationHandle.removeEventListener(
            "characteristicvaluechanged",
            () => {}
          );
          reject(new Error("Notification timeout"));
        }, 500);
      });
    }

    await this._characteristicRef.write.writeValueWithoutResponse(command);
    this.isBusy = false;

    if (response !== true) return;

    try {
      const event = await Promise.race([notificationPromise, timeoutPromise]);
      return event || null;
    } finally {
      if (timeout) clearTimeout(timeout);
      if (notificationHandle) {
        await notificationHandle.stopNotifications();
      }
    }
  }

  async connect() {
    try {
      let deviceHandle = null;
      const connected = await navigator.bluetooth
        .requestDevice({
          filters: [
            {
              namePrefix: INSTAX_PRINTER_NAME_PREFIX,
            },
          ],
          optionalServices: INSTAX_PRINTER_SERVICES,
        })
        .then((device) => {
          deviceHandle = device;
          device.addEventListener("gattserverdisconnected", () => {
            this._characteristicRef.write = null;
            this._characteristicRef.notify = null;
          });
          return device.gatt.connect();
        })
        .then((server) => {
          this._characteristicRef.server = server;
          return server.getPrimaryService(INSTAX_PRINTER_SERVICES[0]);
        })
        .then((service) => service.getCharacteristics())
        .then((characteristics) => {
          if (!characteristics) throw new Error("invalid-characteristic");

          const writeCharacteristic = characteristics.reduce((a, b) =>
            a.properties.write && a.properties.writeWithoutResponse ? a : b
          );
          const notificationsCharacteristic = characteristics.reduce((a, b) =>
            a.properties.notify ? a : b
          );

          if (
            !notificationsCharacteristic ||
            !notificationsCharacteristic.properties.notify ||
            !writeCharacteristic ||
            !writeCharacteristic.properties.write
          ) {
            throw new Error("missing-characteristics");
          }

          this._characteristicRef.notify = notificationsCharacteristic;
          this._characteristicRef.write = writeCharacteristic;

          console.log("> PRINTER CONNECTED");
          return true;
        });

      if (connected === true) return deviceHandle;
      throw new Error("connect-failed");
    } catch (error) {
      this._characteristicRef.notify = null;
      this._characteristicRef.write = null;
      return false;
    }
  }
}
