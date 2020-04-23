import zipfile
from datetime import datetime

import requests
from celery import chain
from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.forms import modelform_factory
from django.forms import modelformset_factory
from django.http import Http404
from django.http import HttpResponse
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.translation import gettext as _

from search.helpers import add_digital_file_aggs
from search.helpers import add_digital_file_filters
from search.helpers import add_query_to_search

from .forms import ContentForm
from .forms import DeleteByDublinCoreForm
from .forms import DublinCoreSettingsForm
from .forms import UserForm
from .helpers import get_page_from_search
from .helpers import get_sort_params
from .models import DIP
from .models import Collection
from .models import Content
from .models import DigitalFile
from .models import DublinCore
from .models import User
from .tasks import extract_mets
from .tasks import parse_mets
from .tasks import save_import_error


def _get_and_validate_digital_file_filters(request):
    """Process digital file filters.

    Obtains the digital file filters from the request GET parameteres and
    validates the start and end dates. Returns two dics, the first one with
    all the filters set (to maintain their value in the templates) and the
    second one with only the valid filters (to be applied to the search).
    Adds error messages to the request for invalid dates.
    """
    filters = {
        "formats": request.GET.getlist("for", []),
        "collections": request.GET.getlist("col", []),
        "start_date": request.GET.get("start_date", ""),
        "end_date": request.GET.get("end_date", ""),
    }
    valid_filters = filters.copy()
    if filters["start_date"]:
        try:
            datetime.strptime(filters["start_date"], "%Y-%m-%d")
        except ValueError:
            messages.error(
                request,
                _(
                    "Incorrect date format for start date (%(date)s). "
                    "Expected: yyyy-mm-dd." % {"date": filters["start_date"]}
                ),
            )
            valid_filters.pop("start_date")
    if filters["end_date"]:
        try:
            datetime.strptime(filters["end_date"], "%Y-%m-%d")
        except ValueError:
            messages.error(
                request,
                _(
                    "Incorrect date format for end date (%(date)s). "
                    "Expected: yyyy-mm-dd." % {"date": filters["end_date"]}
                ),
            )
            valid_filters.pop("end_date")

    return (filters, valid_filters)


@login_required(login_url="/login/")
def collections(request, template):
    # Sort options
    sort_options = {"identifier": "dc.identifier.raw", "title": "dc.title.raw"}
    sort_option, sort_dir = get_sort_params(request.GET, sort_options, "identifier")
    sort_field = sort_options.get(sort_option)

    # Search:
    # This view is used in two URLs from scope.urls, where the template
    # is defined for each case. The query parameter should only filter in
    # the collections page.
    search = Collection.es_doc.search()
    if template == "collections.html":
        search = add_query_to_search(search, request.GET.get("query", ""), ["dc.*"])
    search = search.sort({sort_field: {"order": sort_dir}})

    # Pagination
    page = get_page_from_search(search, request.GET)
    collections = page.object_list.execute()

    table_headers = [
        {"label": _("Identifier"), "sort_param": "identifier"},
        {"label": _("Title"), "sort_param": "title", "width": "25%"},
        {"label": _("Date"), "width": "10%"},
        {"label": _("Description")},
        {"label": _("Details")},
    ]

    # Date column should only appear in collections page
    if template != "collections.html":
        table_headers.pop(2)

    return render(
        request,
        template,
        {
            "collections": collections,
            "table_headers": table_headers,
            "sort_option": sort_option,
            "sort_dir": sort_dir,
            "page": page,
        },
    )


def faq(request):
    return render(request, "faq.html")


@login_required(login_url="/login/")
def users(request):
    if not request.user.is_manager():
        return redirect("home")

    # Sort options
    sort_options = {
        "username": "username",
        "first_name": "first_name",
        "last_name": "last_name",
        "email": "email",
        "groups": "group_names",
    }
    sort_option, sort_dir = get_sort_params(request.GET, sort_options, "username")
    sort_field = sort_options.get(sort_option)
    if sort_dir == "desc":
        sort_field = "-%s" % sort_field

    # Search
    query = None
    if "query" in request.GET and request.GET["query"]:
        query = request.GET["query"]
    users = User.get_users(query, sort_field)

    # Pagination
    page = get_page_from_search(users, request.GET)
    users = page.object_list

    table_headers = [
        {"label": _("Username"), "sort_param": "username"},
        {"label": _("First name"), "sort_param": "first_name"},
        {"label": _("Last name"), "sort_param": "last_name"},
        {"label": _("Email"), "sort_param": "email"},
        {"label": _("Groups"), "sort_param": "groups"},
        {"label": _("Active")},
        {"label": _("Admin")},
        {"label": _("Edit")},
    ]

    return render(
        request,
        "users.html",
        {
            "users": users,
            "table_headers": table_headers,
            "sort_option": sort_option,
            "sort_dir": sort_dir,
            "page": page,
        },
    )


@login_required(login_url="/login/")
def new_user(request):
    if not request.user.is_manager():
        return redirect("home")

    form = UserForm(request.POST or None)

    # Remove superuser field for non-admin users
    if not request.user.is_superuser:
        form.fields.pop("is_superuser")

    if form.is_valid():
        form.save()
        return redirect("users")

    return render(request, "new_user.html", {"form": form})


@login_required(login_url="/login/")
def edit_user(request, pk):
    # Allow self-edit and edits by managers
    instance = get_object_or_404(User, pk=pk)
    if request.user.pk != instance.pk and not request.user.is_manager():
        return redirect("home")

    # Only superusers can edit superusers
    if not request.user.is_superuser and instance.is_superuser:
        return redirect("users")

    form = UserForm(request.POST or None, instance=instance)

    # Remove superuser field for non-admin users
    if not request.user.is_superuser or request.user.pk == instance.pk:
        form.fields.pop("is_superuser")

    # Remove active and groups fields on self-edit
    if request.user.pk == instance.pk:
        form.fields.pop("is_active")
        form.fields.pop("groups")

    if form.is_valid():
        form.save()
        # Redirect to users page when editing other user
        if request.user.pk != instance.pk:
            return redirect("users")

    return render(request, "edit_user.html", {"form": form, "instance": instance})


@login_required(login_url="/login/")
def search(request):
    # Sort options
    sort_options = {
        "path": "filepath.raw",
        "format": "fileformat.raw",
        "size": "size_bytes",
        "date": "datemodified",
    }
    sort_option, sort_dir = get_sort_params(request.GET, sort_options, "path")
    sort_field = sort_options.get(sort_option)

    # Search
    search = DigitalFile.es_doc.search()
    # Exclude DigitalFiles from orphan DIPS and from DIPs with 'PENDING' or 'FAILURE'
    # import status when the user is not an editor or an administrator.
    if not request.user.is_editor():
        search = search.query("exists", field="collection.id").exclude(
            "terms", **{"dip.import_status": [DIP.IMPORT_PENDING, DIP.IMPORT_FAILURE]}
        )
    fields = ["filepath", "fileformat", "collection.title"]
    search = add_query_to_search(search, request.GET.get("query", ""), fields)
    search = search.sort({sort_field: {"order": sort_dir}})

    # Aggregations and filters
    search = add_digital_file_aggs(search)
    filters, valid_filters = _get_and_validate_digital_file_filters(request)
    search = add_digital_file_filters(search, valid_filters)

    # Pagination
    page = get_page_from_search(search, request.GET)
    es_response = page.object_list.execute()

    table_headers = [
        {"label": _("Filepath"), "sort_param": "path"},
        {"label": _("Format"), "sort_param": "format"},
        {"label": _("Size"), "sort_param": "size"},
        {"label": _("Last modified"), "sort_param": "date"},
        {"label": _("Collection name")},
        {"label": _("File details")},
    ]

    return render(
        request,
        "search.html",
        {
            "digital_files": es_response.hits,
            "aggs": es_response.aggregations,
            "filters": filters,
            "table_headers": table_headers,
            "sort_option": sort_option,
            "sort_dir": sort_dir,
            "page": page,
            "statuses": DIP.import_statuses(),
        },
    )


@login_required(login_url="/login/")
def collection(request, pk):
    collection = get_object_or_404(Collection, pk=pk)

    # Sort options
    sort_options = {"identifier": "dc.identifier.raw", "title": "dc.title.raw"}
    sort_option, sort_dir = get_sort_params(request.GET, sort_options, "identifier")
    sort_field = sort_options.get(sort_option)

    # Search
    search = DIP.es_doc.search().query("match", **{"collection.id": pk})
    # Exclude DIPs with 'PENDING' or 'FAILURE' import status
    # when the user is not an editor or an administrator.
    if not request.user.is_editor():
        search = search.exclude(
            "terms", import_status=[DIP.IMPORT_PENDING, DIP.IMPORT_FAILURE]
        )
    search = add_query_to_search(search, request.GET.get("query", ""), ["dc.*"])
    search = search.sort({sort_field: {"order": sort_dir}})

    # Pagination
    page = get_page_from_search(search, request.GET)
    dips = page.object_list.execute()

    table_headers = [
        {"label": _("Identifier"), "sort_param": "identifier"},
        {"label": _("Title"), "sort_param": "title", "width": "25%"},
        {"label": _("Date"), "width": "10%"},
        {"label": _("Description")},
        {"label": _("Details")},
    ]

    return render(
        request,
        "collection.html",
        {
            "collection": collection,
            "dips": dips,
            "table_headers": table_headers,
            "sort_option": sort_option,
            "sort_dir": sort_dir,
            "page": page,
            "statuses": DIP.import_statuses(),
        },
    )


@login_required(login_url="/login/")
def dip(request, pk):
    dip = get_object_or_404(DIP, pk=pk)

    # Redirect to the collection or home page if the DIP is not visible
    if not dip.is_visible_by_user(request.user):
        if dip.collection:
            return redirect("collection", pk=dip.collection.pk)
        else:
            return redirect("home")

    # Show notification to user about import error
    if dip.import_status == DIP.IMPORT_FAILURE:
        messages.error(request, dip.get_import_error_message())

    # Sort options
    sort_options = {
        "path": "filepath.raw",
        "format": "fileformat.raw",
        "size": "size_bytes",
        "date": "datemodified",
    }
    sort_option, sort_dir = get_sort_params(request.GET, sort_options, "path")
    sort_field = sort_options.get(sort_option)

    # Search
    search = DigitalFile.es_doc.search().query("match", **{"dip.id": pk})
    fields = ["filepath", "fileformat"]
    search = add_query_to_search(search, request.GET.get("query", ""), fields)
    search = search.sort({sort_field: {"order": sort_dir}})

    # Aggregations and filters
    search = add_digital_file_aggs(search, collections=False)
    filters, valid_filters = _get_and_validate_digital_file_filters(request)
    search = add_digital_file_filters(search, valid_filters)

    # Pagination
    page = get_page_from_search(search, request.GET)
    es_response = page.object_list.execute()

    table_headers = [
        {"label": _("Filepath"), "sort_param": "path"},
        {"label": _("Format"), "sort_param": "format"},
        {"label": _("Size"), "sort_param": "size"},
        {"label": _("Last modified"), "sort_param": "date"},
        {"label": _("File details")},
    ]

    return render(
        request,
        "dip.html",
        {
            "dip": dip,
            "digital_files": es_response.hits,
            "aggs": es_response.aggregations,
            "filters": filters,
            "table_headers": table_headers,
            "sort_option": sort_option,
            "sort_dir": sort_dir,
            "page": page,
            "statuses": DIP.import_statuses(),
        },
    )


@login_required(login_url="/login/")
def digital_file(request, pk):
    digitalfile = get_object_or_404(DigitalFile, pk=pk)

    # Redirect to the collection or home page if the related DIP is not visible
    if not digitalfile.dip.is_visible_by_user(request.user):
        if digitalfile.dip.collection:
            return redirect("collection", pk=digitalfile.dip.collection.pk)
        else:
            return redirect("home")

    # Show notification to user about import error
    if digitalfile.dip.import_status == DIP.IMPORT_FAILURE:
        messages.error(request, digitalfile.dip.get_import_error_message())

    return render(request, "digitalfile.html", {"digitalfile": digitalfile})


@login_required(login_url="/login/")
def new_collection(request):
    if not request.user.is_editor():
        return redirect("home")

    CollectionForm = modelform_factory(Collection, fields=("link",))
    collection_form = CollectionForm(request.POST or None)
    DublinCoreForm = modelform_factory(DublinCore, fields=DublinCore.enabled_fields())
    dc_form = DublinCoreForm(request.POST or None)

    if request.method == "POST" and collection_form.is_valid() and dc_form.is_valid():
        collection = collection_form.save(commit=False)
        collection.dc = dc_form.save()
        collection.save()

        return redirect("collections")

    return render(
        request,
        "new_collection.html",
        {"collection_form": collection_form, "dc_form": dc_form},
    )


@login_required(login_url="/login/")
def new_dip(request):
    if not request.user.is_editor():
        return redirect("home")

    DIPForm = modelform_factory(DIP, fields=("collection", "objectszip"))
    dip_form = DIPForm(request.POST or None, request.FILES or None)
    DublinCoreForm = modelform_factory(DublinCore, fields=("identifier",))
    dc_form = DublinCoreForm(request.POST or None)

    if request.method == "POST" and dip_form.is_valid() and dc_form.is_valid():
        dip = dip_form.save(commit=False)
        dip.dc = dc_form.save()
        dip.import_status = DIP.IMPORT_PENDING
        dip.save()

        # Extract and parse METS file asynchronously
        chain(extract_mets.s(dip.objectszip.path), parse_mets.s(dip.pk)).on_error(
            save_import_error.s(dip_id=dip.pk)
        ).delay()

        # Show notification to user about import in progress
        messages.info(
            request,
            _(
                "A background process has been launched to extract and parse "
                "the METS file. After the process finishes and the interface "
                "is reloaded, a link to the Folder will show up in the "
                "Folders table below."
            ),
        )

        if dip.collection:
            return redirect("collection", pk=dip.collection.pk)
        else:
            return redirect("orphan_dips")

    return render(request, "new_dip.html", {"dip_form": dip_form, "dc_form": dc_form})


@login_required(login_url="/login/")
def edit_collection(request, pk):
    if not request.user.is_editor():
        return redirect("collection", pk=pk)

    collection = get_object_or_404(Collection, pk=pk)
    CollectionForm = modelform_factory(Collection, fields=("link",))
    collection_form = CollectionForm(request.POST or None, instance=collection)
    DublinCoreForm = modelform_factory(DublinCore, fields=DublinCore.enabled_fields())
    dc_form = DublinCoreForm(request.POST or None, instance=collection.dc)

    if request.method == "POST" and collection_form.is_valid() and dc_form.is_valid():
        dc_form.save()
        collection_form.save()
        if collection.requires_es_descendants_update():
            messages.info(
                request,
                _(
                    "A background process has been launched to update the "
                    "Collection metadata in the Elasticsearch index for the "
                    "related Digital Files."
                ),
            )
        return redirect("collection", pk=pk)

    return render(
        request,
        "edit_collection.html",
        {
            "collection_form": collection_form,
            "dc_form": dc_form,
            "collection": collection,
        },
    )


@login_required(login_url="/login/")
def edit_dip(request, pk):
    if not request.user.is_editor():
        return redirect("dip", pk=pk)

    dip = get_object_or_404(DIP, pk=pk)
    DIPForm = modelform_factory(DIP, fields=("collection",))
    dip_form = DIPForm(request.POST or None, instance=dip)
    DublinCoreForm = modelform_factory(DublinCore, fields=DublinCore.enabled_fields())
    dc_form = DublinCoreForm(request.POST or None, instance=dip.dc)

    if request.method == "POST" and dip_form.is_valid() and dc_form.is_valid():
        dc_form.save()
        dip_form.save()
        if dip.requires_es_descendants_update():
            messages.info(
                request,
                _(
                    "A background process has been launched to update the "
                    "ancestors metadata in the Elasticsearch index for the "
                    "related Digital Files."
                ),
            )
        return redirect("dip", pk=pk)

    return render(
        request, "edit_dip.html", {"dip_form": dip_form, "dc_form": dc_form, "dip": dip}
    )


@login_required(login_url="/login/")
def delete_collection(request, pk):
    if not request.user.is_superuser:
        return redirect("collection", pk=pk)

    collection = get_object_or_404(Collection, pk=pk)
    dc = get_object_or_404(DublinCore, pk=collection.dc_id)
    form = DeleteByDublinCoreForm(
        request.POST or None, instance=dc, initial={"identifier": ""}
    )
    if form.is_valid():
        if collection.requires_es_descendants_delete():
            messages.info(
                request,
                _(
                    "A background process has been launched to delete the "
                    "descendant Folders and Digital Files from the Elasticsearch "
                    "indexes."
                ),
            )
        collection.delete()
        return redirect("collections")

    return render(
        request, "delete_collection.html", {"form": form, "collection": collection}
    )


@login_required(login_url="/login/")
def delete_dip(request, pk):
    if not request.user.is_superuser:
        return redirect("dip", pk=pk)

    dip = get_object_or_404(DIP, pk=pk)
    dc = get_object_or_404(DublinCore, pk=dip.dc_id)
    form = DeleteByDublinCoreForm(
        request.POST or None, instance=dc, initial={"identifier": ""}
    )
    if form.is_valid():
        # Get redirect URL before deletion
        redirection = redirect("home")
        if dip.collection:
            redirection = redirect("collection", pk=dip.collection.pk)
        if dip.requires_es_descendants_delete():
            messages.info(
                request,
                _(
                    "A background process has been launched to delete the "
                    "descendant Digital Files from the Elasticsearch index."
                ),
            )
        dip.delete()
        return redirection

    return render(request, "delete_dip.html", {"form": form, "dip": dip})


@login_required(login_url="/login/")
def orphan_dips(request):
    if not request.user.is_editor():
        return redirect("home")

    # Sort options
    sort_options = {"identifier": "dc.identifier.raw", "title": "dc.title.raw"}
    sort_option, sort_dir = get_sort_params(request.GET, sort_options, "identifier")
    sort_field = sort_options.get(sort_option)

    # Search
    search = DIP.es_doc.search().exclude("exists", field="collection.id")
    search = add_query_to_search(search, request.GET.get("query", ""), ["dc.*"])
    search = search.sort({sort_field: {"order": sort_dir}})

    # Pagination
    page = get_page_from_search(search, request.GET)
    dips = page.object_list.execute()

    table_headers = [
        {"label": _("Identifier"), "sort_param": "identifier"},
        {"label": _("Title"), "sort_param": "title", "width": "25%"},
        {"label": _("Date"), "width": "10%"},
        {"label": _("Description")},
        {"label": _("Details")},
    ]

    return render(
        request,
        "orphan_dips.html",
        {
            "dips": dips,
            "table_headers": table_headers,
            "sort_option": sort_option,
            "sort_dir": sort_dir,
            "page": page,
            "statuses": DIP.import_statuses(),
        },
    )


@login_required(login_url="/login/")
def download_dip(request, pk):
    dip = get_object_or_404(DIP, pk=pk)
    # Prioritize local copy
    if dip.objectszip:
        try:
            response = HttpResponse()
            response["Content-Length"] = dip.objectszip.size
            if zipfile.is_zipfile(dip.objectszip):
                response["Content-Type"] = "application/zip"
            else:
                response["Content-Type"] = "application/x-tar"
            response["Content-Disposition"] = (
                'attachment; filename="%s"' % dip.objectszip.name
            )
            response["X-Accel-Redirect"] = "/media/%s" % dip.objectszip.name
            return response
        except FileNotFoundError:
            raise Http404("DIP file not found.")
    # Proxy stream from the SS
    if dip.ss_host_url not in django_settings.SS_HOSTS.keys():
        raise RuntimeError("Configuration not found for SS host: %s" % dip.ss_host_url)
    headers = {
        "Authorization": "ApiKey %s:%s"
        % (
            django_settings.SS_HOSTS[dip.ss_host_url]["user"],
            django_settings.SS_HOSTS[dip.ss_host_url]["secret"],
        )
    }
    stream = requests.get(dip.ss_download_url, headers=headers, stream=True)
    if stream.status_code != requests.codes.ok:
        raise Http404("DIP file not found.")
    # So far, the SS only downloads DIPs as tar files
    response = StreamingHttpResponse(stream)
    response["Content-Type"] = stream.headers.get("Content-Type", "application/x-tar")
    response["Content-Disposition"] = stream.headers.get(
        "Content-Disposition", 'attachment; filename="%s.tar"' % dip.ss_dir_name
    )
    content_length = stream.headers.get("Content-Length")
    if content_length:
        response["Content-Length"] = content_length
    return response


@login_required(login_url="/login/")
def settings(request):
    if not request.user.is_superuser:
        return redirect("home")

    form = DublinCoreSettingsForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        # Redirect to not add validation classes
        return redirect("settings")

    return render(request, "settings.html", {"form": form})


@login_required(login_url="/login/")
def content(request):
    if not request.user.is_superuser:
        return redirect("home")

    ContentFormSet = modelformset_factory(Content, form=ContentForm, extra=0)
    formset = ContentFormSet(
        request.POST or None, queryset=Content.objects.all().order_by("key")
    )

    if request.method == "POST" and formset.is_valid():
        formset.save()
        # Redirect to not add validation classes
        return redirect("content")

    return render(request, "content.html", {"formset": formset})
