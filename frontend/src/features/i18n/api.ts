import { useMutation, useQuery, useQueryClient, type UseQueryOptions } from '@tanstack/react-query';

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

export function useLocalePreference(
  options: Pick<UseQueryOptions<{ locale: Locale; updatedAt?: string }>, 'enabled'> = {},
) {
  return useQuery({
    queryKey: ['localePreference'],
    queryFn: getLocalePreference,
    enabled: options.enabled ?? true,
  });
}

export function useUpdateLocalePreference() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateLocalePreference,
    onMutate: async (locale) => {
      await queryClient.cancelQueries({ queryKey: ['localePreference'] });
      const previous = queryClient.getQueryData<{ locale: Locale; updatedAt?: string }>([
        'localePreference',
      ]);
      queryClient.setQueryData(['localePreference'], { ...(previous ?? {}), locale });
      return { previous };
    },
    onError: (_error, _locale, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['localePreference'], context.previous);
      }
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['localePreference'] }),
  });
}
