export async function registerServiceWorker() {
  if (!import.meta.env.PROD || !('serviceWorker' in navigator)) return undefined;
  return navigator.serviceWorker.register('/sw.js', { scope: '/', updateViaCache: 'none' });
}
