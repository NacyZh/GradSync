export type BoundaryFixtureKind =
  | 'standalone_shared'
  | 'standalone_writing'
  | 'project_material_project_only'
  | 'project_material_group_wide'
  | 'pending_review';

export type SourceProjectFixture = {
  id: string;
  title: string;
  visibility: 'project_members' | 'group_wide' | 'not_applicable';
};

export function sharedNavigationFixture() {
  return [
    { label: 'Papers', href: '/library/papers' },
    { label: 'Code', href: '/library/code' },
    { label: 'Documents', href: '/library/documents' },
    { label: 'Writing', href: '/writing' },
  ];
}

export function sourceProjectFixture(overrides: Partial<SourceProjectFixture> = {}): SourceProjectFixture {
  return {
    id: 'project-1',
    title: 'Boundary Mapping Project',
    visibility: 'group_wide',
    ...overrides,
  };
}

export function actionCapabilitiesFixture(overrides: Partial<Record<string, boolean>> = {}) {
  return {
    canView: true,
    canDownload: true,
    canRename: false,
    canDelete: false,
    canUploadGroupWide: false,
    ...overrides,
  };
}

export function sharedAssetFixture(kind: BoundaryFixtureKind = 'standalone_shared') {
  const sourceProject =
    kind === 'project_material_group_wide' || kind === 'project_material_project_only' || kind === 'pending_review'
      ? sourceProjectFixture({
          visibility: kind === 'project_material_project_only' ? 'project_members' : 'group_wide',
        })
      : null;
  return {
    id: `${kind}-asset`,
    title: `${kind.replaceAll('_', ' ')} asset`,
    boundaryType: kind === 'standalone_shared' ? 'standalone_shared' : 'project_material',
    visibility: sourceProject?.visibility ?? 'group_wide',
    sourceProject,
    status: kind === 'pending_review' ? 'pending_review' : 'active',
    actionCapabilities: actionCapabilitiesFixture(),
  };
}

export function writingParticipantFixture(role = 'student_author') {
  return {
    id: `${role}-participant`,
    userId: `${role}-user`,
    participantRole: role,
    status: 'active',
  };
}
