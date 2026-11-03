# tools/views/summaries

The summaries at the top of the section indexes, one template per section. `summaries.py` fills each `{slot}` from
the data at every build, and `build.py` writes the result into the `kaphtor:summary` block under the index's `***`.
Edit the prose here; never the block in the index, which the next build rewrites.

| Template | Index |
|---|---|
| `linear-a.md` | `wiki/linear-a/_index.md` |
| `semitic-roots.md` | `wiki/semitic-roots/_index.md` |

A slot no field in `summaries.py` fills stops the build. The first line of each template, an HTML comment, is left out.
