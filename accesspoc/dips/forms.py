from django.contrib.auth.models import User
from django import forms
from .models import Department, Collection, DIP

class DepartmentForm(forms.ModelForm):

    class Meta:
        model = Department
        fields = ['name']

class CollectionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(CollectionForm, self).__init__(*args, **kwargs)

        for key in self.fields:
            self.fields[key].required = False

    dcformat = forms.CharField(widget=forms.Textarea(), max_length=4000)
    description = forms.CharField(widget=forms.Textarea(), max_length=4000)

    class Meta:
        model = Collection
        fields = ['identifier', 'ispartof', 'title', 'date', 'dcformat', 
        'description', 'creator', 'link']

class DIPForm(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        super(DIPForm, self).__init__(*args, **kwargs)

        for key in self.fields:
            self.fields[key].required = False

    dcformat = forms.CharField(widget=forms.Textarea(), max_length=4000)
    description = forms.CharField(widget=forms.Textarea(), max_length=4000)

    class Meta:
        model = DIP
        fields = ['identifier', 'ispartof', 'metsfile', 'objectszip', 
        'title', 'date', 'dcformat', 'description', 'creator']

class DeleteCollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ['identifier']

class DeleteDIPForm(forms.ModelForm):
    class Meta:
        model = DIP
        fields = ['identifier']