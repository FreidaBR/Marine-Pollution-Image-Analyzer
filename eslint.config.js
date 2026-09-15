// Minimal ESLint flat config for the frontend (Vite + JS/JSX).
// Kept intentionally small: this repo's frontend has no code yet beyond
// placeholders, so we lint for correctness issues rather than a specific
// framework's style guide.
export default [
  {
    ignores: ["**/node_modules/**", "**/dist/**", "**/.vite/**"],
  },
  {
    files: ["**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
      globals: {
        window: "readonly",
        document: "readonly",
        console: "readonly",
      },
    },
    rules: {
      "no-unused-vars": "warn",
      "no-undef": "error",
      "no-console": "off",
    },
  },
];
