export const productionChunkSizeWarningLimit = 450;

export function productionManualChunks(id: string) {
  if (id.includes('node_modules')) {
    return 'vendor';
  }
  if (id.includes('/src/features/submissions/')) return 'workspace-submissions';
  if (id.includes('/src/features/resources/')) return 'workspace-resources';
  if (id.includes('/src/features/admin/')) return 'workspace-admin';
}
