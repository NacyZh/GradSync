from .models import PaperImportJob


def get_paper_import_job(import_job_id: int) -> PaperImportJob:
    return PaperImportJob.objects.select_related(
        "paper_file",
        "accepted_paper",
        "duplicate_paper",
        "requested_by",
    ).get(pk=import_job_id)
