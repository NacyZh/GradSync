from dataclasses import dataclass

from apps.projects.permissions import can_access_project_only_material, is_active_user


@dataclass(frozen=True)
class LegacyLinkResolution:
    outcome: str
    target_url: str
    message: str
    status_code: int


SECTION_TARGETS = {
    "papers": "/library/papers",
    "code": "/library/code",
    "documents": "/library/documents",
    "writing": "/writing",
}


def resolve_legacy_project_link(*, user, project, section: str) -> LegacyLinkResolution:
    if not is_active_user(user):
        return LegacyLinkResolution(
            outcome="denied",
            target_url="",
            message="Sign in with an active account to access this workspace.",
            status_code=403,
        )
    target = SECTION_TARGETS.get(section)
    if not target:
        return LegacyLinkResolution(
            outcome="guidance",
            target_url="",
            message="This project link no longer maps to a shared workspace section.",
            status_code=404,
        )
    if section == "writing":
        return LegacyLinkResolution(
            outcome="guidance",
            target_url=target,
            message="Writing now uses participant access in the standalone writing workspace.",
            status_code=200,
        )
    if not can_access_project_only_material(user, project):
        return LegacyLinkResolution(
            outcome="denied",
            target_url=target,
            message=(
                "Open the standalone shared section. "
                "Private project material details are hidden."
            ),
            status_code=403,
        )
    return LegacyLinkResolution(
        outcome="redirect",
        target_url=target,
        message="This workspace section moved out of project navigation.",
        status_code=200,
    )
