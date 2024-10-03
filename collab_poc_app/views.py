from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required

from collab_poc_app.models import TestDoc

@login_required
def index(request: HttpRequest):
    if request.method == "POST":
        obj = TestDoc.objects.create()
        obj.save()
        return redirect("detail", pk=obj.pk)
    return render(request, "poc/index.html", {"docs": TestDoc.objects.order_by("id")})

@login_required
def doc(request: HttpRequest, pk: int):
    return render(request, "poc/doc.html", {
        "doc": get_object_or_404(TestDoc, pk=pk),
        "wspath": f"/ws/doc/",
    })
