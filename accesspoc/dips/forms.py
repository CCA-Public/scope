from django.contrib.auth.models import User
from django import forms
from .models import Department, Collection, DIP

class DepartmentForm(forms.ModelForm):

    class Meta:
        model = Department
        fields = ['name']

class CollectionForm(forms.ModelForm):
    
    dcformat = forms.CharField(widget=forms.Textarea(), 
        label="Format", max_length=4000, required=False)
    description = forms.CharField(widget=forms.Textarea(), 
        max_length=4000, required=False)

    class Meta:
        model = Collection
        fields = ['identifier', 'ispartof', 'title', 'creator', 
        'subject', 'description', 'publisher', 'contributor', 
        'date', 'dctype', 'dcformat', 'source', 'language', 
        'coverage', 'rights', 'link']
        labels = {
            "ispartof": "Department", 
            "dctype": "Type"
        }

class DIPForm(forms.ModelForm):
    
    dcformat = forms.CharField(widget=forms.Textarea(), 
        label="Format", max_length=4000, required=False)
    description = forms.CharField(widget=forms.Textarea(), 
        max_length=4000, required=False)

    class Meta:
        model = DIP
        fields = ['identifier', 'ispartof', 'metsfile', 'objectszip', 
        'title', 'creator', 'subject', 'description', 'publisher', 
        'contributor', 'date', 'dctype', 'dcformat', 'source', 
        'language', 'coverage', 'rights']
        labels = {
            "ispartof": "Collection", 
            "metsfile": "METS file", 
            "objectszip": "Objects zip file", 
            "dctype": "Type"
        }

class DeleteCollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ['identifier']

class DeleteDIPForm(forms.ModelForm):
    class Meta:
        model = DIP
        fields = ['identifier']