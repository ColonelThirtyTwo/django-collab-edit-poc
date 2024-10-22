import { WebsocketProvider } from "y-websocket";
import * as Y from "yjs";

export default class Connection {
  public doc: Y.Doc;
  public provider: WebsocketProvider;

  constructor(wspath: string, room: string, username: string) {
    this.doc = new Y.Doc();
    this.provider = new WebsocketProvider(wspath, room, this.doc);
    this.provider.awareness.setLocalStateField("user", {
      name: username,
      color: hsv_to_rgb(
        (this.doc.clientID % 255) / 255.0,
        0.5,
        1.0,
      ),
    });
  }

  destroy() {
    this.provider.destroy();
    this.doc.destroy();
  }
}

function hsv_to_rgb(h: number, s: number, v: number) {
  const i = Math.floor(h * 6);
  const f = h * 6 - i;
  const p = v * (1 - s);
  const q = v * (1 - f * s);
  const t = v * (1 - (1 - f) * s);

  let r,g,b;
  switch (i % 6) {
      case 0: r = v, g = t, b = p; break;
      case 1: r = q, g = v, b = p; break;
      case 2: r = p, g = v, b = t; break;
      case 3: r = p, g = q, b = v; break;
      case 4: r = t, g = p, b = v; break;
      case 5: r = v, g = p, b = q; break;
  }

  const to_hex = (n: number) => {
    var str = Math.round(n * 255).toString(16);
    return str.length == 1 ? "0" + str : str;
  }

  return `#${to_hex(r!)}${to_hex(g!)}${to_hex(b!)}`
}
