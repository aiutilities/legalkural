# Assembler Theme Style Map

## Global Styles Tokens

| Token | Value | Use |
| --- | --- | --- |
| Navy 900 | `#0B1F3A` | Header, footer, primary headings |
| Navy 700 | `#183B5B` | Secondary heading/interface depth |
| Teal 600 | `#087E8B` | Brand accent and large active elements |
| Teal 700 | `#066872` | Links/focus/hover on white |
| Teal 100 | `#DDF3F4` | Quiet information panels |
| White | `#FFFFFF` | Primary canvas |
| Mist | `#F5F9FB` | Alternating sections |
| Slate 900 | `#17212B` | Body text |
| Slate 600 | `#52606D` | Secondary text |
| Rule | `#D7E0E8` | Borders and dividers |

## Typography

- Headings: Georgia, `Times New Roman`, serif.
- Body/UI: Inter where supplied by Assembler, falling back to system sans.
- Body size: 18px desktop, 17px mobile; line-height 1.7.
- Content measure: maximum 72 characters for long-form reading.
- One `h1`; logical heading order; no visual-only heading levels.

## Block Mapping

- Header: Group (navy) → Row → Site Logo + Navigation + Search.
- Hero: Group (mist) → constrained Columns, with copy on left and a quiet
  record/meaning motif on right; no stock courthouse imagery.
- Latest insight: Query/featured Post Template limited to the certified post.
- Legal fields: responsive Columns or Grid of linked Group blocks.
- Method: three accessible numbered Group blocks.
- Journal: navy Group with reversed lockup and white text.
- Footer: navy Group with navigation and legal links.

## Accessibility Rules

- Text/link contrast must be measured after Global Styles are applied.
- Use teal 700 for normal-size links on white.
- Focus ring: 3px teal with 2px white offset on dark surfaces.
- Navigation remains keyboard operable and visible at 200% zoom.
- Minimum target size 24px; 44px preferred for primary actions.
- No animation required; respect reduced-motion preference.

## Responsive Rules

- Breakpoint behaviour follows Assembler’s native responsive blocks.
- Two-column hero becomes one column before content becomes cramped.
- Cards become one column at 600px.
- No fixed pixel heights for content sections.
- No horizontal scrolling at 320 CSS pixels.

## Free-Plan Constraint

Use only controls confirmed in the Site Editor. Do not assume custom CSS,
plugins, custom fonts, arbitrary head markup or structured-data injection are
available. Unsupported enhancements remain non-blocking if semantic content,
metadata and accessibility are preserved through available controls.
