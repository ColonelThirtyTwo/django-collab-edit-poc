import { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { createEditor, Editor, Transforms } from 'slate';
import { Slate, withReact, Editable } from 'slate-react';
import { YjsEditor } from '@slate-yjs/core'
import { YjsPlugin } from '@udecode/plate-yjs/react';
import * as Y from 'yjs';
import Connection from "./connection.ts";
import { usePlateEditor, Plate, PlateContent, createPlateEditor, useEditorPlugin, toPlatePlugin } from '@udecode/plate-common/react';
import { withTYjs } from "@udecode/plate-yjs";
import { WebsocketProvider } from "y-websocket";
import { createTSlatePlugin, PluginConfig } from "@udecode/plate-common";
import React from "react";

// Plate's YJS provider is hardcoded to use Hocuspocus, which we don't use. So reimplement it...

type MyYjsPluginOptions = {
    isConnected: boolean;
    provider: WebsocketProvider,

};

type MyYjsPluginConfig = PluginConfig<'myyjs', MyYjsPluginOptions>;

const BaseMyYjsPlugin = createTSlatePlugin<MyYjsPluginConfig>({
    key: 'myyjs',
    //extendEditor: 
    options: {
        isConnected: false,
        provider: {} as any,
    },
}).extend(({getOptions, setOption}) => {
    const provider = getOptions().provider;
    provider.on("status", ({status}: {status: "disconnected" | "connecting" | "connected"}) => {
        setOption("isConnected", status === "connected");
    });

    return { options: { provider } };
});

const MyYjsAboveEditable: React.FC<{
    children: React.ReactNode
}> = ({children}) => {
    const { editor, useOption } = useEditorPlugin<MyYjsPluginConfig>(BaseMyYjsPlugin);

  const provider = useOption('provider');

  React.useEffect(() => {
    void provider.connect();
    return () => provider.disconnect();
  }, [provider]);

  React.useEffect(() => {
    YjsEditor.connect(editor as any);
    return () => YjsEditor.disconnect(editor as any);
  }, [provider.awareness, provider.doc]);

  if(!useOption("isConnected"))
    return null;

  return <>{children}</>;
}

export const MyYjsPlugin = toPlatePlugin(BaseMyYjsPlugin, {
    render: { aboveEditable: MyYjsAboveEditable },
});

// ^ TODO: this above is mostly a copy of Plate's yjs plugin, but it doesn't actually
// do anything except listen to the connection state. What does the actual listening?

function MyEditor2(props: {connection: Connection, docKey: string}) {
    const editor = useMemo(() => withTYjs(
        // ???
        createPlateEditor({
            plugins: [
                YjsPlugin.configure({
                    
                })
            ]
        }),
        props.connection.doc.get(props.docKey, Y.XmlText),
    ), [props.connection, props.docKey]);
    return <Plate editor={editor}>
        <PlateContent placeholder="Type..." />
    </Plate>;
}

export function plateSingleLineEditor(el: HTMLElement, conn: Connection, key: string) {
    const root = createRoot(el);
    root.render(<MyEditor2 connection={conn} docKey={key} />);
}

export function plateAreaEditor(el: HTMLElement, conn: Connection, key: string) {
    
}
