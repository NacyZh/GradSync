import { existsSync, readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';

import { describe, expect, it } from 'vitest';

const root = process.cwd();
const repoRoot = path.resolve(root, '..');

const sourceExtensions = new Set(['.ts', '.tsx', '.js', '.jsx', '.json']);
const ignoredTestFiles = new Set(['frontend-import-boundaries.test.ts', 'frontend-structure.test.ts']);

function collectFiles(directory: string): string[] {
  if (!existsSync(directory)) {
    return [];
  }

  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const nextPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      return collectFiles(nextPath);
    }
    return sourceExtensions.has(path.extname(entry.name)) ? [nextPath] : [];
  });
}

function projectPath(filePath: string) {
  return path.relative(repoRoot, filePath).split(path.sep).join('/');
}

function readProjectFiles() {
  return [
    ...collectFiles(path.join(root, 'src')),
    ...collectFiles(path.join(root, 'tests/component')),
    path.join(root, 'components.json'),
  ].filter((filePath) => !ignoredTestFiles.has(path.basename(filePath)));
}

function readSourceFilesUnder(relativeDirectory: string) {
  return collectFiles(path.join(root, relativeDirectory));
}

describe('frontend import boundaries', () => {
  it('does not use legacy shared import roots', () => {
    const prohibited = [
      /@\/components\/ui\//,
      /@\/lib\/utils/,
      /src\/app\/styles\.css/,
      /features\/i18n\/messages\.(en|zh)/,
    ];

    const violations = readProjectFiles().flatMap((filePath) => {
      const source = readFileSync(filePath, 'utf8');
      return prohibited
        .filter((pattern) => pattern.test(source))
        .map((pattern) => `${projectPath(filePath)} contains ${pattern}`);
    });

    expect(violations).toEqual([]);
  });

  it('uses canonical shared primitive and utility import paths', () => {
    const source = readProjectFiles()
      .map((filePath) => readFileSync(filePath, 'utf8'))
      .join('\n');

    expect(source).toContain('@/shared/ui/primitives/button');
    expect(source).toContain('@/shared/lib/utils');
  });

  it('keeps locale message consumers on src/data', () => {
    const source = readProjectFiles()
      .map((filePath) => readFileSync(filePath, 'utf8'))
      .join('\n');

    expect(source).toContain('@/data/locale/messages.en');
    expect(source).toContain('@/data/locale/messages.zh');
  });

  it('prevents shared modules from depending on feature internals', () => {
    const violations = readSourceFilesUnder('src/shared').flatMap((filePath) => {
      const source = readFileSync(filePath, 'utf8');
      return [
        /from ['"](?:@\/features|(?:\.\.\/)+features)\//,
        /import\(['"](?:@\/features|(?:\.\.\/)+features)\//,
      ]
        .filter((pattern) => pattern.test(source))
        .map((pattern) => `${projectPath(filePath)} contains ${pattern}`);
    });

    expect(violations).toEqual([]);
  });

  it('prevents cross-feature imports of private API modules', () => {
    const featureRoot = path.join(root, 'src/features');
    const violations = readSourceFilesUnder('src/features').flatMap((filePath) => {
      const relativeFile = path.relative(featureRoot, filePath).split(path.sep).join('/');
      const owningFeature = relativeFile.split('/')[0];
      const source = readFileSync(filePath, 'utf8');

      return [...source.matchAll(/from ['"](?:\.\.\/)([^/'"]+)\/api(?:['"]|\/)/g)]
        .filter((match) => match[1] !== owningFeature)
        .map((match) => `${projectPath(filePath)} imports private ${match[1]}/api`);
    });

    expect(violations).toEqual([]);
  });
});
