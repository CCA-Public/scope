from django.contrib.auth.models import Group
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import UserChangeForm
from django.utils.translation import gettext_lazy as _
from django import forms
from .models import User, DublinCore, Setting


class DeleteByDublinCoreForm(forms.ModelForm):
    class Meta:
        model = DublinCore
        fields = ['identifier']
        labels = {
            'identifier': _('Identifier'),
        }

    def clean_identifier(self):
        if self.instance.identifier != self.cleaned_data['identifier']:
            raise forms.ValidationError(_('Identifier does not match'))
        return self.cleaned_data['identifier']


class UserCreationForm(UserCreationForm):
    is_superuser = forms.BooleanField(required=False, label=_('Administrator'))

    def __init__(self, *args, **kwargs):
        super(UserCreationForm, self).__init__(*args, **kwargs)
        self.fields['groups'] = forms.MultipleChoiceField(
            choices=Group.objects.all().values_list('id', 'name'),
            required=False,
            label=_('Groups'),
            help_text=_('Ctrl + Click to select multiple or unselect.'),
        )

    def clean_password1(self):
        data = self.cleaned_data['password1']
        if data != '' and len(data) < 8:
            raise forms.ValidationError(_('Password should be at least 8 characters long'))
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
    is_superuser = forms.BooleanField(required=False, label=_('Administrator'))

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
            label=_('Groups'),
            help_text=_('Ctrl + Click to select multiple or unselect.'),
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
            raise forms.ValidationError(_('Password should be at least 8 characters long'))
        return data

    def clean(self):
        cleaned_data = super(UserChangeForm, self).clean()
        if cleaned_data.get('password') != '' or cleaned_data.get('password_confirmation') != '':
            if cleaned_data.get('password') != cleaned_data.get('password_confirmation'):
                raise forms.ValidationError(_('Password and password confirmation do not match'))
        return cleaned_data

    def save(self, commit=True):
        user = super(UserChangeForm, self).save(commit=False)
        if commit:
            user.save()
        return user


class SettingsForm(forms.Form):
    """
    Base form for `models.Setting` management:

    - Field names declared in sub-forms must match the setting names.
    - The field type and other properties must be defined in the sub-forms
      based on the related setting expected value type.
    - The `Setting.value` is a JSONField (only with auto encoding/decoding
      capabilities); the initial value of the form fields will be populated
      with the decoded setting value and the encoded form field value will be
      saved on form submission.
    """
    settings = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            self.settings[name] = Setting.objects.get(name=name)
            field.initial = self.settings[name].value

    def save(self):
        for name, field in self.fields.items():
            self.settings[name].value = self.cleaned_data[name]
            self.settings[name].save()


class DublinCoreSettingsForm(SettingsForm):
    enabled_optional_dc_fields = forms.MultipleChoiceField(
        required=False,
        label=_('Optional fields'),
        help_text=_('Ctrl + Click to select multiple or unselect.'),
        choices=DublinCore.get_optional_fields().items(),
    )
    hide_empty_dc_fields = forms.BooleanField(
        required=False,
        label=_('Hide empty fields'),
        help_text=_(
            'Check to not display Dublin Core fields without data '
            'in the Collection and Folder view pages.'
        ),
    )
