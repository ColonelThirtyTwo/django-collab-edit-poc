import { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { createEditor, Editor, Transforms } from "slate";
import { Slate, withReact, Editable } from "slate-react";
import { withYjs, YjsEditor } from "@slate-yjs/core";
import * as Y from "yjs";
import Connection from "../connection.ts";

const initial = [{ type: "paragraph", children: [{ text: "" }] }];

const MyEditor = (props: { connection: Connection; docKey: string }) => {
  const [connected, setConnected] = useState(false);
  useEffect(() => {
    props.connection.provider.on("sync", setConnected);
    return () => {
      props.connection.provider.off("sync", setConnected);
    };
  }, [props.connection, setConnected]);

  const docObj = useMemo(
    () => props.connection.doc.get(props.docKey, Y.XmlText),
    [props.connection, props.docKey],
  );

  if (!connected) {
    return <div>Loading...</div>;
  }

  return <MyEditorInner docObj={docObj} />;
};

const MyEditorInner = (props: { docObj: Y.XmlText }) => {
  const editor = useMemo(() => {
    const e = withReact(withYjs(createEditor(), props.docObj));
    const normalizeNode = e.normalizeNode;
    e.normalizeNode = (entry: any) => {
      const [node] = entry;
      if (!Editor.isEditor(node) || node.children.length > 0)
        return normalizeNode(entry);
      Transforms.insertNodes(editor, initial, { at: [0] });
    };
    return e;
  }, [props.docObj]);

  useEffect(() => {
    YjsEditor.connect(editor);
    return () => YjsEditor.disconnect(editor);
  }, [editor]);

  return (
    <Slate editor={editor} initialValue={initial}>
      <Editable />
    </Slate>
  );
};

export function slateSingleLineEditor(
  el: HTMLElement,
  conn: Connection,
  key: string,
) {
  const root = createRoot(el);
  root.render(<MyEditor connection={conn} docKey={key} />);
}

export function slateAreaEditor(
  el: HTMLElement,
  conn: Connection,
  key: string,
) {
  const root = createRoot(el);
  root.render(<MyEditor connection={conn} docKey={key} />);
}
