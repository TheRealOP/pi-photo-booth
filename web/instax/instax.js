import { INSTAX_OPCODES } from "./instax.events.js";
import { InstaxBluetooth } from "./instax.bluetooth.js";
import { parse } from "./instax.parser.js";
import { encodeColor } from "./instax.color.js";
import { InstaxFilmVariant } from "./instax.types.js";

export class InstaxPrinter extends InstaxBluetooth {
  _printableHex(command) {
    return Array.from(command, (byte) => byte.toString(16).padStart(2, "0")).join(
      " "
    );
  }

  async setColor(colors, speed = 20, repeat = 0, when = 0) {
    await this.sendCommand(
      INSTAX_OPCODES.LED_PATTERN_SETTINGS,
      encodeColor(colors, speed, repeat, when),
      false
    );
  }

  async sendCommand(opCode, command, awaitResponse = true) {
    const instaxCommandData = this.encode(opCode, command);
    console.log(">", this._printableHex(instaxCommandData));
    const response = await this.send(instaxCommandData, awaitResponse);
    return this._decode(response);
  }

  async getInformation(includeType = false) {
    const printerStatus = {
      battery: {
        charging: false,
        level: null,
      },
      polaroidCount: null,
      type: null,
    };

    let response = null;

    if (includeType === true) {
      response = await this.sendCommand(INSTAX_OPCODES.SUPPORT_FUNCTION_INFO, [0]);
      const width = parseInt(
        String(
          response.width !== 600 &&
            response.width !== 800 &&
            response.width !== 1260
            ? 800
            : response.width
        ),
        10
      );
      const height = parseInt(
        String(response.height !== 800 && response.height !== 840 ? 800 : response.height),
        10
      );

      if (width === 1260 && height === 840) {
        printerStatus.type = InstaxFilmVariant.WIDE;
      } else if (width === 800) {
        printerStatus.type = InstaxFilmVariant.SQUARE;
      } else if (width === 600) {
        printerStatus.type = InstaxFilmVariant.MINI;
      }
    }

    response = await this.sendCommand(INSTAX_OPCODES.SUPPORT_FUNCTION_INFO, [1]);
    printerStatus.battery.charging = response.isCharging > 5;
    printerStatus.battery.level = response.battery;

    response = await this.sendCommand(INSTAX_OPCODES.SUPPORT_FUNCTION_INFO, [2]);
    printerStatus.polaroidCount = response.photosLeft;
    return printerStatus;
  }

  async printImage(printCount = 1, callback, signal) {
    await new Promise((resolve) => setTimeout(resolve, 500));
    let aborted = false;
    signal.addEventListener("abort", () => {
      aborted = true;
    });

    for (let index = 0; index < printCount; index += 1) {
      await this.sendCommand(INSTAX_OPCODES.PRINT_IMAGE, [], true);
      await new Promise((resolve) => setTimeout(resolve, 15000));

      if (aborted) {
        callback(-1);
      } else {
        callback(index + 1);
      }
    }
  }

  async sendImage(imageUrl, print = false, type, callback, signal) {
    const imageData = await this._base64ToByteArray(imageUrl);
    const chunks = this.imageToChunks(
      imageData,
      type === InstaxFilmVariant.SQUARE ? 1808 : 900
    );

    let isSendingImage = true;
    let printTimeout = 15;
    let abortedPrinting = false;

    signal.addEventListener("abort", () => {
      isSendingImage = false;
      abortedPrinting = true;
    });

    while (isSendingImage && !abortedPrinting) {
      try {
        const imageDataLength = imageData.length;
        const uint16Array = new Uint16Array([imageDataLength]);
        const dataView = new DataView(uint16Array.buffer);
        const bigEndianValue = dataView.getUint16(0, false);
        const bigEndianBytes = new Uint8Array(
          new Uint16Array([bigEndianValue]).buffer
        );

        const response = await this.sendCommand(
          INSTAX_OPCODES.PRINT_IMAGE_DOWNLOAD_START,
          [0x02, 0x00, 0x00, 0x00, 0x00, 0x00, ...Array.from(bigEndianBytes)]
        );

        if (!response || response.status !== 0) throw new Error("start-failed");

        for (let packetId = 0; packetId < chunks.length; packetId += 1) {
          if (!isSendingImage) {
            await new Promise((resolve) => setTimeout(resolve, 500));
            await this.sendCommand(
              INSTAX_OPCODES.PRINT_IMAGE_DOWNLOAD_CANCEL,
              [],
              false
            );
            callback(-1);
            break;
          }

          const chunk = this.encode(
            INSTAX_OPCODES.PRINT_IMAGE_DOWNLOAD_DATA,
            Array.from(chunks[packetId])
          );

          for (let index = 0; index < chunks[packetId].length + 7; index += 182) {
            const isPacketEnd = index > chunks[packetId].length + 7 - 182;
            const splitChunk = chunk.slice(index, index + 182);
            const responseEvent = await this.send(splitChunk, isPacketEnd);

            if (isPacketEnd) {
              const decoded = this._decode(responseEvent);
              if (!decoded) throw new Error("packet-failed");
            }

            callback(
              (packetId * chunks[packetId].length + index) /
                (chunks[packetId].length * chunks.length)
            );

            await new Promise((resolve) => setTimeout(resolve, printTimeout));
          }
        }

        if (!abortedPrinting) {
          await this.sendCommand(INSTAX_OPCODES.PRINT_IMAGE_DOWNLOAD_END, [], true);
          callback(print ? 1 : -1);
        }

        isSendingImage = false;
      } catch (error) {
        printTimeout += 25;

        let resp = await this.sendCommand(
          INSTAX_OPCODES.PRINT_IMAGE_DOWNLOAD_CANCEL,
          [],
          true
        );
        if (resp && resp.status !== 0) {
          resp = await this.sendCommand(
            INSTAX_OPCODES.PRINT_IMAGE_DOWNLOAD_CANCEL,
            [],
            true
          );
        }

        if (printTimeout > 200) {
          isSendingImage = false;
          throw new Error("send-timeout");
        }
      }
    }
  }

  async _base64ToByteArray(base64) {
    const cleaned = String(base64).replace(/^data:image\/(png|jpeg);base64,/, "");
    const binary = atob(cleaned);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes;
  }

  createImageDataChunk(index, chunk) {
    const indexArray = new Uint32Array([index]);
    const indexBytes = new Uint8Array(indexArray.buffer);
    const combined = new Uint8Array(4 + chunk.length);

    for (let i = 0; i < 4; i += 1) {
      combined[i] = indexBytes[3 - i];
    }

    combined.set(chunk, 4);
    return combined;
  }

  imageToChunks(imgData, chunkSize = 900) {
    const imgDataChunks = [];

    for (let i = 0; i < imgData.length; i += chunkSize) {
      const chunk = imgData.slice(i, i + chunkSize);
      imgDataChunks.push(chunk);
    }

    if (imgDataChunks[imgDataChunks.length - 1].length < chunkSize) {
      const lastChunk = imgDataChunks[imgDataChunks.length - 1];
      const padding = new Uint8Array(chunkSize - lastChunk.length);
      imgDataChunks[imgDataChunks.length - 1] = new Uint8Array([
        ...lastChunk,
        ...padding,
      ]);
    }

    for (let i = 0; i < imgDataChunks.length; i += 1) {
      imgDataChunks[i] = this.createImageDataChunk(i, imgDataChunks[i]);
    }

    return imgDataChunks;
  }

  _decode(event) {
    if (!event || !event.target) return null;
    const packet = Array.from(new Uint8Array(event.target.value.buffer));
    const packetLength = (packet[2] << 8) | packet[3];
    const packetChecksum = packet.reduce((acc, val) => acc + val, 0) & 255;

    if (packetLength !== packet.length || packetChecksum !== 255) {
      throw new Error("Invalid packet");
    }

    if (packet[0] !== 0x61 || packet[1] !== 0x42) {
      throw new Error("Invalid header");
    }

    console.log(">", this._printableHex(new Uint8Array(packet)));

    const opCode = (packet[4] << 8) | packet[5];
    const status = packet[6];
    const command = packet[7];
    const payload = packet.slice(8, packet.length - 1);

    return parse(opCode, command, payload, status);
  }

  encode(opcode, payload) {
    const length = payload.length + 7;
    const commandPacket = [
      0x41,
      0x62,
      (length >> 8) & 0xff,
      length & 0xff,
      opcode >> 8,
      opcode & 0xff,
      ...payload,
    ];

    const checksum = commandPacket.reduce((acc, val) => acc + val, 0) & 0xff;
    return new Uint8Array([...commandPacket, checksum ^ 0xff]);
  }
}
