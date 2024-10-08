
import Connection from "./connection.ts";
import { editor } from "./editors/tiptap.tsx";
import { nonCollabText } from "./non_collab_fields.ts";

type EditorFunc = (el: HTMLElement, conn: Connection, key: string) => void;

editor satisfies EditorFunc;

(window as any).pocConnection = Connection;
(window as any).pocEditor = editor;
(window as any).pocNonCollabText = nonCollabText;
