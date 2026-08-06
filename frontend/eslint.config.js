import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import prettier from 'eslint-config-prettier'

// Flat config ESLint (E00US002). `prettier` désactive les règles de mise en forme
// qui entreraient en conflit avec Prettier (qui reste seul maître du formatage).
export default tseslint.config(
  { ignores: ['dist'] },
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      ...tseslint.configs.recommended,
      reactHooks.configs.flat['recommended-latest'],
      reactRefresh.configs.vite,
      prettier,
    ],
    languageOptions: {
      ecmaVersion: 2023,
      globals: globals.browser,
    },
  },

  // — La frontière navigateur / Node, tenue **ici** et non par TypeScript (E17US001, revue). —
  //
  // Deux tests lisent les sources sur disque (`charte.test.ts`, `theme.test.ts`) et ont donc besoin
  // d'`@types/node`. Les deux façons de le leur donner **fuient sur tout le programme** : `types`
  // dans `tsconfig.app.json` évidemment, mais aussi `/// <reference types="node" />`, qui injecte le
  // paquet dans les globaux **du programme entier** et non du seul fichier — c'est contre-intuitif,
  // et deux relecteurs l'ont prouvé par mutation après que la première correction eut affirmé
  // l'inverse.
  //
  // Le typage ne peut donc pas tenir cette frontière : eslint le fait, et il est dans la porte de CI
  // au même titre. Sans lui, un `process.env.X` ou un `node:fs` écrit dans un composant passe le
  // typecheck **et** le build, pour n'exploser qu'au chargement — sur une tablette, dans le gymnase,
  // le jour J.
  {
    files: ['**/*.{ts,tsx}'],
    ignores: ['**/*.test.{ts,tsx}', 'src/test-setup.ts'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['node:*', 'fs', 'path', 'child_process'],
              message:
                'Code navigateur : les modules Node ne sont disponibles que dans les tests (@types/node fuit sur tout le programme, cf. eslint.config.js).',
            },
          ],
        },
      ],
      'no-restricted-globals': [
        'error',
        { name: 'process', message: 'Code navigateur : utiliser `import.meta.env` si besoin.' },
        { name: 'Buffer', message: 'Code navigateur : pas de Buffer Node dans le bundle.' },
        { name: '__dirname', message: 'Code navigateur : pas de chemin de module Node.' },
      ],
    },
  },
)
