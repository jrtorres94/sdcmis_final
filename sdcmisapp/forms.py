from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model, authenticate # Import get_user_model and authenticate

from .models import iec_records, CustomUser, PreChargeInvestigation


from django import forms
from django.forms.widgets import PasswordInput, TextInput, DateInput, Select

from django.forms import Select


# register user


class CreateUserForm(UserCreationForm):
    
        class Meta:

            model = CustomUser
            fields = ['username','first_name','last_name','designation','location', 'role'] # Removed password fields, UserCreationForm handles them

        def save(self, commit=True):
            user = super().save(commit=False)
            user.is_active = False  # Set user to inactive by default
            if commit:
                user.save()
            return user




        
# login a user


class Loginform(AuthenticationForm):
   
    username = forms.CharField(widget=TextInput())
    password = forms.CharField(widget=PasswordInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customize the error message for inactive users
        self.error_messages['inactive'] = "Your account is awaiting admin approval. Please wait or contact support."

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            # authenticate() will return None if user is inactive (due to ModelBackend's user_can_authenticate)
            # or if credentials are bad / user doesn't exist.
            self.user_cache = authenticate(self.request, username=username, password=password)

            if self.user_cache is None:
                # Since authenticate returned None, we need to figure out why.
                # Was it an inactive user with correct password, or genuinely bad credentials?
                UserModel = get_user_model() # This will be CustomUser
                try:
                    user = UserModel._default_manager.get_by_natural_key(username)
                    # We found a user by that username.
                    # Now, check if the password was correct for this user.
                    if user.check_password(password):
                        # Password is correct. If they are inactive, this is the scenario we want to customize.
                        if not user.is_active:
                            raise forms.ValidationError(
                                self.error_messages['inactive'],
                                code='inactive',
                            )
                        # If user is active and password correct, authenticate should have returned the user.
                        # This path implies an unexpected state, so fall through to generic invalid login.
                except UserModel.DoesNotExist:
                    # User does not exist. Fall through to generic invalid login.
                    pass # The self.get_invalid_login_error() below will handle this.
                raise self.get_invalid_login_error() # Default error if not specifically an inactive user with correct pass
            else:
                self.confirm_login_allowed(self.user_cache) # Standard check for active users
        return self.cleaned_data
    

#IEC ADDFORM

class IEC_AddForm(forms.ModelForm):

     class Meta:

        model = iec_records
        fields = ['date_received', 'complainant', 'respondent', 'charge', 'remarks']
        widgets = {
            'date_received': forms.DateInput(attrs={'type': 'date'}),
        }


#IEC UPDATEFORM

class IEC_UpdateForm(forms.ModelForm):

     class Meta:

        model = iec_records
        fields = ['date_received', 'complainant', 'respondent', 'charge', 'remarks']
        widgets = {
            'date_received': forms.DateInput(attrs={'type': 'date'}),
        }

# FORM FOR ROUTING TASK AND SELECTING NEXT ASSIGNEE
class RouteTaskForm(forms.Form):
    assign_to = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(),  # Queryset will be set dynamically in the view
        label="Assign to:",
        widget=forms.Select(attrs={'class': 'form-control'}), # Optional: for styling
        required=True,
        empty_label="Select a user" # Optional: placeholder text
    )
    director_approval_date = forms.DateField(
        label="IER Approved by Director On",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False # Make it optional
    )
    submission_remarks = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label="Submission Remarks",
        required=False
    )


    def __init__(self, *args, **kwargs):
        eligible_users_queryset = kwargs.pop('eligible_users_queryset', None)
        super().__init__(*args, **kwargs)
        if eligible_users_queryset is not None:
            self.fields['assign_to'].queryset = eligible_users_queryset


class NoticePCISubmissionForm(forms.ModelForm):
    class Meta:
        model = PreChargeInvestigation
        fields = [
            'precharge_no',
            'notice_pci_respondent_received_on',
            'notice_pci_remarks'
        ]
        widgets = {
            'precharge_no': forms.TextInput(attrs={'class': 'form-control'}),
            'notice_pci_respondent_received_on': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notice_pci_remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'precharge_no': "Pre-Charge Investigation No. (PCIR No.)",
            'notice_pci_respondent_received_on': "Date Notice of PCI Received by Respondent",
            'notice_pci_remarks': "Remarks for Notice of PCI Submission",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['precharge_no'].required = True # Assuming this should be confirmed/entered here
        self.fields['notice_pci_respondent_received_on'].required = False
        self.fields['notice_pci_remarks'].required = False


class CommentCounterAffidavitSubmissionForm(forms.ModelForm):
    class Meta:
        model = PreChargeInvestigation
        fields = [
            'comment_counter_affidavit_received_on',
            # 'comment_counter_affidavit_received_from', # Removed this line
            'comment_counter_affidavit_remarks'
        ]
        widgets = {
            'comment_counter_affidavit_received_on': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            # 'comment_counter_affidavit_received_from': forms.TextInput(attrs={'class': 'form-control'}), # Removed this line
            'comment_counter_affidavit_remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'comment_counter_affidavit_received_on': "Date Comment/Counter Affidavit Received",
            # 'comment_counter_affidavit_received_from': "Comment/Counter Affidavit Received From", # Removed this line
            'comment_counter_affidavit_remarks': "Remarks for Comment/Counter Affidavit Submission",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['comment_counter_affidavit_received_on'].required = False # Optional, in case no comment is filed
        # self.fields['comment_counter_affidavit_received_from'].required = False # Removed this line
        self.fields['comment_counter_affidavit_remarks'].required = False