
import Connection from "./connection.ts";
import { quillSingleLineEditor, quillAreaEditor } from "./quill.ts";
import { slateSingleLineEditor, slateAreaEditor } from "./slate.tsx";

(window as any).pocConnection = Connection;
(window as any).quillSingleLineEditor = quillSingleLineEditor;
(window as any).quillAreaEditor = quillAreaEditor;
(window as any).slateSingleLineEditor = slateSingleLineEditor;
(window as any).slateAreaEditor = slateAreaEditor;
