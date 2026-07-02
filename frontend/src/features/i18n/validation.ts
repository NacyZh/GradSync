import type { Locale } from './api';

const messages = {
  en: {
    required: 'This field is required.',
    unsupportedUpload: 'This file type is not supported.',
  },
  zh: {
    required: '此字段为必填项。',
    unsupportedUpload: '不支持此文件类型。',
  },
};

export function validationMessage(locale: Locale, key: keyof typeof messages.en) {
  return messages[locale]?.[key] ?? messages.en[key];
}
