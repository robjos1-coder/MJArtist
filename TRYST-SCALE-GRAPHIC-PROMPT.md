# Handoff: "maquette to monument" graphic for the Sculpture page

> **Update:** a finished drawing traced from the real photo is now on the site (`images/tryst-scale.png`). For other styles, use the ComfyUI pack (`comfyui-tryst.zip`): it keeps the true shape by using ControlNet. What follows is the original prompt for chat-based generators, which tend to reinvent the form.

Use an image generator that accepts reference photos (ChatGPT image generation or Google Gemini both work). Attach both photos, then paste the prompt.

**Reference photos**
1. **Tryst, full size:** `images/tryst.jpg` in the site folder (the photo against the white wall, without Michael).
2. **Tryst maquette:** download the full-size original from
   https://static.wixstatic.com/media/c7e04c_c8e723af3f8e4f05a5b1dca007172e77~mv2.jpg

**Before you paste:** replace `[MAQUETTE HEIGHT]` with 25 cm.

```
Create a clean greyscale scale drawing in the style of an architect's elevation or a museum-catalogue diagram, using the two attached photos as exact references.

Composition — portrait 4:5, plain flat background colour #D4D3CF:
- Left: the small maquette (reference photo 2) standing on a simple rectangular plinth. The maquette is [MAQUETTE HEIGHT] tall.
- Centre: a plain standing adult human silhouette, 1.8 m tall, flat mid-grey, no face or detail.
- Right: the full-size sculpture (reference photo 1), drawn to the same scale as the person, just over 3 m tall — about 1.75 times the person's height. The solid cut-steel female figure is flat dark grey. The open welded-steel lattice figure is crisp thin black lines, with the gaps between the bars left open so the background shows through.
- Everything stands on one straight horizontal ground line.
- Very faint horizontal guide lines at 1 m, 2 m and 3 m.

Style: flat 2D elevation, straight-on view, no perspective, no shadows, no gradients, no texture, no colour. Use only four tones: black, dark grey, mid grey and the background. Thin, even line weights. Minimal and elegant.

Keep both sculptures' outlines faithful to the photos. Don't invent extra parts or tidy the lattice into a regular pattern.

Do not add any text, numbers, labels, logos or watermarks.

Output a PNG at least 2000 px tall.
```

**Check before using**
- AI tools often simplify the lattice. Compare it with the photo and regenerate if the pattern is obviously wrong.
- The person and the full-size sculpture must share one scale: Tryst's top should sit at roughly 1.75× the person's height.
- If the lattice keeps coming out wrong, ask for "silhouettes only, both figures solid dark grey". That is simpler and still reads well.

**Putting it on the site:** in the editor, go to *About, contact & home page* → *Scale feature — drawing* and upload the PNG. It replaces the automatic diagram next to the photo of Tryst.
