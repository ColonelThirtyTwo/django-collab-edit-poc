import { ySyncPlugin, yUndoPlugin, yCursorPlugin, undo, redo, initProseMirrorDoc } from 'y-prosemirror'
import {schema} from "prosemirror-schema-basic";
import {EditorState} from "prosemirror-state";
import {EditorView} from "prosemirror-view";
import { keymap } from 'prosemirror-keymap';
import * as Y from 'yjs';
import { exampleSetup } from 'prosemirror-example-setup';
import Connection from '../connection.ts';

import "../node_modules/prosemirror-view/style/prosemirror.css";
import "../node_modules/prosemirror-example-setup/style/style.css";
import "../node_modules/prosemirror-menu/style/menu.css";
import "./prosemirror.scss";

const textAreaSchema = schema;

export function editor(el: HTMLElement, conn: Connection, key: string) {
    el.innerHTML = "";
    const schema = textAreaSchema;
    const item = conn.doc.get(key, Y.XmlFragment);
    const { doc, mapping } = initProseMirrorDoc(item, schema);
    const plugins = [
        ySyncPlugin(item, { mapping }),
        yCursorPlugin(conn.provider.awareness),
        yUndoPlugin(),
        keymap({
            "Mod-z": undo,
            "Mod-y": redo,
            "Mod-Shift-z": redo,
        }),
    ].concat(exampleSetup({
        schema,
        menuBar: true,
    }));

    const state = EditorState.create({
        doc,
        schema,
        plugins,
    });
    const _view = new EditorView(el, {
        state,
    });
}
