// App JS modules are served at runtime from /static/js/modules/ and ship without
// type declarations. A few specs import them dynamically inside page.evaluate
// (resolved in the browser, e.g. `await import('/static/js/modules/toast.js')`).
// Declare them as untyped modules so `tsc --noEmit` can resolve the import
// specifiers; imported members are typed `any` and call sites cast where needed
// (e.g. `as never`).
declare module '/static/js/modules/*';
