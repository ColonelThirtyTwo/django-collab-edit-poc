import "quill/dist/quill.core.css";
import "quill/dist/quill.snow.css";
import Quill from 'quill';
import QuillCursors from "quill-cursors";
import Connection from "./connection.ts";
import { QuillBinding } from "y-quill";
import * as Y from 'yjs';

Quill.register("modules/cursors", QuillCursors);

export function quillSingleLineEditor(el: HTMLElement, conn: Connection, key: string) {
    const quill = new Quill(el, {
        debug: "info",
        formats: [],
        modules: {
            toolbar: null,
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

export function quillAreaEditor(el: HTMLElement, conn: Connection, key: string) {
    const quill = new Quill(el, {
        debug: "info",
        modules: {
            toolbar: [
                [{ header: [1, 2, false] }],
                ['bold', 'italic', 'underline'],
                ['image', 'code-block'],
            ],
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
};

