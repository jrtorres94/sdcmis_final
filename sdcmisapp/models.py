from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from datetime import date # For generating year in iec_ref
from django.conf import settings # To refer to AUTH_USER_MODEL
from .workflow_def import get_status_choices, get_initial_status_key


# Create your models here.

# Custom User registration
class CustomUser(AbstractUser):
    LOCATION_CHOICES = [
        ('co', 'CENTRAL OFFICE'),
        ('ncr', 'NATIONAL CAPITAL REGION'),
        ('car', 'CORDILLERA ADMINISTRATIVE REGION'),
        ('r1', 'Region 1'),
        ('r2', 'Region 2'),
        ('r3', 'Region 3'),
        ('r4a', 'CALABARZON'),
        ('r4b', 'MIMAROPA'),
        ('r5', 'Region 5'),
        ('r6', 'Region 6'),
        ('r7', 'Region 7'),
        ('r8', 'Region 8'),
        ('r9', 'Region 9'),
        ('r10', 'Region 10'),
        ('r11', 'Region 11'),
        ('r12', 'Region 12'),
        ('r13', 'Region 13'),
        ('barmm', 'BANGSAMORO AUTONOMOUS REGION IN MUSLIM MINDANAO'),
    ]
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('ier_inv', 'Initial Evaluator'),
        ('pci_inv', 'PCI Investigator'),
        ('dir', 'Director'),
        ('sho', 'Summary Hearing Officer'),
        ('comr', 'Commissioner'),
        
    ]

    designation = models.CharField(max_length=100)
    location = models.CharField(max_length=10, choices=LOCATION_CHOICES, blank=False, null=True) # Max length for keys
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=False, null=True)
    
    # Explicitly define groups and user_permissions to avoid potential reverse accessor clashes
    # and to ensure clarity, especially when extending AbstractUser.
    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        help_text=(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="customuser_groups_set", # Unique related_name
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="customuser_permissions_set", # Unique related_name
        related_query_name="user",
    )

# iec records
class iec_records(models.Model):
    STATUS_CHOICES = get_status_choices() # Define choices using the imported function

    date_created = models.DateTimeField(auto_now_add=True) # Set on creation, not on every save
    date_received = models.DateField()
    iec_ref = models.CharField(max_length=50, unique=True, editable=False, blank=True) # Auto-generated
    complainant = models.CharField(max_length=100)
    respondent = models.CharField(max_length=100)
    charge = models.CharField(max_length=100)
    remarks = models.TextField(blank= True, null=True)
    # is_completed = models.BooleanField(default=False) # Consider deriving from status
    due_date = models.DateField(null=True, blank=True) # Allow due_date to be initially null
    status = models.CharField(max_length=100, choices=STATUS_CHOICES, default=get_initial_status_key) # Corrected single definition
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='created_iec_records', on_delete=models.SET_NULL, null=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='assigned_iec_records', on_delete=models.SET_NULL, null=True, blank=True)

    # Removed direct IER fields from here
    # initial_evaluation_submitted_on = models.DateField(null=True, blank=True)
    # initial_evaluation_director_approval_date = models.DateField(null=True, blank=True)
    # initial_evaluation_remarks = models.TextField(blank=True, null=True)
    def __str__(self):
        return f"{self.iec_ref} - {self.complainant} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.pk and not self.iec_ref:  # Only generate if it's a new record and iec_ref isn't already set
            user_location_code = "NOLOC"  # Default if user or user's location is not set

            if self.created_by:
                if self.created_by.location: # Check if location is not None or empty
                    user_location_code = self.created_by.location.upper()
                # If self.created_by exists but self.created_by.location is None/empty, NOLOC is used.
            # If self.created_by is None, NOLOC is used.

            current_year = date.today().year

            base_ref_prefix = f"IEC-{user_location_code}-{current_year}-"

            # Find the last record for this location and year to determine the next sequence number
            last_record = iec_records.objects.filter(
                iec_ref__startswith=base_ref_prefix
            ).order_by('iec_ref').last()

            next_sequence_number = 1
            if last_record and last_record.iec_ref:
                try:
                    # Extract the sequence part from the full iec_ref
                    # Example: IER-NCR-2023-0012 -> 0012
                    sequence_str = last_record.iec_ref.split('-')[-1]
                    next_sequence_number = int(sequence_str) + 1
                except (IndexError, ValueError) as e:
                    # Log this error or handle it. For now, default to 1 if parsing fails.
                    # This might happen if an existing iec_ref has an unexpected format.
                    print(f"Error parsing sequence from {last_record.iec_ref}: {e}") # Consider proper logging
                    pass # next_sequence_number remains 1

            self.iec_ref = f"{base_ref_prefix}{next_sequence_number:04d}"
        super().save(*args, **kwargs)


class InitialEvaluationReport(models.Model):
    """
    Stores details specific to the Initial Evaluation Report (IER) submission.
    """
    iec_record = models.OneToOneField(
        iec_records,
        on_delete=models.CASCADE,
        related_name='initial_evaluation_report_details', # How to access this from iec_records instance
        primary_key=True, # Makes iec_record the PK for this table
    )
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='submitted_iers')
    submitted_on = models.DateField(auto_now_add=True) # Automatically set when the report object is created
    director_approval_date = models.DateField(null=True, blank=True, verbose_name="IER Approved by Director On")
    remarks = models.TextField(blank=True, null=True, verbose_name="Submission Remarks")

    def __str__(self):
        return f"IER for {self.iec_record.iec_ref} submitted by {self.submitted_by.username if self.submitted_by else 'N/A'}"

class PreChargeInvestigation(models.Model):
    """
    Stores details specific to the Pre-Charge Investigation (PCI) phase.
    The 'PCIR ref no' is implicitly the iec_record.iec_ref.
    """
    iec_record = models.OneToOneField(
        iec_records,
        on_delete=models.CASCADE,
        related_name='pre_charge_investigation_details',
        primary_key=True,
    )
    precharge_no = models.CharField(
        max_length=100,
        unique=True, # Ensures this number is unique across all PCI records
        blank=True, # Makes this field required
        null=True,  # Database-level not null
        verbose_name="Pre-Charge Investigation No."
    )

    # Notice of Pre-Charge Investigation
    notice_pci_submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_pci_notices',
        verbose_name="Notice of PCI Submitted By"
    )
    notice_pci_submitted_on = models.DateField(
        null=True, blank=True,
        verbose_name="Notice of PCI Submitted On (by staff)"
    )
    notice_pci_respondent_received_on = models.DateField(
        null=True, blank=True,
        verbose_name="Notice of PCI Received by Respondent On"
    )
    notice_pci_remarks = models.TextField(
        blank=True, null=True,
        verbose_name="Notice of PCI Remarks"
    )

    # Comment/Counter Affidavit
    comment_counter_affidavit_received_on = models.DateField(
        null=True, blank=True,
        verbose_name="Comment/Counter Affidavit Received On"
    )
    comment_counter_affidavit_remarks = models.TextField(
        blank=True, null=True,
        verbose_name="Comment/Counter Affidavit Remarks"
    )

    # PCI Report / Draft Formal Charge
    pci_report_submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_pci_reports',
        verbose_name="PCI Report/Draft Formal Charge Submitted By"
    )
    pci_report_submitted_on = models.DateField(
        null=True, blank=True,
        verbose_name="PCI Report/Draft Formal Charge Submitted On"
    )
    pci_report_remarks = models.TextField(
        blank=True, null=True,
        verbose_name="PCI Report/Draft Formal Charge Remarks"
    )

    def __str__(self):
        return f"PCI No: {self.precharge_no} (IEC Ref: {self.iec_record.iec_ref})"
