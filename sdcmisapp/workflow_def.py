class TaskStep:
    """
    Represents a single step in a defined workflow,
    including its key, description, and estimated duration.
    """
    def __init__(self, key: str, description: str, days_to_complete: int):
        """
        Initializes a new TaskStep.

        Args:
            key (str): A unique key for this step (e.g., 'initial_evaluation').
            description (str): A human-readable description of the task step.
            days_to_complete (int): The estimated number of days to complete this step.

        Raises:
            ValueError: If key or description is not a non-empty string or
                        if days_to_complete is not a non-negative integer.
        """
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Key must be a non-empty string.")
        if not isinstance(description, str) or not description.strip():
            raise ValueError("Description must be a non-empty string.")
        if not isinstance(days_to_complete, int) or days_to_complete < 0:
            raise ValueError("Days to complete must be a non-negative integer.")

        self.key = key
        self.description = description
        self.days_to_complete = days_to_complete

    def __repr__(self) -> str:
        """
        Returns a string representation of the TaskStep.
        """
        return f"TaskStep(key='{self.key}', description='{self.description}', days_to_complete={self.days_to_complete})"

# Define the standard workflow steps for a case
CASE_WORKFLOW_STEPS = [
    TaskStep("initial_evaluation", "Initial Evaluation Report", 1),
    TaskStep("notice_pci", "Notice of Pre-Charge Investigation", 2),
    TaskStep("comment_counter_affidavit", "Comment/Counter Affidavit", 3),
    TaskStep("pci_report_draft_charge", "PCI Report and/or Draft Formal Charge", 1),
    TaskStep("formal_charge", "Formal Charge", 1),
    TaskStep("assign_hearing_officer", "Assignment of Hearing Officer", 1),
    TaskStep("summons", "Summons", 2),
    TaskStep("answer", "Answer", 7),
    TaskStep("pre_hearing_conference", "Pre-Hearing Conference", 3),
    TaskStep("position_paper", "Position Paper", 7), # Clarified for Hearing Officer
    TaskStep("clarificatory_hearing", "Clarificatory Hearing", 2),
    TaskStep("report_investigation_draft_decision", "Report of Investigation and Draft Decision/Resolution", 7),
    TaskStep("deliberations", "Deliberations", 14),
    TaskStep("resolved", "Resolved", 15),
]

def get_status_choices():
    """Returns a list of choices for the status field based on CASE_WORKFLOW_STEPS."""
    return [(step.key, step.description) for step in CASE_WORKFLOW_STEPS]

def get_initial_status_key():
    """Returns the key of the first step in the workflow."""
    return CASE_WORKFLOW_STEPS[0].key if CASE_WORKFLOW_STEPS else None

def get_task_step_by_key(key: str) -> TaskStep | None:
    """Retrieves a TaskStep object by its key."""
    for step in CASE_WORKFLOW_STEPS:
        if step.key == key:
            return step
    return None