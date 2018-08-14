from django.contrib import messages
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.forms import modelform_factory
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import gettext as _
from .models import User, Collection, DIP, DigitalFile, DublinCore
from .forms import DeleteByDublinCoreForm, UserCreationForm, UserChangeForm
from .tasks import extract_and_parse_mets


def get_sort_params(request, options, default):
    """
    Get sort option and direction from request. Check options dict. for
    available choices and use default if no option is passed on the request
    or if the option is not valid. Defaults to asc. sort direction.
    """
    option = default
    if 'sort' in request.GET and request.GET['sort'] in list(options.keys()):
        option = request.GET['sort']

    direction = 'asc'
    if 'sort_dir' in request.GET and request.GET['sort_dir'] in ['asc', 'desc']:
        direction = request.GET['sort_dir']

    return (option, direction)


def add_query_to_search(search, request, fields):
    """
    Check if a `query` parameter has been sent in the request and add a
    `simple_query_string` to the search over a given list of fields.
    """
    if 'query' in request.GET and request.GET['query']:
        search = search.query(
            'simple_query_string',
            query=request.GET['query'],
            default_operator='and',
            fields=fields,
        )

    return search


def get_page_from_search(search, request):
    """
    Create paginator and return current page based on the current search
    and the page and limit request parameters. Limit defaults to 10 and
    can't be set over 100.
    """
    try:
        limit = int(request.GET.get('limit', 10))
        if limit <= 0 or limit > 100:
            raise ValueError
    except ValueError:
        limit = 10

    paginator = Paginator(search, limit)
    page_no = request.GET.get('page')
    try:
        page = paginator.page(page_no)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    return page


@login_required(login_url='/login/')
def home(request):
    # Sort options
    sort_options = {
        'identifier': 'dc.identifier.raw',
        'title': 'dc.title.raw',
    }
    sort_option, sort_dir = get_sort_params(request, sort_options, 'identifier')
    sort_field = sort_options.get(sort_option)

    # Search
    search = Collection.es_doc.search()
    search = add_query_to_search(search, request, ['dc.*'])
    search = search.sort({sort_field: {'order': sort_dir}})

    # Pagination
    page = get_page_from_search(search, request)
    collections = page.object_list.execute()

    table_headers = [
        (_('Identifier'), 'identifier'),
        (_('Title'), 'title'),
        (_('Date'), None),
        (_('Description'), None),
        (_('Details'), None),
    ]

    return render(request, 'home.html', {
        'collections': collections,
        'table_headers': table_headers,
        'sort_option': sort_option,
        'sort_dir': sort_dir,
        'page': page,
    })


def faq(request):
    return render(request, 'faq.html')


@login_required(login_url='/login/')
def users(request):
    # Only admins or managers can see users
    if not request.user.is_manager():
        return redirect('home')

    # Sort options
    sort_options = {
        'username': 'username',
        'first_name': 'first_name',
        'last_name': 'last_name',
        'email': 'email',
        'groups': 'group_names'
    }
    sort_option, sort_dir = get_sort_params(request, sort_options, 'username')
    sort_field = sort_options.get(sort_option)
    if sort_dir == 'desc':
        sort_field = '-%s' % sort_field

    # Search
    query = None
    if 'query' in request.GET and request.GET['query']:
        query = request.GET['query']
    users = User.get_users(query, sort_field)

    # Pagination
    page = get_page_from_search(users, request)
    users = page.object_list

    table_headers = [
        (_('Username'), 'username'),
        (_('First name'), 'first_name'),
        (_('Last name'), 'last_name'),
        (_('Email'), 'email'),
        (_('Groups'), 'groups'),
        (_('Active'), None),
        (_('Admin'), None),
        (_('Edit'), None),
    ]

    return render(request, 'users.html', {
        'users': users,
        'table_headers': table_headers,
        'sort_option': sort_option,
        'sort_dir': sort_dir,
        'page': page,
    })


@login_required(login_url='/login/')
def new_user(request):
    # Only admins or managers can make new users
    if not request.user.is_manager():
        return redirect('home')

    form = UserCreationForm(request.POST or None)

    # Disable superuser field for non-admin users
    if not request.user.is_superuser:
        form.fields['is_superuser'].disabled = True

    if form.is_valid():
        user = form.save(commit=False)

        # Avoid superuser creation from non-admin user
        if not request.user.is_superuser:
            user.is_superuser = False

        user.save()

        # Add user groups
        for group_id in form.cleaned_data['groups']:
            group = Group.objects.get(id=group_id)
            user.groups.add(group)

        return redirect('users')

    return render(request, 'new_user.html', {'form': form})


@login_required(login_url='/login/')
def edit_user(request, pk):
    # Only admins or managers can make new users
    if not request.user.is_manager():
        return redirect('home')

    instance = get_object_or_404(User, pk=pk)
    current_groups = list(instance.groups.values_list('id', flat=True))
    current_is_superuser = instance.is_superuser
    form = UserChangeForm(
        request.POST or None,
        instance=instance,
        initial={'groups': current_groups},
    )

    # Disable superuser field for non-admin users
    if not request.user.is_superuser:
        form.fields['is_superuser'].disabled = True

    if form.is_valid():
        user = form.save(commit=False)

        # Change password if requested
        password = request.POST.get('password', '')
        if password != '':
            user.set_password(password)

        # Avoid is_superuser change from non-admin user
        if not request.user.is_superuser:
            user.is_superuser = current_is_superuser

        user.save()

        # Update user groups. Groups from the form is a
        # list of strings but the existing groups is a
        # list of integers, therefore some conversion is
        # needed in the if conditions bellow.
        new_groups = form.cleaned_data['groups']
        for group_id in new_groups:
            # Do not add already added groups
            if int(group_id) not in current_groups:
                group = Group.objects.get(id=group_id)
                user.groups.add(group)
        # Remove groups not present in new_groups
        for group_id in current_groups:
            if str(group_id) not in new_groups:
                group = Group.objects.get(id=group_id)
                user.groups.remove(group)

        return redirect('users')

    return render(request, 'edit_user.html', {'form': form})


@login_required(login_url='/login/')
def search(request):
    # Sort options
    sort_options = {
        'path': 'filepath.raw',
        'format': 'fileformat.raw',
        'size': 'size_bytes',
        'date': 'datemodified.raw',
    }
    sort_option, sort_dir = get_sort_params(request, sort_options, 'path')
    sort_field = sort_options.get(sort_option)

    # Search
    search = DigitalFile.es_doc.search()
    # Exclude DigitalFiles in DIPs with 'PENDING' or 'FAILURE' import
    # status when the user is not an editor or an administrator.
    if not request.user.is_editor():
        search = search.exclude(
            'terms',
            **{'dip.import_status': [DIP.IMPORT_PENDING, DIP.IMPORT_FAILURE]},
        )
    fields = ['filepath', 'fileformat', 'datemodified', 'dip.identifier']
    search = add_query_to_search(search, request, fields)
    search = search.sort({sort_field: {'order': sort_dir}})

    # Pagination
    page = get_page_from_search(search, request)
    digital_files = page.object_list.execute()

    table_headers = [
        (_('Filepath'), 'path'),
        (_('Format'), 'format'),
        (_('Size (bytes)'), 'size'),
        (_('Last modified'), 'date'),
        (_('View parent folder'), None),
        (_('File details'), None),
    ]

    return render(request, 'search.html', {
        'digital_files': digital_files,
        'table_headers': table_headers,
        'sort_option': sort_option,
        'sort_dir': sort_dir,
        'page': page,
        'statuses': DIP.import_statuses(),
    })


@login_required(login_url='/login/')
def collection(request, pk):
    collection = get_object_or_404(Collection, pk=pk)

    # Sort options
    sort_options = {
        'identifier': 'dc.identifier.raw',
        'title': 'dc.title.raw',
    }
    sort_option, sort_dir = get_sort_params(request, sort_options, 'identifier')
    sort_field = sort_options.get(sort_option)

    # Search
    search = DIP.es_doc.search().query(
        'match',
        **{'collection.id': pk},
    )
    # Exclude DIPs with 'PENDING' or 'FAILURE' import status
    # when the user is not an editor or an administrator.
    if not request.user.is_editor():
        search = search.exclude(
            'terms',
            import_status=[DIP.IMPORT_PENDING, DIP.IMPORT_FAILURE],
        )
    search = add_query_to_search(search, request, ['dc.*'])
    search = search.sort({sort_field: {'order': sort_dir}})

    # Pagination
    page = get_page_from_search(search, request)
    dips = page.object_list.execute()

    table_headers = [
        (_('Identifier'), 'identifier'),
        (_('Title'), 'title'),
        (_('Date'), None),
        (_('Description'), None),
        (_('Details'), None),
    ]

    return render(request, 'collection.html', {
        'collection': collection,
        'dips': dips,
        'table_headers': table_headers,
        'sort_option': sort_option,
        'sort_dir': sort_dir,
        'page': page,
        'statuses': DIP.import_statuses(),
    })


@login_required(login_url='/login/')
def dip(request, pk):
    dip = get_object_or_404(DIP, pk=pk)

    # Redirect to the collection page if the DIP is not visible
    if not dip.is_visible_by_user(request.user):
        return redirect('collection', pk=dip.collection.pk)

    # Show notification to user about import error
    if dip.import_status == DIP.IMPORT_FAILURE:
        messages.error(request, dip.get_import_error_message())

    # Sort options
    sort_options = {
        'path': 'filepath.raw',
        'format': 'fileformat.raw',
        'size': 'size_bytes',
        'date': 'datemodified.raw',
    }
    sort_option, sort_dir = get_sort_params(request, sort_options, 'path')
    sort_field = sort_options.get(sort_option)

    # Search
    search = DigitalFile.es_doc.search().query(
        'match',
        **{'dip.id': pk},
    )
    fields = ['filepath', 'fileformat', 'datemodified', 'dip.identifier']
    search = add_query_to_search(search, request, fields)
    search = search.sort({sort_field: {'order': sort_dir}})

    # Pagination
    page = get_page_from_search(search, request)
    digital_files = page.object_list.execute()

    table_headers = [
        (_('Filepath'), 'path'),
        (_('Format'), 'format'),
        (_('Size (bytes)'), 'size'),
        (_('Last modified'), 'date'),
        (_('Details'), None),
    ]

    return render(request, 'dip.html', {
        'dip': dip,
        'digital_files': digital_files,
        'table_headers': table_headers,
        'sort_option': sort_option,
        'sort_dir': sort_dir,
        'page': page,
        'statuses': DIP.import_statuses(),
    })


@login_required(login_url='/login/')
def digital_file(request, pk):
    digitalfile = get_object_or_404(DigitalFile, pk=pk)

    # Redirect to the collection page if the related DIP is not visible
    if not digitalfile.dip.is_visible_by_user(request.user):
        return redirect('collection', pk=digitalfile.dip.collection.pk)

    # Show notification to user about import error
    if digitalfile.dip.import_status == DIP.IMPORT_FAILURE:
        messages.error(request, digitalfile.dip.get_import_error_message())

    return render(request, 'digitalfile.html', {
        'digitalfile': digitalfile,
    })


@login_required(login_url='/login/')
def new_collection(request):
    # Only admins and users in group "Editors"
    # can add collections
    if not request.user.is_editor():
        return redirect('home')

    CollectionForm = modelform_factory(Collection, fields=('link',))
    collection_form = CollectionForm(request.POST or None)
    DublinCoreForm = modelform_factory(DublinCore, exclude=())
    dc_form = DublinCoreForm(request.POST or None)

    if request.method == 'POST' and collection_form.is_valid() and dc_form.is_valid():
        collection = collection_form.save(commit=False)
        collection.dc = dc_form.save()
        collection.save()

        return redirect('home')

    return render(
        request,
        'new_collection.html',
        {'collection_form': collection_form, 'dc_form': dc_form}
    )


@login_required(login_url='/login/')
def new_dip(request):
    # Only admins and users in group "Editors"
    # can add DIPs
    if not request.user.is_editor():
        return redirect('home')

    DIPForm = modelform_factory(
        DIP,
        fields=('collection', 'objectszip',),
    )
    dip_form = DIPForm(request.POST or None, request.FILES or None)
    DublinCoreForm = modelform_factory(DublinCore, fields=('identifier',))
    dc_form = DublinCoreForm(request.POST or None)

    if request.method == 'POST' and dip_form.is_valid() and dc_form.is_valid():
        dip = dip_form.save(commit=False)
        dip.dc = dc_form.save()
        # TODO: Avoid this save from updating the related ES
        # documents, as a later save when the async_result id
        # is added, will repeat the process. It may require
        # stop using signals and move to a custom save method.
        dip.save()

        # Extract and parse METS file asynchronously
        async_result = extract_and_parse_mets.delay(dip.pk, dip.objectszip.path)
        # Save the async_result id to relate later with the TaskResult
        # related object, which is not created on task call. Celery docs
        # recommend to call get() or forget() on AsyncResult to free the
        # backend resources used to store and transmit results, but the
        # former waits for the task completion and the later may remove
        # the result in the backend and the database. The only solution
        # I could find is to rely on the `__del__` method, which cancels
        # pending operations over the AsyncResult but doesn't delete the
        # related TaskResult from the database.
        dip.import_task_id = async_result.id
        dip.import_status = DIP.IMPORT_PENDING
        dip.save()

        # Show notification to user about import in progress
        messages.info(request, _(
            'A background process has been launched to extract and parse '
            'the METS file. After the process finishes and the interface '
            'is reloaded, a link to the Folder will show up in the '
            'Folders table at the related Collection page.'
        ))

        return redirect('collection', pk=dip.collection.pk)

    return render(
        request,
        'new_dip.html',
        {'dip_form': dip_form, 'dc_form': dc_form}
    )


@login_required(login_url='/login/')
def edit_collection(request, pk):
    # Only admins and users in group "Editors"
    # can edit collections
    if not request.user.is_editor():
        return redirect('collection', pk=pk)

    collection = get_object_or_404(Collection, pk=pk)
    CollectionForm = modelform_factory(Collection, fields=('link',))
    collection_form = CollectionForm(request.POST or None, instance=collection)
    DublinCoreForm = modelform_factory(DublinCore, exclude=())
    dc_form = DublinCoreForm(request.POST or None, instance=collection.dc)

    if request.method == 'POST' and collection_form.is_valid() and dc_form.is_valid():
        dc_form.save()
        collection_form.save()

        return redirect('collection', pk=pk)

    return render(
        request,
        'edit_collection.html',
        {'collection_form': collection_form, 'dc_form': dc_form, 'collection': collection}
    )


@login_required(login_url='/login/')
def edit_dip(request, pk):
    # Only admins and users in group "Editors"
    # can edit DIPs
    if not request.user.is_editor():
        return redirect('dip', pk=pk)

    dip = get_object_or_404(DIP, pk=pk)
    DublinCoreForm = modelform_factory(DublinCore, exclude=())
    dc_form = DublinCoreForm(request.POST or None, instance=dip.dc)

    if request.method == 'POST' and dc_form.is_valid():
        dc_form.save()
        # Trigger ES update
        dip.save()
        return redirect('dip', pk=pk)

    return render(request, 'edit_dip.html', {'form': dc_form, 'dip': dip})


@login_required(login_url='/login/')
def delete_collection(request, pk):
    # Only admins can delete collections
    if not request.user.is_superuser:
        return redirect('collection', pk=pk)

    collection = get_object_or_404(Collection, pk=pk)
    dc = get_object_or_404(DublinCore, pk=collection.dc_id)
    form = DeleteByDublinCoreForm(
        request.POST or None,
        instance=dc,
        initial={'identifier': ''},
    )
    if form.is_valid():
        collection.delete()
        return redirect('home')

    return render(
        request,
        'delete_collection.html',
        {'form': form, 'collection': collection},
    )


@login_required(login_url='/login/')
def delete_dip(request, pk):
    # Only admins can delete DIPs
    if not request.user.is_superuser:
        return redirect('dip', pk=pk)

    dip = get_object_or_404(DIP, pk=pk)
    dc = get_object_or_404(DublinCore, pk=dip.dc_id)
    form = DeleteByDublinCoreForm(
        request.POST or None,
        instance=dc,
        initial={'identifier': ''},
    )
    if form.is_valid():
        dip.delete()
        return redirect('home')

    return render(request, 'delete_dip.html', {'form': form, 'dip': dip})
