import { InstaxPrinter } from "./instax/instax.js";
import { InstaxFilmVariant } from "./instax/instax.types.js";

const connectButton = document.getElementById("connect-btn");
const printButton = document.getElementById("print-btn");
const statusLabel = document.getElementById("status");
const progressLabel = document.getElementById("progress");
const latestImage = document.getElementById("latest-image");
const placeholder = document.getElementById("placeholder");

let printer = null;
let filmType = InstaxFilmVariant.MINI;
let isPrinting = false;

function setStatus(message) {
  statusLabel.textContent = message;
}

function setProgress(message) {
  progressLabel.textContent = message;
}

async function connectPrinter() {
  if (!navigator.bluetooth) {
    setStatus("Web Bluetooth is not available in this browser.");
    return;
  }

  connectButton.disabled = true;
  setStatus("Connecting to printer...");

  try {
    printer = new InstaxPrinter();
    const device = await printer.connect();
    if (!device) {
      setStatus("Printer connection cancelled.");
      connectButton.disabled = false;
      return;
    }

    setStatus("Printer connected.");
    device.addEventListener("gattserverdisconnected", () => {
      printer = null;
      printButton.disabled = true;
      connectButton.disabled = false;
      setStatus("Printer disconnected.");
    });

    await new Promise((resolve) => setTimeout(resolve, 200));
    const info = await printer.getInformation(true);
    if (info && info.type) {
      filmType = info.type;
    }

    printButton.disabled = false;
  } catch (error) {
    console.error(error);
    printer = null;
    connectButton.disabled = false;
    setStatus("Failed to connect. Try again.");
  }
}

async function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("Failed to read image"));
    reader.readAsDataURL(blob);
  });
}

async function getLatestImageDataUrl() {
  const response = await fetch(`/latest.jpg?ts=${Date.now()}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("No latest image found");
  }
  const blob = await response.blob();
  return blobToDataUrl(blob);
}

async function printLatest() {
  if (!printer || isPrinting) {
    return;
  }

  isPrinting = true;
  printButton.disabled = true;
  setStatus("Preparing image...");
  setProgress("");

  try {
    const dataUrl = await getLatestImageDataUrl();
    const controller = new AbortController();

    setStatus("Sending image to printer...");
    await printer.sendImage(
      dataUrl,
      true,
      filmType,
      (progress) => {
        if (progress < 0) {
          return;
        }
        setProgress(`Sending: ${Math.round(progress * 100)}%`);
      },
      controller.signal
    );

    setStatus("Printing...");
    await printer.printImage(1, (printed) => {
      if (printed > 0) {
        setProgress(`Printed ${printed}/1`);
      }
    }, controller.signal);

    setStatus("Print complete.");
  } catch (error) {
    console.error(error);
    setStatus("Print failed. Check printer and try again.");
  } finally {
    isPrinting = false;
    printButton.disabled = !printer;
  }
}

function refreshLatestPreview() {
  latestImage.src = `/latest.jpg?ts=${Date.now()}`;
}

latestImage.addEventListener("load", () => {
  latestImage.style.display = "block";
  placeholder.style.display = "none";
});

latestImage.addEventListener("error", () => {
  latestImage.style.display = "none";
  placeholder.style.display = "block";
});

connectButton.addEventListener("click", connectPrinter);
printButton.addEventListener("click", printLatest);

setInterval(refreshLatestPreview, 2000);
refreshLatestPreview();
