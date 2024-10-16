
import logging
from typing import Any, Callable, Iterable, Iterator, TypeVar
import pycrdt
from xml.dom.minidom import Document, DocumentFragment, Node, Element, Text
from django.utils.safestring import SafeString

logger = logging.getLogger(__name__)

T = TypeVar('T')

class TiptapToHtml:
    """
    Class for converting TipTap/Prosemirror XML from a YJS doc to (X)HTML, and for applying diff markup
    based off of update events.

    To use, create an instance with a `pycrdt.XmlFragment`, optionally add diff markup via `apply_text_event` or
    `apply_element_event` from observing the fragment, then call `str` on the instance.

    This converter assumes the XML comes from this app's tiptap/prosemirror schema config, and also only works
    assuming that block nodes can only contain either block nodes or text nodes as direct children, and does not
    mix them (which is true for every schema that I am aware of).
    
    `XmlElements` are converted to their HTML equivalent. `XmlText` segments are converted to a sequence of
    `span`, `a`, or other inline elements - one for each "diff" segment of the text.

    The generated HTML is stored as an XML document so that it can be navigated for applying event diffs.
    `__str__` converts the document to XHTML for inclusion in a document.
    """
    xhtmldoc: Document
    xhtmlfrag: DocumentFragment

    def __init__(self, yxml: pycrdt.XmlFragment) -> None:
        self.xhtmldoc = Document()
        self.xhtmlfrag = self.xhtmldoc.createDocumentFragment()
        for node in self._convert(yxml):
            self.xhtmlfrag.appendChild(node)

    def __str__(self) -> SafeString:
        return SafeString(
            "".join(node.toxml() for node in self.xhtmlfrag.childNodes)
        )

    def _convert(self, yxml: pycrdt.XmlElement | pycrdt.XmlText | pycrdt.XmlFragment) -> Iterator[Node]:
        if isinstance(yxml, pycrdt.XmlText):
            for text, attrs in yxml.diff():
                yield self._convert_text_segment(text, attrs)
            return
        if isinstance(yxml, pycrdt.XmlFragment):
            yield from self._convert_children(yxml)
            return
        yield self._convert_element(yxml)

    def _convert_children(self, yxml: pycrdt.XmlElement | pycrdt.XmlFragment) -> Iterator[Node]:
        for ch in yxml.children:
            yield from self._convert(ch)

    def _convert_text_segment(self, text: str, attrs: dict[str, Any] | None) -> Element:
        text = self.xhtmldoc.createTextNode(text)
        el = self.xhtmldoc.createElement("span")
        el.appendChild(text)
        if attrs:
            self._apply_text_formatting(el, attrs.items())
        return el

    def _apply_text_formatting(self, node: Element, changes: Iterable[tuple[str, Any | None]]) -> None:
        """
        Applies a change in text formatting.

        `changes` is an iterable of key/value pairs of new attribute values, or deletions of the value is None.
        It may be a complete set from the element's initial creation, or a difference from an edit event.
        """
        classes = set(node.getAttribute("class").split())
        for name, value in changes:
            try:
                method = getattr(self, f"_apply_mark_{name}")
            except AttributeError:
                logger.warning("Unrecognized mark: %r", name)
                classes.add("unrecgonized-mark")
            else:
                method(node, value, classes)
        node.setAttribute("class", " ".join(sorted(classes)))

    def _convert_element(self, yxml: pycrdt.XmlElement) -> Element:
        """
        Converts a YJS XmlElement and its children to its XHTML equivalent and returns it.
        """
        node = self.xhtmldoc.createElement("div")
        node.setAttribute("data-yjs-tag", yxml.tag)
        self._apply_element_formatting(yxml.tag, node, iter(yxml.attributes))
        for child in self._convert_children(yxml):
            node.appendChild(child)
        return node

    def _apply_element_formatting(self, yxml_tag: str, node: Element, changes: Iterable[tuple[str, Any | None]]) -> None:
        """
        Applies a change in element formatting.

        `changes` is an iterable of key/value pairs of new attribute values, or deletions of the value is None.
        It may be a complete set from the element's initial creation, or a difference from an edit event.
        """
        try:
            method: Callable[[Element, Iterable[tuple[str, Any | None]], set[str]], None] = getattr(self, f"_apply_tag_{yxml_tag}")
        except AttributeError:
            logger.warning("Unimplemented yxml tag: %s", yxml_tag)
            node.tagName = "div"
            node.setAttribute("class", "unrecognized-tag")
        else:
            classes = set()
            method(node, changes, classes)
            node.setAttribute("class", " ".join(sorted(classes)))

    # ######################################################################
    # Text diff

    def apply_text_event(self, path: list[int], delta: list[dict[str,Any]]):
        """
        Applies diff formatting for an alteration on a text node.

        `path` and `delta` should be from the `pycrdt.XmlEvent` fired for the modifications on the top
        level `XmlFragment.observe_deep` listener, when its target is an `pycrdt.XmlText` instance.
        """
        assert path[-1] == 0

        parentNode: Node = self.xhtmlfrag
        for index in path[:-1]:
            parentNode = parentNode.childNodes[index]

        assert isinstance(parentNode, Element)

        # Delta sections are specified via adding character offsets. This is more complicated since we have XHTML nodes.
        # So store the current position as a tuple of the current span we are in and the string offset.
        #
        # _advance_characters will return a new span,index 
        current_span = parentNode.childNodes[0]
        char_index = 0

        for op in delta:
            if "retain" in op:
                current_span, char_index, segments = self._advance_characters(current_span, char_index, op["retain"])

                attrs: dict[str, Any] | None = op.get("attributes")
                if not attrs:
                    continue
                for node, slice in segments:
                    if slice.stop is not None:
                        node, _, current_span, char_index = self._split_span_and_track_pos(node, slice.stop, current_span, char_index)
                    if slice.start != 0:
                        _, node, current_span, char_index = self._split_span_and_track_pos(node, slice.start, current_span, char_index)
                self._apply_text_formatting(node, attrs.items())
                add_class(node, "changeset-edited")
            elif "delete" in op:
                current_span, char_index, segments = self._advance_characters(current_span, char_index, op["delete"])
                for node, slice in segments:
                    if slice.stop is not None:
                        node, _, current_span, char_index = self._split_span_and_track_pos(node, slice.stop, current_span, char_index)
                    if slice.start != 0:
                        _, node, current_span, char_index = self._split_span_and_track_pos(node, slice.start, current_span, char_index)
                    add_class(node, "changeset-deleted")
            elif "insert" in op:
                if char_index != 0:
                    _, current_span = self._split_span(current_span, char_index)
                    char_index = 0
                node = self._convert_text_segment(op["insert"], op.get("attributes"))
                add_class(node, "changeset-added")
                parentNode.insertBefore(node, current_span)
            else:
                raise ValueError(f"Unrecognized yjs delta: {op!r}")

    @staticmethod
    def _advance_characters(current_span: Element, char_index: int, num_chars: int) -> tuple[
        Element,
        int,
        list[tuple[Element, slice]],
    ]:
        """
        Advances by a number of characters specified from a yjs delta.

        Starting at `char_index` bytes into the `current_span` element, advance `num_char` ahead, possibly into the next
        siblings of the element.

        `current_span` and its siblings must be elements that each have a single text node child.

        Returns a tuple of the element and sibling after advancement, and the list of elements and text sections
        traversed.
        """
        passed_over = []
        while num_chars > 0:
            assert len(current_span.childNodes) == 1
            assert isinstance(current_span.childNodes[0], Text)
            text: str = current_span.childNodes[0].data
            if char_index + num_chars >= len(text):
                passed_over.append((
                    current_span,
                    slice(char_index, None),
                ))
                num_chars = num_chars + char_index - len(text)
                current_span = current_span.nextSibling
                char_index = 0
            else:
                passed_over.append((
                    current_span,
                    slice(char_index, char_index+num_chars)
                ))
                char_index += num_chars
                num_chars = 0
        return (current_span, char_index, passed_over)

    def _split_span(self, span: Element, offset: int) -> tuple[Element, Element]:
        """
        Splits a span that has a single text node child. Copies attributes.
        """
        left = self.xhtmldoc.createElement(span.tagName)
        right = self.xhtmldoc.createElement(span.tagName)
        for k,v in span.attributes.items():
            left.setAttribute(k,v)
            right.setAttribute(k,v)
        text = span.childNodes[0].data
        left.appendChild(self.xhtmldoc.createTextNode(text[:offset]))
        right.appendChild(self.xhtmldoc.createTextNode(text[offset:]))
        span.parentNode.insertBefore(left, span)
        span.parentNode.replaceChild(right, span)
        return (left, right)

    def _split_span_and_track_pos(self, span: Element, offset: int, current_span: Element, char_index: int) -> tuple[Element, Element, Element, int]:
        """
        Split spans and also returns adjusted current_span + char_index if the span being split is the current_span.
        """
        is_current = current_span == span
        left, right = self._split_span(span, offset)
        if is_current:
            current_span = right
            char_index = char_index - len(left.childNodes[0].data)
        return (left, right, current_span, char_index)

    # ######################################################################
    # Element deltas

    def apply_element_event(self, path: list[int], delta: list[dict[str, Any]], key_delta: dict[str, Any | None]):
        """
        Applies diff formatting for an alteration on an element.

        `path` and `delta` should be from the `pycrdt.XmlEvent` fired for the modifications on the top
        level `XmlFragment.observe_deep` listener, when its target is an `pycrdt.XmlElement` or `pycrdt.XmlFragment` instance.
        """
        node: Element = self.xhtmlfrag
        for index in path:
            node = node.childNodes[index]

        if key_delta:
            self._apply_element_formatting(
                node.getAttribute("data-yjs-tag"),
                node,
                ((k, v.get("newValue")) for k,v in key_delta.items()),
            )
            add_class(node, "changeset-edited")

        i = 0
        for op in delta:
            if "retain" in op:
                i += op["retain"]
            elif "insert" in op:
                for el in op["insert"]:
                    if isinstance(el, pycrdt.XmlText):
                        new_nodes = (self._convert_text_segment(text, attrs) for text, attrs in el.diff())
                    else:
                        new_nodes = [self._convert_element(el)]
                    for insert_node in new_nodes:
                        add_class(insert_node, "changeset-added")
                        if i == len(node.childNodes):
                            node.appendChild(insert_node)
                        else:
                            node.insertBefore(insert_node, node.childNodes[i])
                        i += 1
            elif "delete" in op:
                for _ in range(op["delete"]):
                    delete_node = node.childNodes[i]
                    add_class(delete_node, "changeset-deleted")
                    i += 1
            else:
                raise ValueError(f"Unrecognized yjs delta: {op!r}")

    # ######################################################################
    # Tag handlers
    # Should be named `_apply_tag_<name>` and take an `Element` to modify, an iterable of changed attributes
    # (with None values meaning deleted), and a set of classes that will be applied after the call.
    # The function should modify the provided element, applying the `attr_changes` (which may originate from either
    # the yjs element itself or from a change event)

    def _apply_tag_paragraph(self, el: Element, attr_changes: Iterable[tuple[str, Any | None]], classes: set[str]) -> None:
        el.tagName = "p"
        for name, value in attr_changes:
            if name == "textAlign":
                set_retain(classes, lambda cls: not cls.startswith("text-align-"))
                if value is not None:
                    classes.add("text-align-" + value)

    def _apply_tag_header(self, el: Element, attr_changes: Iterable[tuple[str, Any | None]], _classes: set[str]) -> None:
        for name, value in attr_changes:
            if name == "level" and isinstance(value, int) and value >= 1 and value <= 6:
                el.tagName = "h" + value

    def _apply_tag_blockquote(self, el: Element, _attr_changes: Iterable[tuple[str, Any | None]], _classes: set[str]) -> None:
        el.tagName = "blockquote"

    def _apply_tag_table(self, el: Element, _attr_changes: Iterable[tuple[str, Any | None]], _classes: set[str]) -> None:
        el.tagName = "table"

    def _apply_tag_tableRow(self, el: Element, _attr_changes: Iterable[tuple[str, Any | None]], _classes: set[str]) -> None:
        el.tagName = "tr"

    def _apply_tag_tableCell(self, el: Element, _attr_changes: Iterable[tuple[str, Any | None]], _classes: set[str]) -> None:
        el.tagName = "td"

    def _apply_tag_tableHeader(self, el: Element, _attr_changes: Iterable[tuple[str, Any | None]], _classes: set[str]) -> None:
        el.tagName = "th"

    def _apply_tag_bulletList(self, el: Element, _attr_changes: Iterable[tuple[str, Any | None]], _classes: set[str]) -> None:
        el.tagName = "ul"

    def _apply_tag_orderedList(self, el: Element, _attr_changes: Iterable[tuple[str, Any | None]], _classes: set[str]) -> None:
        el.tagName = "ol"

    def _apply_tag_listItem(self, el: Element, _attr_changes: Iterable[tuple[str, Any | None]], _classes: set[str]) -> None:
        el.tagName = "li"

    def _apply_tag_hardBreak(self, el: Element, _attr_changes: Iterable[tuple[str, Any | None]], _classes: set[str]) -> None:
        el.tagName = "br"

    def _apply_tag_codeBlock(self, el: Element, _attr_changes: Iterable[tuple[str, Any | None]], classes: set[str]) -> None:
        el.tagName = "code"
        classes.add("code-block")

    def _apply_tag_hardBreak(self, el: Element, _attr_changes: Iterable[tuple[str, Any | None]], _classes: set[str]) -> None:
        el.tagName = "div"
        if not el.childNodes:
            line1 = self.xhtmldoc.createElement("div")
            line1.setAttribute("class", "page-break-line")
            el.appendChild(line1)
            text = self.xhtmldoc.createElement("div")
            text.setAttribute("class", "page-break-text")
            text.appendChild(self.xhtmldoc.createTextNode("Page Break"))
            el.appendChild(text)
            line2 = self.xhtmldoc.createElement("div")
            line2.setAttribute("class", "page-break-line")
            el.appendChild(line2)

    # ######################################################################
    # Mark handlers

    def _apply_mark_link(self, el: Element, attr: Any | None, classes: set[str]) -> None:
        if attr is None:
            el.tagName = "span"
            el.removeAttribute("href")
            el.removeAttribute("rel")
            el.removeAttribute("target")
        else:
            el.tagName = "a"
            el.setAttribute("href", attr) # TODO: is this correct?
            el.setAttribute("rel", "noopener noreferrer nofollow")
            el.setAttribute("target", "_blank")

    def _apply_mark_bold(self, _el: Element, attr: Any | None, classes: set[str]) -> None:
        modify_class(classes, "bold", attr)

    def _apply_mark_code(self, _el: Element, attr: Any | None, classes: set[str]) -> None:
        modify_class(classes, "code", attr)

    def _apply_mark_italic(self, _el: Element, attr: Any | None, classes: set[str]) -> None:
        modify_class(classes, "italic", attr)

    def _apply_mark_strike(self, _el: Element, attr: Any | None, classes: set[str]) -> None:
        modify_class(classes, "strike", attr)

    def _apply_mark_underline(self, _el: Element, attr: Any | None, classes: set[str]) -> None:
        modify_class(classes, "underline", attr)

def modify_class(classes: set[str], name: str, value: Any | None):
    """
    If `value` is not None, add `name` to the `classes` set - otherwise removes it.
    """
    if value is None:
        classes.discard(name)
    else:
        classes.add(name)

def set_retain(set: set[T], func: Callable[[T], bool]):
    """
    Remove elements from a set where `func(element)` returns false
    """
    for v in set:
        if not func(v):
            set.remove(v)

def add_class(el: Element, cls: str):
    """
    Adds a class to an element's "class" attribute
    """
    if el.hasAttribute("class") and el.getAttribute("class") != "":
        el.setAttribute("class", el.getAttribute("class") + " " + cls)
    else:
        el.setAttribute("class", cls)
