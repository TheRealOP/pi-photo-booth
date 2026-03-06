import asyncio
import io
import math
from dataclasses import dataclass
from enum import Enum

from PIL import Image, ImageOps
from bleak import BleakClient, BleakScanner


class SID(Enum):
    SUPPORT_FUNCTION_INFO = (0, 2)
    PRINT_IMAGE_DOWNLOAD_START = (16, 0)
    PRINT_IMAGE_DOWNLOAD_DATA = (16, 1)
    PRINT_IMAGE_DOWNLOAD_END = (16, 2)
    PRINT_IMAGE_DOWNLOAD_CANCEL = (16, 3)
    PRINT_IMAGE = (16, 128)


class ResultCode(Enum):
    OK = 0
    PRINTER_PROCESSING = 127
    UNKNOWN = -1


class SupportFunctionInfoType(Enum):
    IMAGE_SUPPORT_INFO = 0
    PRINTER_FUNCTION_INFO = 2


@dataclass
class ImageSupportInfo:
    width: int
    height: int
    pic_type: int
    pic_option: int
    max_size: int


class OutboundMessage:
    def __init__(self, sid, data):
        self.signature = b"\x41\x62"
        self.sid = sid
        self.data = data
        self.size = 7 + len(data)
        self.checksum = self._checksum()

    def _checksum(self):
        payload = self.get_content()
        return (255 - (sum(payload) & 255)) & 255

    def get_content(self):
        return (
            self.signature
            + self.size.to_bytes(2, "big")
            + bytes([self.sid.value[0], self.sid.value[1]])
            + self.data
        )

    def payload(self):
        return self.get_content() + bytes([self.checksum])


class Response:
    def __init__(self, payload):
        self.signature = payload[0:2]
        self.size = int.from_bytes(payload[2:4], "big")
        self.sid = SID((payload[4], payload[5])) if (payload[4], payload[5]) in [s.value for s in SID] else None
        self.result_code = ResultCode(payload[6]) if payload[6] in [c.value for c in ResultCode] else ResultCode.UNKNOWN
        self.data = payload[7:-1]
        self.checksum = payload[-1]


class InstaxBLEConnection:
    def __init__(self, device_name, debug=False):
        self.device_name = device_name.upper()
        self.debug = debug
        self.client = None
        self.response_event = asyncio.Event()
        self.response_payload = None

        self.service_uuid = "70954782-2d83-473d-9e5f-81e1d02d5273"
        self.write_uuid = "70954783-2d83-473d-9e5f-81e1d02d5273"
        self.notify_uuid = "70954784-2d83-473d-9e5f-81e1d02d5273"

    async def discover(self):
        devices = await BleakScanner.discover(5.0, return_adv=True)
        for device in devices:
            advertisement_data = devices[device][1]
            if (
                advertisement_data.local_name
                and advertisement_data.local_name.upper() == self.device_name
            ):
                return device
        return None

    async def connect(self):
        device = await self.discover()
        if not device:
            raise RuntimeError(f"Instax printer '{self.device_name}' not found")
        self.client = BleakClient(device)
        await self.client.connect()
        await self.client.start_notify(self.notify_uuid, self._response_callback)

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()

    def _response_callback(self, _characteristic, payload):
        if self.debug:
            print("RX", payload.hex(" "))
        self.response_payload = payload
        self.response_event.set()

    async def send_command(self, payload):
        if not self.client:
            raise RuntimeError("Printer is not connected")
        max_packet_size = 182
        number_of_packets = math.ceil(len(payload) / max_packet_size)
        for packet_index in range(number_of_packets):
            packet = payload[
                packet_index * max_packet_size : packet_index * max_packet_size + max_packet_size
            ]
            if self.debug:
                print("TX", packet.hex(" "))
            await self.client.write_gatt_char(self.write_uuid, packet, False)

        self.response_payload = None
        self.response_event.clear()
        try:
            await asyncio.wait_for(self.response_event.wait(), timeout=2.0)
        except asyncio.TimeoutError as exc:
            raise RuntimeError("Printer response timeout") from exc
        return self.response_payload


class InstaxBLEPrinter:
    def __init__(self, device_name, debug=False):
        self.device_name = device_name
        self.debug = debug
        self.connection = InstaxBLEConnection(device_name, debug)
        self.image_support = None

    async def connect(self):
        await self.connection.connect()
        self.image_support = await self._request_image_support()

    async def disconnect(self):
        await self.connection.disconnect()

    async def _request_image_support(self):
        request = OutboundMessage(SID.SUPPORT_FUNCTION_INFO, bytes([SupportFunctionInfoType.IMAGE_SUPPORT_INFO.value]))
        response = await self.connection.send_command(request.payload())
        parsed = Response(response)
        if not parsed.data or len(parsed.data) < 11:
            raise RuntimeError("Failed to read image support info")
        info = parsed.data
        width = int.from_bytes(info[1:3], "big")
        height = int.from_bytes(info[3:5], "big")
        pic_type = info[5]
        pic_option = info[6]
        max_size = int.from_bytes(info[7:11], "big")
        return ImageSupportInfo(width, height, pic_type, pic_option, max_size)

    async def print_image(self, image_path):
        if not self.image_support:
            raise RuntimeError("Printer not connected")

        image_bytes = prepare_image(image_path, self.image_support)

        start_payload = OutboundMessage(
            SID.PRINT_IMAGE_DOWNLOAD_START,
            bytes([2, 0, 0, 0]) + len(image_bytes).to_bytes(4, "big"),
        ).payload()
        response = await self.connection.send_command(start_payload)
        frame_size = int.from_bytes(Response(response).data[0:4], "big")

        frames = slice_image(image_bytes, frame_size)
        for index, frame in enumerate(frames):
            frame_payload = OutboundMessage(
                SID.PRINT_IMAGE_DOWNLOAD_DATA, index.to_bytes(4, "big") + frame
            ).payload()
            await self.connection.send_command(frame_payload)

        await self.connection.send_command(OutboundMessage(SID.PRINT_IMAGE_DOWNLOAD_END, b"").payload())
        await self.connection.send_command(OutboundMessage(SID.PRINT_IMAGE, b"").payload())


def prepare_image(image_path, image_support):
    image = Image.open(image_path).convert("RGB")
    target = (image_support.width, image_support.height)
    image = ImageOps.fit(image, target, Image.LANCZOS)

    quality = 95
    while True:
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality)
        data = buffer.getvalue()
        if len(data) <= image_support.max_size or quality <= 60:
            return data
        quality -= 5


def slice_image(image_bytes, frame_size):
    frames = []
    for i in range(0, len(image_bytes), frame_size):
        frame = image_bytes[i : i + frame_size]
        if len(frame) < frame_size:
            frame += b"\x00" * (frame_size - len(frame))
        frames.append(frame)
    return frames


def print_image(image_path, device_name, debug=False):
    async def runner():
        printer = InstaxBLEPrinter(device_name, debug)
        await printer.connect()
        await printer.print_image(image_path)
        await printer.disconnect()

    asyncio.run(runner())
