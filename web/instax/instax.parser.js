import { INSTAX_OPCODES } from "./instax.events.js";

const twoByteInt = (offset, byteArray) => {
  return byteArray.length < offset + 2
    ? 0
    : (byteArray[offset] << 8) | byteArray[offset + 1];
};

const oneByteInt = (offset, byteArray) => {
  return byteArray.length < offset + 1 ? 0 : byteArray[offset];
};

export function parse(eventCode, command, payload, status) {
  if (eventCode === INSTAX_OPCODES.DEVICE_INFO_SERVICE) {
    const asciiResponse = String.fromCharCode(
      ...payload.filter((code) => code !== 8)
    );
    switch (command) {
      case 0:
        return { company: asciiResponse };
      case 1:
        return { printerTypeId: asciiResponse };
      case 2:
        return { serialNumber: asciiResponse };
      default:
        return { eventCode, command, payload };
    }
  }

  if (eventCode === INSTAX_OPCODES.SUPPORT_FUNCTION_INFO) {
    switch (command) {
      case 0:
        return {
          width: twoByteInt(0, payload),
          height: twoByteInt(2, payload),
          packet: twoByteInt(4, payload),
        };
      case 1:
        return {
          isCharging: oneByteInt(0, payload),
          battery: oneByteInt(1, payload),
        };
      case 2:
        return {
          photosLeft: payload[0] & 15,
          isCharging: (1 << 7) & (payload[0] >= 1),
        };
      default:
        break;
    }
  }

  return { eventCode, command, payload, status };
}
