
import { WebsocketProvider } from "y-websocket";
import * as Y from 'yjs';

export default class Connection {
    public doc: Y.Doc;
    public provider: WebsocketProvider;

    constructor(wspath: string, room: string) {
        this.doc = new Y.Doc();
        this.provider = new WebsocketProvider(wspath, room, this.doc);
        this.provider.awareness.setLocalStateField("user", {
            name: "testuer",
            color: "blue",
        });
    }

    destroy() {
        this.provider.destroy();
        this.doc.destroy();
    }
}
