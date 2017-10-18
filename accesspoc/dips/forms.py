from django.contrib.auth.models import User
from django import forms
from .models import Department, Collection, DIP

class DepartmentForm(forms.ModelForm):

    class Meta:
        model = Department
        fields = ['name']

class CollectionForm(forms.ModelForm):
    extentmedium = forms.CharField(widget=forms.Textarea(), max_length=4000)
    abstract = forms.CharField(widget=forms.Textarea(), max_length=4000)

    class Meta:
        model = Collection
        fields = ['identifier', 'ispartof', 'title', 'date', 'dcformat', 
        'description', 'creator', 'link']

class DIPForm(forms.ModelForm):
    extentmedium = forms.CharField(widget=forms.Textarea(), max_length=4000)
    scopecontent = forms.CharField(widget=forms.Textarea(), max_length=4000)

    class Meta:
        model = DIP
        fields = ['identifier', 'ispartof', 'title', 'date', 'dcformat', 
        'description', 'creator', 'metsfile', 'objectszip']

class DeleteCollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ['identifier']

class DeleteDIPForm(forms.ModelForm):
    class Meta:
        model = DIP
        fields = ['identifier']