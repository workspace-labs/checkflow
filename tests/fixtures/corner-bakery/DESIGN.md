# DESIGN.md: Corner Bakery
> v1 · Approved 2026-11-29 by the bakery owner

## The feel
Clear rows like a printed bread list. The name and price are easy to read together.

## Colors
| Name | Color | Used for |
|---|---|---|
| Background | #FFF9EE | Printed pages |
| Card | #FFFFFF | Grouped details |
| Text | #2D2219 | Main text |
| Quiet text | #5B4C3F | Dates and notes |
| Main color | #783E22 | Labels |
| On main | #FFFFFF | Text on the main color |
| Lines | #AE9C87 | Dividers |
| Error | #932D22 | Error labels |

## Fonts
| Use | Font | Size |
|---|---|---|
| Headings | System monospace | 24 px |
| Text | System monospace | 16 px |

The terminal uses its system font and colors.

## Shapes and spacing
- **Corners:** 4 px for printed panels.
- **Spacing:** 4, 8, 16, 24 and 32 px on printed pages; spaces between terminal columns.

## Pieces
- **Menu:** one line per bread with the price beside it.
- **Orders:** show the reference, bread and pickup date in text.

## Must-have rules
- The customer can use the menu and place an order with a keyboard.
- Bread names and prices are readable without color.

## Ready values
```css
:root {
  --color-background: #FFF9EE;
  --color-card: #FFFFFF;
  --color-text: #2D2219;
  --color-quiet: #5B4C3F;
  --color-main: #783E22;
  --color-on-main: #FFFFFF;
  --color-lines: #AE9C87;
  --color-error: #932D22;
  --font-heading: monospace;
  --font-text: monospace;
  --radius: 4px;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 16px;
  --space-4: 24px;
  --space-5: 32px;
}
```
