import argparse

from instax_ble_printer import print_image


def main():
    parser = argparse.ArgumentParser(description="Print to Instax Mini Link over BLE")
    parser.add_argument("--device-name", required=True, help="Printer name, e.g. INSTAX-XXXX")
    parser.add_argument("--image", required=True, help="Path to JPEG image")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    print_image(args.image, args.device_name, debug=args.debug)


if __name__ == "__main__":
    main()
