
from django.http import HttpRequest, HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
import pycrdt

from collab_poc_app.models import TestDoc
from collab_poc_app.tiptap_to_html import TiptapToHtml
from pycrdt_model.models import History

@login_required
def index(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        obj = TestDoc.objects.create()
        obj.save()
        return redirect("detail", pk=obj.pk)
    return render(request, "poc/index.html", {"docs": TestDoc.objects.order_by("id").defer("yjs_doc")})

@login_required
def doc(request: HttpRequest, pk: int) -> HttpResponse:
    return render(request, "poc/doc.html", {
        "doc": get_object_or_404(TestDoc, pk=pk),
        "wspath": f"/ws/doc/",
    })

def observe_history(frag: pycrdt.XmlFragment):
    out_list = list()
    def callback(evs: list[pycrdt.XmlEvent]):
        for ev in evs:
            #print(type(ev), str(ev.target), ev.path, ev.delta, ev.keys, flush=True)
            out_list.append((isinstance(ev.target, pycrdt.XmlText), ev.path, ev.delta, ev.keys))
    frag.observe_deep(callback)
    return out_list

@login_required
def history_list(request: HttpRequest, pk: int) -> HttpResponse:
    doc_model = get_object_or_404(TestDoc, pk=pk)

    history_qs = History.for_object(doc_model, recent_first=True)
    history_paginator = Paginator(history_qs, 30, allow_empty_first_page=True)
    history_page = history_paginator.get_page(request.GET.get("page"))

    if not history_page:
        # Don't bother restoring doc for an empty page
        return render(request, "poc/doc_history_list.html", {
            "doc": doc_model,
            "page": history_page,
            "entries": [],
        })

    doc = History.replay(doc_model, history_page[-1].id, until_id_inclusive=False)
    frags = [doc.get(key, type=pycrdt.XmlFragment) for key, _ in TestDoc.RICH_TEXT_FIELDS]
    frag_events = [observe_history(frag) for frag in frags]

    html_diffs_per_instance: list[list[TiptapToHtml]] = []
    instance: History
    for instance in reversed(history_page):
        delta_render = [TiptapToHtml(frag) for frag in frags]
        doc.apply_update(instance.update)
        for html, events in zip(delta_render, frag_events):
            for (is_text, path, delta, keys) in events:
                if is_text:
                    html.apply_text_event(path, delta)
                else:
                    html.apply_element_event(path, delta, keys)
            events.clear()
        html_diffs_per_instance.append([str(html) for html in delta_render])
    
    entries = (
        (instance, (
            (name, pretty_name, diff)
            for (name, pretty_name), diff
            in zip(TestDoc.RICH_TEXT_FIELDS, html_diffs_per_field)
        ))
        for instance, html_diffs_per_field
        in zip(history_page, reversed(html_diffs_per_instance))
    )

    return render(request, "poc/doc_history_list.html", {
        "doc": doc_model,
        "page": history_page,
        "entries": entries,
    })

@login_required
def history_view(request: HttpRequest, doc_pk: int, history_pk: int) -> HttpResponse:
    doc_model = get_object_or_404(TestDoc, pk=doc_pk)

    res = History.replay_until(doc_model, history_pk)
    if res is None:
        raise Http404()
    doc, history_entry = res

    non_collab_fields_changed = []
    doc.get("non_collab_fields", type=pycrdt.Map).observe(lambda ev: non_collab_fields_changed.extend(ev.keys))

    frags = [doc.get(key, type=pycrdt.XmlFragment) for key, _ in TestDoc.RICH_TEXT_FIELDS]
    events = [observe_history(frag) for frag in frags]
    before = [str(TiptapToHtml(frag)) for frag in frags]
    delta_render = [TiptapToHtml(frag) for frag in frags]

    doc.apply_update(history_entry.update)

    after = [str(TiptapToHtml(frag)) for frag in frags]
    for html, evs in zip(delta_render, events):
        for (is_text, path, delta, keys) in evs:
            if is_text:
                html.apply_text_event(path, delta)
            else:
                html.apply_element_event(path, delta, keys)

    return render(request, "poc/doc_history_view.html", {
        "doc": doc_model,
        "history_entry": history_entry,
        "non_collab_fields_changed": non_collab_fields_changed,
        "collab_fields": list(zip(
            (pretty for pretty, _ in TestDoc.RICH_TEXT_FIELDS),
            before,
            after,
            delta_render,
            events,
        )),
    })
