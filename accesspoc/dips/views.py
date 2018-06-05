from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from .models import User, Collection, DIP, DigitalFile
from .forms import CollectionForm, EditDIPForm, NewDIPForm, DeleteCollectionForm, DeleteDIPForm, UserCreationForm, UserChangeForm
from .parsemets import METS

import os
import re
import shutil
import tempfile
import zipfile


@login_required(login_url='/login/')
def home(request):
    collections = Collection.objects.all().order_by('identifier')
    return render(request, 'home.html', {'collections': collections})


def faq(request):
    return render(request, 'faq.html')


@login_required(login_url='/login/')
def users(request):
    # Only admins can see users
    if not request.user.is_superuser:
        return redirect('home')
    users = User.objects.all()
    return render(request, 'users.html', {'users': users})


@login_required(login_url='/login/')
def new_user(request):
    # Only admins can make new users
    if not request.user.is_superuser:
        return redirect('home')

    if not request.method == 'POST':
        form = UserCreationForm()
        return render(request, 'new_user.html', {'form': form})

    form = UserCreationForm(request.POST)
    if form.is_valid():
        form.save()
        return redirect('users')

    return render(request, 'new_user.html', {'form': form})


@login_required(login_url='/login/')
def edit_user(request, pk):
    # Only admins can edit users
    if not request.user.is_superuser:
        return redirect('home')

    instance = get_object_or_404(User, pk=pk)
    current_groups = list(instance.groups.values_list('id', flat=True))
    form = UserChangeForm(
        request.POST or None,
        instance=instance,
        initial={'groups': current_groups},
    )
    if form.is_valid():
        user = form.save(commit=False)

        # Change password if requested
        password = request.POST.get('password', '')
        if password != '':
            user.set_password(password)

        # Prevent non-admin from self-promotion
        if not request.user.is_superuser:
            user.is_superuser = False

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
    digitalfiles = DigitalFile.objects.all()
    return render(request, 'search.html', {'digitalfiles': digitalfiles})


@login_required(login_url='/login/')
def collection(request, identifier):
    collection = get_object_or_404(Collection, identifier=identifier)
    return render(request, 'collection.html', {'collection': collection})


@login_required(login_url='/login/')
def dip(request, identifier):
    dip = get_object_or_404(DIP, identifier=identifier)
    return render(request, 'dip.html', {'dip': dip})


@login_required(login_url='/login/')
def digital_file(request, uuid):
    digitalfile = get_object_or_404(DigitalFile, uuid=uuid)
    dip = DIP.objects.get(identifier=digitalfile.dip)
    return render(request, 'digitalfile.html', {
        'digitalfile': digitalfile,
        'dip': dip,
    })


@login_required(login_url='/login/')
def new_collection(request):
    # Only admins and users in group "Edit Collections and Folders"
    # can add collections
    if not request.user.is_editor():
        return redirect('home')

    if not request.method == 'POST':
        form = CollectionForm(request.POST)
        return render(request, 'new_collection.html', {'form': form})

    form = CollectionForm(request.POST)
    if form.is_valid():
        form.save()
        return redirect('home')

    return render(request, 'new_collection.html', {'form': form})


@login_required(login_url='/login/')
def new_dip(request):
    # Only admins and users in group "Edit Collections and Folders"
    # can add DIPs
    if not request.user.is_editor():
        return redirect('home')

    if not request.method == 'POST':
        form = NewDIPForm()
        return render(request, 'new_dip.html', {'form': form})

    form = NewDIPForm(request.POST, request.FILES)
    if form.is_valid():
        form.save()
        # Extract METS file from DIP objects zip
        tmpdir = tempfile.mkdtemp()
        if not os.path.isdir(tmpdir):
            os.mkdirs(tmpdir)
        objectszip = os.path.join(settings.MEDIA_ROOT, request.FILES['objectszip'].name)
        metsfile = ''
        zip = zipfile.ZipFile(objectszip)
        for info in zip.infolist():
            if re.match(r'.*METS.[0-9a-f\-]{32}.*$', info.filename):
                print('METS file to extract:', info.filename)
                metsfile = zip.extract(info, tmpdir)
        # Parse METS file
        mets = METS(os.path.abspath(metsfile), request.POST.get('identifier'))
        mets.parse_mets()
        # Delete extracted METS file
        shutil.rmtree(tmpdir)
        return redirect('home')

    return render(request, 'new_dip.html', {'form': form})


@login_required(login_url='/login/')
def edit_collection(request, identifier):
    # Only admins and users in group "Edit Collections and Folders"
    # can edit collections
    if not request.user.is_editor():
        return redirect('collection', identifier=identifier)

    instance = get_object_or_404(Collection, identifier=identifier)
    form = CollectionForm(request.POST or None, instance=instance)
    if form.is_valid():
        form.save()
        return redirect('collection', identifier=identifier)

    return render(request, 'edit_collection.html', {'form': form, 'collection': instance})


@login_required(login_url='/login/')
def edit_dip(request, identifier):
    # Only admins and users in group "Edit Collections and Folders"
    # can edit DIPs
    if not request.user.is_editor():
        return redirect('dip', identifier=identifier)

    instance = get_object_or_404(DIP, identifier=identifier)
    form = EditDIPForm(request.POST or None, instance=instance)
    if form.is_valid():
        form.save()
        return redirect('dip', identifier=identifier)

    return render(request, 'edit_dip.html', {'form': form, 'dip': instance})


@login_required(login_url='/login/')
def delete_collection(request, identifier):
    # Only admins can delete collections
    if not request.user.is_superuser:
        return redirect('collection', identifier=identifier)

    instance = get_object_or_404(Collection, identifier=identifier)
    form = DeleteCollectionForm(request.POST or None, instance=instance)
    if form.is_valid():
        instance.delete()
        return redirect('home')

    return render(request, 'delete_collection.html', {'form': form})


@login_required(login_url='/login/')
def delete_dip(request, identifier):
    # Only admins can delete DIPs
    if not request.user.is_superuser:
        return redirect('dip', identifier=identifier)

    instance = get_object_or_404(DIP, identifier=identifier)
    form = DeleteDIPForm(request.POST or None, instance=instance)
    if form.is_valid():
        instance.delete()
        return redirect('home')

    return render(request, 'delete_dip.html', {'form': form})
