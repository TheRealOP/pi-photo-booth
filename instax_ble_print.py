import argparse

from instax_ble_printer import print_image


def main():
    parser = argparse.ArgumentParser(description="Print to Instax Mini Link over BLE")
    parser.add_argument("--device-name", help="Printer name, e.g. INSTAX-XXXX")
    parser.add_argument("--device-address", help="BLE address, e.g. AA:BB:CC:DD:EE:FF")
    parser.add_argument("--image", required=True, help="Path to JPEG image")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    if not args.device_name and not args.device_address:
        raise SystemExit("Provide --device-name or --device-address")

    print_image(
        args.image,
        device_name=args.device_name,
        device_address=args.device_address,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
