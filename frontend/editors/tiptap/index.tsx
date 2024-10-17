import { ChainedCommands, Editor, Extensions, getSchema } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import Collaboration from "@tiptap/extension-collaboration";
import CollaborationCursor from "@tiptap/extension-collaboration-cursor";
import { EditorProvider, useCurrentEditor } from "@tiptap/react";
import { createRoot } from "react-dom/client";
import { useMemo } from "react";
import Connection from "../../connection.ts";
import "./tiptap.scss";
import "@szhsin/react-menu/dist/core.css";
import Underline from "@tiptap/extension-underline";
import Link from "@tiptap/extension-link";
import { Menu, MenuButton, MenuDivider, MenuItem } from "@szhsin/react-menu";
import TextAlign from "@tiptap/extension-text-align";
import Table from "@tiptap/extension-table";
import TableCell from "@tiptap/extension-table-cell";
import TableHeader from "@tiptap/extension-table-header";
import TableRow from "@tiptap/extension-table-row";
import PageBreak from "./pagebreak.ts";

export function editor(el: HTMLElement, conn: Connection, key: string) {
  el.innerHTML = "";
  const root = createRoot(el);
  root.render(<MyEditor conn={conn} docKey={key} />);
}

export const EXTENSIONS: Extensions = [
  // IF ADDING/CHANGING: edit tiptap_to_html.py to reflect changes. Also keep in mind old data!
  StarterKit.configure({
    history: false,
  }),
  Underline,
  Link,
  TextAlign.configure({
    types: ["heading", "paragraph"],
  }),
  Table,
  TableRow,
  TableHeader,
  TableCell,
  PageBreak,
];

function FormatButton(props: {
  chain: (ch: ChainedCommands) => ChainedCommands;
  active?: boolean | string | {} | ((e: Editor) => boolean);
  enable?: boolean | null | ((e: Editor) => boolean);
  menuItem?: boolean;
  children: React.ReactNode;
}) {
  const { editor } = useCurrentEditor();
  if (!editor) return null;

  let enabled = false;
  if (typeof props.enable === "function") enabled = props.enable(editor);
  else if (typeof props.enable === "boolean") enabled = props.enable;
  else enabled = props.chain(editor.can().chain().focus()).run();

  let active = false;
  if (props.active === undefined) active = false;
  else if (typeof props.active === "function") active = props.active(editor);
  else if (typeof props.active === "boolean") active = props.active;
  else active = editor.isActive(props.active);

  if (props.menuItem === true) {
    return (
      <MenuItem
        onClick={() => {
          props.chain(editor.chain().focus()).run();
        }}
        disabled={!enabled}
        className={active ? "is-active" : undefined}
      >
        {props.children}
      </MenuItem>
    );
  }
  return (
    <button
      onClick={(ev) => {
        ev.preventDefault();
        props.chain(editor.chain().focus()).run();
      }}
      disabled={!enabled}
      className={active ? "is-active" : undefined}
    >
      {props.children}
    </button>
  );
}

function Toolbar() {
  const { editor } = useCurrentEditor();
  if (!editor) return null;
  return (
    <div className="control-group">
      <div className="button-group">
        <FormatButton chain={(c) => c.toggleBold()} active="bold">
          Bold
        </FormatButton>
        <FormatButton chain={(c) => c.toggleItalic()} active="italic">
          Italic
        </FormatButton>
        <FormatButton chain={(c) => c.toggleUnderline()} active="underline">
          Underline
        </FormatButton>
        <FormatButton chain={(c) => c.toggleCode()} active="code">
          Code Segment
        </FormatButton>
        {/* TODO: Link, needs UI to specify URL */}
        <button
          onClick={(ev) => {
            ev.preventDefault();
            editor.chain().focus().unsetAllMarks().run();
          }}
        >
          Clear Formatting
        </button>
      </div>
      <div className="separator" />
      <div className="button-group">
        <Menu menuButton={<MenuButton>Heading...</MenuButton>}>
          {([1, 2, 3, 4, 5, 6] as const).map((level) => (
            <FormatButton
              key={level}
              menuItem
              chain={(c) => c.toggleHeading({ level })}
              active={(e) => e.isActive("heading", { level })}
            >
              Heading {level}
            </FormatButton>
          ))}
        </Menu>
        <Menu menuButton={<MenuButton>Justify...</MenuButton>}>
          <FormatButton
            menuItem
            chain={(c) => c.setTextAlign("left")}
            active={{ textAlign: "left" }}
          >
            Left
          </FormatButton>
          <FormatButton
            menuItem
            chain={(c) => c.setTextAlign("center")}
            active={{ textAlign: "center" }}
          >
            Center
          </FormatButton>
          <FormatButton
            menuItem
            chain={(c) => c.setTextAlign("right")}
            active={{ textAlign: "right" }}
          >
            Right
          </FormatButton>
          <FormatButton
            menuItem
            chain={(c) => c.setTextAlign("justify")}
            active={{ textAlign: "justify" }}
          >
            Justify
          </FormatButton>
        </Menu>
        <FormatButton chain={(c) => c.toggleCodeBlock()} active="codeBlock">
          Code Block
        </FormatButton>
        <FormatButton chain={(c) => c.toggleBlockquote()} active="blockquote">
          Blockquote
        </FormatButton>
      </div>
      <div className="separator" />
      <div className="button-group">
        <Menu menuButton={<MenuButton>List...</MenuButton>}>
          <FormatButton
            menuItem
            chain={(c) => c.toggleBulletList()}
            active="bulletList"
          >
            Bullet
          </FormatButton>
          <FormatButton
            menuItem
            chain={(c) => c.toggleOrderedList()}
            active="orderedList"
          >
            Ordered
          </FormatButton>
        </Menu>
        <Menu menuButton={<MenuButton>Table...</MenuButton>}>
          <FormatButton
            menuItem
            chain={(c) =>
              c.insertTable({ rows: 3, cols: 3, withHeaderRow: true })
            }
          >
            Insert
          </FormatButton>
          <FormatButton menuItem chain={(c) => c.deleteTable()}>
            Delete
          </FormatButton>
          <MenuDivider />
          <FormatButton menuItem chain={(c) => c.addRowBefore()}>
            Add row before
          </FormatButton>
          <FormatButton menuItem chain={(c) => c.addRowAfter()}>
            Add row after
          </FormatButton>
          <FormatButton menuItem chain={(c) => c.deleteRow()}>
            Delete row
          </FormatButton>
          <FormatButton menuItem chain={(c) => c.toggleHeaderRow()}>
            Toggle header column
          </FormatButton>
          <MenuDivider />
          <FormatButton menuItem chain={(c) => c.addColumnBefore()}>
            Add column before
          </FormatButton>
          <FormatButton menuItem chain={(c) => c.addColumnAfter()}>
            Add column after
          </FormatButton>
          <FormatButton menuItem chain={(c) => c.deleteColumn()}>
            Delete column
          </FormatButton>
          <FormatButton menuItem chain={(c) => c.toggleHeaderColumn()}>
            Toggle header column
          </FormatButton>
        </Menu>
        <FormatButton chain={(c) => c.setHorizontalRule()}>
          Horizontal Rule
        </FormatButton>
        <FormatButton chain={(c) => c.setPageBreak()}>Page Break</FormatButton>
      </div>
    </div>
  );
}

function MyEditor(props: { conn: Connection; docKey: string }) {
  const extensions = useMemo(
    () =>
      EXTENSIONS.concat(
        Collaboration.configure({
          document: props.conn.doc,
          field: props.docKey,
        }),
        CollaborationCursor.configure({
          provider: props.conn.provider,
          user: props.conn.provider.awareness.getLocalState()!.user,
        }),
      ),
    [props.conn, props.docKey],
  );

  return (
    <EditorProvider
      extensions={extensions}
      slotBefore={<Toolbar />}
    ></EditorProvider>
  );
}

(window as any).tiptapSchema = getSchema(EXTENSIONS);
