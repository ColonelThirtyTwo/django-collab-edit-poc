import * as Y from "yjs";
import Connection from "./connection.ts";

export function nonCollabText(
  input: HTMLInputElement,
  conn: Connection,
  key: string,
) {
  input.disabled = false;
  const map = conn.doc.get("non_collab_fields", Y.Map);
  input.value = (map.get(key) as string | null) ?? "";

  // TODO: don't change when focused and editing
  map.observe((ev, _tx) => {
    if (ev.keysChanged.has(key))
      input.value = (map.get(key) as string | null) ?? "";
  });
  input.addEventListener("change", () => {
    map.set(key, input.value);
  });
}

export function nonCollabInteger(
  input: HTMLInputElement,
  conn: Connection,
  key: string,
) {
  input.disabled = false;
  const map = conn.doc.get("non_collab_fields", Y.Map);

  const get = () => {
    let v = map.get(key) as number | undefined | null;
    return v != null ? v.toString() : "";
  };
  input.value = get();

  // TODO: don't change when focused and editing
  map.observe((ev, _tx) => {
    if (ev.keysChanged.has(key))
      input.value = get();
  });
  input.addEventListener("change", () => {
    if(input.value === "") {
      map.set(key, null);
    } else {
      const v = parseInt(input.value);
      if(v === v) {
        map.set(key, v);
      } else {
        input.value = get();
      }
    }
  });
}
