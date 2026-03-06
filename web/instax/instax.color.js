export function encodeColor(colorArray, speed, repeat, when) {
  const colorsBGR = colorArray.map((color) => convertHexColor(color));
  const payloadSize = 4 + colorsBGR.length * 3;
  const payload = new Uint8Array(payloadSize);

  payload.set([when, colorsBGR.length, speed, repeat]);

  colorsBGR.flat().forEach((value, index) => {
    payload[index + 4] = value;
  });

  return Array.from(payload);
}

function convertHexColor(hex) {
  let value = hex.replace(/^#/, "");

  if (value.length === 3) {
    value = value
      .split("")
      .map((char) => char.repeat(2))
      .join("");
  }

  const rgb = parseInt(value, 16);
  const red = (rgb >> 16) & 255;
  const green = (rgb >> 8) & 255;
  const blue = rgb & 255;

  return [blue, green, red];
}
