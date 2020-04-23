from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from modeltranslation.forms import TranslationModelForm

from .models import Content
from .models import DublinCore
from .models import Setting
from .models import User


class DeleteByDublinCoreForm(forms.ModelForm):
    class Meta:
        model = DublinCore
        fields = ["identifier"]
        labels = {"identifier": _("Identifier")}

    def clean_identifier(self):
        if self.instance.identifier != self.cleaned_data["identifier"]:
            raise forms.ValidationError(_("Identifier does not match"))
        return self.cleaned_data["identifier"]


class UserForm(UserCreationForm):
    """Form used for user creation and edit.

    It uses UserCreationForm as base for both cases to allow editing the user
    password on edit. The password fields are required on creation but not on
    edit, when the password will only be updated if the fields are populated.
    """

    is_superuser = forms.BooleanField(required=False, label=_("Administrator"))

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "is_superuser",
            "groups",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        # Get and add initial groups (must be done before super init)
        self.initial_groups = []
        if "instance" in kwargs:
            self.initial_groups = list(
                kwargs["instance"].groups.values_list("id", flat=True)
            )
            kwargs["initial"] = {"groups": self.initial_groups}
        super().__init__(*args, **kwargs)
        # Add group fields (must be done after super init)
        self.fields["groups"] = forms.MultipleChoiceField(
            choices=Group.objects.all().values_list("id", "name"),
            required=False,
            label=_("Groups"),
            help_text=_("Ctrl + Click to select multiple or unselect."),
        )
        # Do not require password fields when editing
        if "instance" in kwargs:
            self.fields["password1"].required = False
            self.fields["password2"].required = False

    def save(self):
        # Call ModelForm save directly to avoid setting the
        # user password allways in UserCreationForm save.
        user = super(UserCreationForm, self).save(commit=False)
        # Only set the password when it's populated. It's required on creation.
        password = self.cleaned_data.get("password1", "")
        if password != "":
            user.set_password(password)
        user.save()
        # Process user groups. Groups from the form is a
        # list of strings but the existing groups is a
        # list of integers, therefore some conversion is
        # needed in the if conditions bellow.
        if "groups" in self.cleaned_data:
            for group_id in self.cleaned_data["groups"]:
                # Do not add already added groups
                if int(group_id) not in self.initial_groups:
                    group = Group.objects.get(id=group_id)
                    user.groups.add(group)
            # Remove groups not present in new_groups
            for group_id in self.initial_groups:
                if str(group_id) not in self.cleaned_data["groups"]:
                    group = Group.objects.get(id=group_id)
                    user.groups.remove(group)
        return user


class SettingsForm(forms.Form):
    """Base form for `models.Setting` management.

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
        label=_("Optional fields"),
        help_text=_("Ctrl + Click to select multiple or unselect."),
        choices=DublinCore.get_optional_fields().items(),
    )
    hide_empty_dc_fields = forms.BooleanField(
        required=False,
        label=_("Hide empty fields"),
        help_text=_(
            "Check to not display Dublin Core fields without data "
            "in the Collection and Folder view pages."
        ),
    )


class ContentForm(TranslationModelForm):
    class Meta:
        model = Content
        fields = ("content",)
