import "quill/dist/quill.core.css";
import "quill/dist/quill.snow.css";
import Quill from 'quill';
import QuillCursors from "quill-cursors";
import Connection from "../connection.ts";
import { QuillBinding } from "y-quill";
import * as Y from 'yjs';

Quill.register("modules/cursors", QuillCursors);

export function editor(el: HTMLElement, conn: Connection, key: string, typ: "single-line" | "area") {
    const quill = new Quill(el, {
        formats: [],
        modules: {
            toolbar: typ === "area" ? [
                [{ header: [1, 2, false] }],
                ['bold', 'italic', 'underline'],
                ['image', 'code-block'],
            ] : null,
            history: {
                userOnly: true,
            },
        },
        placeholder: "Put text here!",
        theme: "snow",
    });
    const _binding = new QuillBinding(
        conn.doc.get(key, Y.Text),
        quill,
        conn.provider.awareness,
    );
}
