import { existsSync, readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';

import { describe, expect, it } from 'vitest';

const root = process.cwd();
const src = path.join(root, 'src');

function relative(pathname: string) {
  return path.relative(root, pathname).split(path.sep).join('/');
}

function readSource(relativePath: string) {
  return readFileSync(path.join(root, relativePath), 'utf8');
}

function collectFiles(directory: string): string[] {
  if (!existsSync(directory)) {
    return [];
  }

  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const nextPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      return collectFiles(nextPath);
    }
    return [nextPath];
  });
}

describe('frontend source structure contract', () => {
  it('uses canonical Vite source directories', () => {
    for (const directory of [
      'src/app',
      'src/routes',
      'src/features',
      'src/shared/api',
      'src/shared/ui',
      'src/shared/lib',
      'src/shared/platform',
      'src/data/locale',
      'src/data/display',
      'src/styles',
      'src/assets',
      'src/test',
    ]) {
      expect(existsSync(path.join(root, directory)), `${directory} should exist`).toBe(true);
    }
  });

  it('removes legacy shared and style roots after migration', () => {
    const legacyPaths = [
      ['src', 'app', 'styles.css'],
      ['src', 'lib'],
      ['src', 'components'],
    ].map((parts) => parts.join('/'));

    for (const legacyPath of legacyPaths) {
      expect(existsSync(path.join(root, legacyPath)), `${legacyPath} should be migrated`).toBe(false);
    }
  });

  it('keeps app bootstrap focused and loads global CSS from src/styles', () => {
    const allowedAppFiles = new Set(['App.tsx', 'HomePage.tsx', 'Layout.tsx', 'main.tsx', 'queryClient.tsx']);
    const appFiles = readdirSync(path.join(src, 'app')).filter((entry) =>
      readdirSync(path.join(src, 'app'), { withFileTypes: true }).some(
        (dirent) => dirent.name === entry && dirent.isFile(),
      ),
    );

    expect(appFiles.sort()).toEqual([...allowedAppFiles].sort());
    expect(readSource('src/app/main.tsx')).toContain("import '../styles/globals.css';");
    expect(existsSync(path.join(root, 'src/styles/globals.css'))).toBe(true);
    expect(existsSync(path.join(root, 'src/styles/theme.css'))).toBe(true);
  });

  it('stores static locale messages under src/data', () => {
    for (const localeFile of ['src/data/locale/messages.en.ts', 'src/data/locale/messages.zh.ts']) {
      expect(existsSync(path.join(root, localeFile)), `${localeFile} should exist`).toBe(true);
    }
  });

  it('keeps data config static and styles independent from features', () => {
    const dataViolations = collectFiles(path.join(src, 'data')).flatMap((filePath) => {
      const source = readFileSync(filePath, 'utf8');
      return [
        /from ['"]react['"]/,
        /use[A-Z][A-Za-z0-9_]*\s*\(/,
        /<[A-Z][A-Za-z0-9_]*[\s>]/,
      ]
        .filter((pattern) => pattern.test(source))
        .map((pattern) => `${relative(filePath)} contains ${pattern}`);
    });

    const styleViolations = collectFiles(path.join(src, 'styles')).flatMap((filePath) => {
      const source = readFileSync(filePath, 'utf8');
      return [/features\//]
        .filter((pattern) => pattern.test(source))
        .map((pattern) => `${relative(filePath)} contains ${pattern}`);
    });

    expect(dataViolations).toEqual([]);
    expect(styleViolations).toEqual([]);
  });

  it('keeps tracked architecture notes aligned with moved files', () => {
    const architectureGuide = readFileSync(path.join(root, '..', 'docs/frontend-architecture.md'), 'utf8');

    for (const documentedPath of [
      'frontend/src/styles/theme.css',
      'frontend/src/shared/lib/utils.ts',
      'frontend/src/shared/ui/primitives/button.tsx',
      'frontend/src/data/locale/messages.en.ts',
    ]) {
      expect(architectureGuide, `${documentedPath} should be documented`).toContain(documentedPath);
    }

    for (const sourcePath of [
      'src/styles/globals.css',
      'src/styles/theme.css',
      'src/shared/lib/utils.ts',
      'src/shared/ui/primitives/button.tsx',
      'src/data/locale/messages.en.ts',
      'src/data/locale/messages.zh.ts',
    ]) {
      expect(existsSync(path.join(root, sourcePath)), `${sourcePath} should exist`).toBe(true);
    }
  });
});

describe('frontend source structure diagnostics', () => {
  it('reports paths relative to the frontend root', () => {
    expect(relative(path.join(root, 'src/styles/globals.css'))).toBe('src/styles/globals.css');
  });
});
