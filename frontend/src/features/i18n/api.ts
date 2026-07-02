import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiRequest } from '../../shared/api/client';

export type Locale = 'en' | 'zh';

export function getLocalePreference() {
  return apiRequest<{ locale: Locale; updatedAt?: string }>('/api/accounts/locale/');
}

export function updateLocalePreference(locale: Locale) {
  return apiRequest<{ locale: Locale; updatedAt?: string }>('/api/accounts/locale/', {
    method: 'PUT',
    body: JSON.stringify({ locale }),
  });
}

export function useLocalePreference() {
  return useQuery({ queryKey: ['localePreference'], queryFn: getLocalePreference });
}

export function useUpdateLocalePreference() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateLocalePreference,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['localePreference'] }),
  });
}
