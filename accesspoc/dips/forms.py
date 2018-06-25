from django.contrib.auth.models import Group
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import UserChangeForm
from django import forms
from .models import User, DublinCore


class DeleteByDublinCoreForm(forms.ModelForm):
    class Meta:
        model = DublinCore
        fields = ['identifier']

    def clean_identifier(self):
        if self.instance.identifier != self.cleaned_data['identifier']:
            raise forms.ValidationError('Identifier does not match')
        return self.cleaned_data['identifier']


class UserCreationForm(UserCreationForm):
    is_superuser = forms.BooleanField(label='Administrator', required=False)

    def __init__(self, *args, **kwargs):
        super(UserCreationForm, self).__init__(*args, **kwargs)
        self.fields['groups'] = forms.MultipleChoiceField(
            choices=Group.objects.all().values_list('id', 'name'),
            required=False,
            help_text='Ctrl + Click to select multiple or unselect.',
        )

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
        fields = (
            'username', 'first_name', 'last_name',
            'email', 'is_active', 'is_superuser', 'groups',
        )


class UserChangeForm(UserChangeForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    password_confirmation = forms.CharField(widget=forms.PasswordInput, required=False)
    is_superuser = forms.BooleanField(label='Administrator', required=False)

    def __init__(self, *args, **kwargs):
        suppress_administrator_toggle = kwargs.get('suppress_administrator_toggle', False)
        if 'suppress_administrator_toggle' in kwargs:
            del kwargs['suppress_administrator_toggle']

        super(UserChangeForm, self).__init__(*args, **kwargs)
        if suppress_administrator_toggle:
            del self.fields['is_superuser']

        self.fields['groups'] = forms.MultipleChoiceField(
            choices=Group.objects.all().values_list('id', 'name'),
            required=False,
            help_text='Ctrl + Click to select multiple or unselect.',
        )

    class Meta:
        model = User
        fields = (
            'username', 'first_name', 'last_name',
            'email', 'is_active', 'is_superuser', 'groups',
        )

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
