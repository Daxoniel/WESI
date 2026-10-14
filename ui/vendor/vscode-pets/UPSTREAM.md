# VS Code Pets integration

Source: https://github.com/tonybaloney/vscode-pets
Pinned commit: 93a420cab4b6618bfa9928da0dd941447a145d8f
License: MIT, original text retained in LICENSE.

The files in src/ are unchanged upstream TypeScript: BasePetType, states, sequences, common types and RubberDuck. WESI bundles these through ui/pet-engine-entry.js into vendor/pet-engine.js; npm run build rebuilds them offline from checked-in source.

Rubber duck artwork is credited to Marc Duiker by upstream README. The included media/rubber-duck files are copied from that commit. No Live2D models, cat/dog commercial packs or unrelated character assets are included.

WESI supplies the desktop window, local Python bridge, game persistence and text expeditions. The upstream state machine drives the actual sprite behavior; this is not only an icon or a launcher to a separately installed extension. Native movement remains inside the companion window; the handle moves that window around the desktop. This version does not detect other application edges or provide click-through.
