import { readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import ts from 'typescript';
import { describe, expect, it } from 'vitest';

import { messagesEn } from '../../src/data/locale/messages.en';
import { messagesZh } from '../../src/data/locale/messages.zh';
import { runtimeZh } from '../../src/data/locale/runtime.zh';
import { applyRuntimeLocalization } from '../../src/features/i18n/runtimeLocalization';
import { formatUiDate, translateUiText } from '../../src/shared/i18n/translate';

const root = path.resolve(__dirname, '../../src');
const userFacingAttributes = new Set([
  'actionLabel',
  'aria-label',
  'description',
  'label',
  'message',
  'placeholder',
  'title',
]);

function tsxFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) return tsxFiles(target);
    return target.endsWith('.tsx') ? [target] : [];
  });
}

describe('i18n completeness', () => {
  it('keeps keyed English and Chinese catalogs aligned', () => {
    expect(Object.keys(messagesZh).sort()).toEqual(Object.keys(messagesEn).sort());
  });

  it('registers every static JSX label in a locale catalog', () => {
    const keyedEnglish = new Set<string>(Object.values(messagesEn));
    const keyedMessageKeys = new Set<string>(Object.keys(messagesEn));
    const allowedBrandText = new Set(['GradSync', 'GS']);
    const technicalText = new Set(['dark', 'zh', '.pdf', 'EEEE, MMMM d']);
    const missing: string[] = [];

    for (const file of tsxFiles(root)) {
      const source = readFileSync(file, 'utf8');
      const tree = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
      function visit(node: ts.Node) {
        const values: string[] = [];
        if (ts.isJsxText(node)) values.push(node.text.replace(/\s+/g, ' ').trim());
        if (
          ts.isJsxAttribute(node)
          && userFacingAttributes.has(node.name.getText(tree))
          && node.initializer
        ) {
          if (ts.isStringLiteral(node.initializer)) values.push(node.initializer.text);
          if (
            ts.isJsxExpression(node.initializer)
            && node.initializer.expression
          ) {
            function collectLiteral(expression: ts.Node) {
              if (ts.isStringLiteral(expression)) values.push(expression.text);
              ts.forEachChild(expression, collectLiteral);
            }
            collectLiteral(node.initializer.expression);
          }
        }
        for (const value of values) {
          if (
            value
            && /[A-Za-z]{2}/.test(value)
            && !allowedBrandText.has(value)
            && !technicalText.has(value)
            && !keyedMessageKeys.has(value)
            && !keyedEnglish.has(value)
            && !runtimeZh[value]
          ) missing.push(`${path.relative(root, file)}: ${value}`);
        }
        ts.forEachChild(node, visit);
      }
      visit(tree);
    }

    expect(missing).toEqual([]);
  });

  it('localizes dynamic UI copy and dates using the selected locale', () => {
    window.localStorage.setItem('gradsync.locale', 'zh');
    expect(translateUiText('Download started: report.pdf')).toBe('下载已开始：report.pdf');
    expect(translateUiText('3 visible workspaces')).toBe('3 个可见工作区');
    expect(formatUiDate('2026-07-21T12:00:00Z', { year: 'numeric', month: 'long', timeZone: 'UTC' })).toContain('2026年');
    window.localStorage.removeItem('gradsync.locale');
  });

  it('translates newly rendered UI nodes and restores their English source', () => {
    const host = document.createElement('div');
    host.innerHTML = '<button aria-label="Open notifications">Shared code</button>';
    document.body.append(host);

    const stop = applyRuntimeLocalization('zh');
    expect(host).toHaveTextContent('共享代码');
    expect(host.querySelector('button')).toHaveAttribute('aria-label', '打开通知');
    stop();
    applyRuntimeLocalization('en')();
    expect(host).toHaveTextContent('Shared code');
    expect(host.querySelector('button')).toHaveAttribute('aria-label', 'Open notifications');
    host.remove();
  });
});
