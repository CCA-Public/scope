from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import UserChangeForm
from django import forms
from .models import Collection, DIP


class CollectionForm(forms.ModelForm):
    
    dcformat = forms.CharField(widget=forms.Textarea(), 
        label="Format", max_length=4000, required=False)
    description = forms.CharField(widget=forms.Textarea(), 
        max_length=4000, required=False)

    class Meta:
        model = Collection
        fields = ['identifier', 'title', 'creator', 
        'subject', 'description', 'publisher', 'contributor', 
        'date', 'dctype', 'dcformat', 'source', 'language', 
        'coverage', 'rights', 'link']
        labels = {
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

class UserCreationForm(UserCreationForm):
    is_superuser = forms.BooleanField(label = 'Administrator',required=False)

    def clean_password1(self):
        data = self.cleaned_data['password1']
        if data != '' and len(data) < 8:
            raise forms.ValidationError('Password should be at least 8 characters long')
        return data

    def save(self, commit=True):
        user = super(UserCreationForm, self).save(commit=False)
        if commit:
            user.save()
        return user

    class Meta:
        model = User
        fields = ('username', 'first_name','last_name','email', 'is_active','is_superuser')

class UserChangeForm(UserChangeForm):
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    password_confirmation = forms.CharField(widget=forms.PasswordInput, required=False)
    is_superuser = forms.BooleanField(label = 'Administrator', required=False)

    def __init__(self, *args, **kwargs):
        suppress_administrator_toggle = kwargs.get('suppress_administrator_toggle', False)

        if 'suppress_administrator_toggle' in kwargs:
            del kwargs['suppress_administrator_toggle']

        super(UserChangeForm, self).__init__(*args, **kwargs)

        if suppress_administrator_toggle:
            del self.fields['is_superuser']

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_active', 'is_superuser')

    def clean_password(self):
        data = self.cleaned_data['password']
        if self.cleaned_data['password'] != '' and len(self.cleaned_data['password']) < 8:
            raise forms.ValidationError('Password should be at least 8 characters long')
        return data

    def clean(self):
        cleaned_data = super(UserChangeForm, self).clean()
        if cleaned_data.get('password') != '' or cleaned_data.get('password_confirmation') != '':
            if cleaned_data.get('password') != cleaned_data.get('password_confirmation'):
                raise forms.ValidationError('Password and password confirmation do not match')
        return cleaned_data

    def save(self, commit=True):
        user = super(UserChangeForm, self).save(commit=False)
        if commit:
            user.save()
        return user