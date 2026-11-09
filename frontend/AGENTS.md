<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

- All backend HTTP goes through `src/api/client.ts` (apiGet + parsers) and per-domain query option modules in `src/api/`; components never call fetch — keeps error/timeout/malformed handling uniform.
- The UI never fabricates marine values: layers and values derive only from backend responses; missing capabilities render an explicit "unavailable" state.
- Leaflet is imported dynamically inside `MarineMap` effects so SSR never evaluates it.
