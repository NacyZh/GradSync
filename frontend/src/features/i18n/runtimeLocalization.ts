import { translateUiText } from '@/shared/i18n/translate';

import type { Locale } from './I18nProvider';

const originalText = new WeakMap<Text, string>();
const trackedText = new Set<Text>();
const originalAttributes = new WeakMap<Element, Record<string, string>>();
const trackedElements = new Set<Element>();
const attributes = ['aria-label', 'placeholder', 'title'] as const;

function translated(value: string) {
  return translateUiText(value, 'zh');
}

function localizeTextNode(node: Text) {
  const current = node.nodeValue ?? '';
  const trimmed = current.trim();
  if (!trimmed) return;
  const prior = originalText.get(node);
  if (!prior || (current !== translated(prior) && current !== prior)) originalText.set(node, current);
  const source = originalText.get(node) ?? current;
  const sourceTrimmed = source.trim();
  const localized = translated(sourceTrimmed);
  if (localized === sourceTrimmed) return;
  trackedText.add(node);
  node.nodeValue = source.replace(sourceTrimmed, localized);
}

function localizeElement(element: Element) {
  for (const attribute of attributes) {
    const current = element.getAttribute(attribute);
    if (!current) continue;
    const existing = originalAttributes.get(element) ?? {};
    const prior = existing[attribute];
    if (!prior || (current !== translated(prior) && current !== prior)) existing[attribute] = current;
    originalAttributes.set(element, existing);
    const localized = translated(existing[attribute]);
    if (localized !== current) element.setAttribute(attribute, localized);
    trackedElements.add(element);
  }
}

function walk(root: Node) {
  if (root.nodeType === Node.TEXT_NODE) localizeTextNode(root as Text);
  if (root.nodeType === Node.ELEMENT_NODE) localizeElement(root as Element);
  root.childNodes.forEach(walk);
}

export function applyRuntimeLocalization(locale: Locale) {
  if (locale === 'en') {
    trackedText.forEach((node) => { if (node.isConnected) node.nodeValue = originalText.get(node) ?? node.nodeValue; });
    trackedElements.forEach((element) => {
      if (!element.isConnected) return;
      const originals = originalAttributes.get(element) ?? {};
      attributes.forEach((attribute) => { if (originals[attribute]) element.setAttribute(attribute, originals[attribute]); });
    });
    return () => undefined;
  }
  walk(document.body);
  const observer = new MutationObserver((mutations) => {
    observer.disconnect();
    mutations.forEach((mutation) => {
      if (mutation.type === 'characterData') walk(mutation.target);
      mutation.addedNodes.forEach(walk);
      if (mutation.type === 'attributes') localizeElement(mutation.target as Element);
    });
    observer.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: [...attributes] });
  });
  observer.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: [...attributes] });
  return () => observer.disconnect();
}
