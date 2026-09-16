import "@testing-library/jest-dom/vitest";

// Node 26 ships an experimental built-in `localStorage` global that resolves to
// `undefined` unless the process starts with `--localstorage-file`. Its getter
// already exists on `globalThis`, so the vitest jsdom environment cannot install
// jsdom's implementation on top of it, and `window.localStorage` resolves to the
// same undefined value. `sessionStorage` is unaffected, which is why only
// `localStorage` breaks. On Node 22/24 (the versions this repo targets) jsdom
// provides `localStorage` and this shim is skipped.
if (typeof globalThis.localStorage === "undefined") {
  const store = new Map<string, string>();
  const localStorageShim: Storage = {
    get length() {
      return store.size;
    },
    key: (index: number) => Array.from(store.keys())[index] ?? null,
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => {
      store.set(String(key), String(value));
    },
    removeItem: (key: string) => {
      store.delete(key);
    },
    clear: () => {
      store.clear();
    },
  };
  Object.defineProperty(globalThis, "localStorage", {
    value: localStorageShim,
    configurable: true,
    writable: true,
  });
}