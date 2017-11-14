from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from .models import Department, Collection, DIP, DigitalFile
from .forms import DepartmentForm, CollectionForm, DIPForm, DeleteCollectionForm, DeleteDIPForm, UserCreationForm, UserChangeForm
from .parsemets import METS, convert_size

import os

@login_required(login_url='/login/')
def home(request):
    collections = Collection.objects.all().order_by('identifier')
    dept_ids = Collection.objects.order_by('ispartof').values('ispartof').distinct()
    departments = [Department.objects.get(id=dept['ispartof']) for dept in dept_ids]
    return render(request, 'home.html', {'collections': collections, 
        'departments': departments})

def faq(request):
    return render(request, 'faq.html')

@login_required(login_url='/login/')
def users(request):
    # only admins can see users
    if request.user.is_superuser:
        users = User.objects.all()
        return render(request, 'users.html', {'users': users})
    else:
        return redirect('home')

@login_required(login_url='/login/')
def new_user(request):
    # only admins can make new users
    if request.user.is_superuser:
        if request.method == 'POST':
            form = UserCreationForm(request.POST)
            if form.is_valid():
                user = form.save()
                return redirect('users')
        else:
            form = UserCreationForm()
            return render(request, 'new_user.html', {'form': form})
    else:
        return redirect('home')

@login_required(login_url='/login/')
def edit_user(request, pk):
    # only admins can edit records
    if request.user.is_superuser:
        instance = get_object_or_404(User, pk=pk)
        form = UserChangeForm(request.POST or None, instance=instance)
        if form.is_valid():
            user = form.save(commit=False)

            # change password if requested
            password = request.POST.get('password', '')
            if password != '':
                user.set_password(password)

            # prevent non-admin from self-promotion
            if not request.user.is_superuser:
                user.is_superuser = False

            user.save()

            return redirect('users')
        return render(request, 'edit_user.html', {'form': form})
    else:
        return redirect('home')

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
    return render(request, 'digitalfile.html', {'digitalfile': digitalfile})

@login_required(login_url='/login/')
def new_department(request):
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            department = form.save()
            return redirect('home')
    else:
        form = DepartmentForm()
    return render(request, 'new_department.html', {'form': form})

@login_required(login_url='/login/')
def new_collection(request):
    if request.method == 'POST':
        form = CollectionForm(request.POST)
        if form.is_valid():
            collection = form.save()
            return redirect('home')
    else:
        form = CollectionForm()
    return render(request, 'new_collection.html', {'form': form})

@login_required(login_url='/login/')
def new_dip(request):
    if request.method == 'POST':
        form = DIPForm(request.POST, request.FILES)
        if form.is_valid():
            collection = form.save()
            metspath = os.path.join(settings.MEDIA_ROOT, request.FILES['metsfile'].name)
            mets = METS(metspath, request.POST.get('identifier'))
            mets.parse_mets()
            return redirect('home')
    else:
        form = DIPForm()
    return render(request, 'new_dip.html', {'form': form})

@login_required(login_url='/login/')
def edit_collection(request, identifier):
    # only admins and users in group "Edit Collections and Folders" can edit records
    if request.user.groups.filter(name__in=['Edit Collections and Folders']).exists() or request.user.is_superuser:
        instance = get_object_or_404(Collection, identifier=identifier)
        form = CollectionForm(request.POST or None, instance=instance)
        if form.is_valid():
            form.save()
            return redirect('collection', identifier=identifier)
        return render(request, 'edit_collection.html', {'form': form})
    else:
        return redirect('collection', identifier=identifier)

@login_required(login_url='/login/')
def edit_dip(request, identifier):
    # only admins and users in group "Edit Collections and Folders" can edit records
    if request.user.groups.filter(name__in=['Edit Collections and Folders']).exists() or request.user.is_superuser:
        instance = get_object_or_404(DIP, identifier=identifier)
        form = DIPForm(request.POST or None, instance=instance)
        if form.is_valid():
            form.save()
            return redirect('dip', identifier=identifier)
        return render(request, 'edit_dip.html', {'form': form})
    else:
        return redirect('dip', identifier=identifier)

@login_required(login_url='/login/')
def delete_collection(request, identifier):
    # only admins can delete records
    if request.user.is_superuser:
        instance = get_object_or_404(Collection, identifier=identifier)
        form = DeleteCollectionForm(request.POST or None, instance=instance)
        if form.is_valid():
            instance.delete()
            return redirect('home')
        return render(request, 'delete_collection.html', {'form': form})
    else:
        return redirect('collection', identifier=identifier)

@login_required(login_url='/login/')
def delete_dip(request, identifier):
    # only admins can delete records
    if request.user.is_superuser:
        instance = get_object_or_404(DIP, identifier=identifier)
        form = DeleteDIPForm(request.POST or None, instance=instance)
        if form.is_valid():
            instance.delete()
            return redirect('home')
        return render(request, 'delete_dip.html', {'form': form})
    else:
        return redirect('dip', identifier=identifier)
