# WeChat HTML Style

Use inline styles in the article fragment.

## Container

```html
<section data-role="wechat-article"
  style="width:100%;max-width:none;margin:0;padding:0;box-sizing:border-box;">
```

## Body Paragraph

```text
margin:0 0 18px 0; line-height:1.9; font-size:16px; color:#262626;
font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',Arial,sans-serif;
text-align:justify; letter-spacing:.02em;
```

## Section Heading

```text
margin:30px 0 18px 0; padding-left:12px; border-left:4px solid #D18A00;
line-height:1.45; font-size:21px; font-weight:700; color:#0B4A2F;
```

Use `margin-top:0` on the first rendered element.

## Image

```text
display:block; width:100%; height:auto; margin:24px auto 28px auto;
```

## Source Note

Use a light warm-gray panel, 13 px text, and 1.75 line height. Include sources, data date, and a scenario/model disclaimer when relevant.

## Preview Wrapper

When the user requests no side whitespace, use `width:100%;max-width:none;margin:0;padding:0` for both the standalone preview wrapper and article container. Do not reintroduce padding in a mobile media query. Preserve all other existing article formatting unless the user explicitly requests a redesign.