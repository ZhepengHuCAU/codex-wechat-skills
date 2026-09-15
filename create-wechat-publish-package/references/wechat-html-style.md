# WeChat HTML Style

Use inline styles in the article fragment.

## Container

```html
<section data-role="wechat-article"
  style="width:100%;max-width:none;margin:0;padding:0;box-sizing:border-box;">
```

## Body Paragraph

```text
margin:0 0 18px 0; line-height:31px; font-size:16px; color:#262626;
font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',Arial,sans-serif;
text-align:justify; letter-spacing:.02em;
```

## Section Heading

```text
margin:30px 0 18px 0; padding-left:12px; border-left:4px solid #D18A00;
line-height:30px; font-size:21px; font-weight:700; color:#0B4A2F;
```

Use `margin-top:0` on the first rendered element.

## Image

```text
display:block; width:100%; height:auto; margin:24px auto 28px auto;
```

## Source Note

Use a light warm-gray panel, 13 px text, and 23 px line height. Include sources, data date, and a scenario/model disclaimer when relevant.

## WeChat Compatibility Guardrails

- Use explicit pixel `line-height` values in inline styles. Avoid unitless ratios such as `1.9`, percentages, or values smaller than the font size because the WeChat editor/plugin checker may flag them as overlapping text.
- Avoid wide HTML tables in copyable article bodies. Do not use `min-width`, `overflow-x:auto`, or horizontally scrolling table wrappers by default.
- For small comparison tables, render stacked cards or vertical key-value blocks with `width:100%;max-width:100%;box-sizing:border-box`.
- If a true table is explicitly required, inspect the rendered mobile preview and confirm the page scroll width does not exceed the viewport width.

## Preview Wrapper

When the user requests no side whitespace, use `width:100%;max-width:none;margin:0;padding:0` for both the standalone preview wrapper and article container. Do not reintroduce padding in a mobile media query. Preserve all other existing article formatting unless the user explicitly requests a redesign.