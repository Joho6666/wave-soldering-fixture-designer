---
name: Precision-Sync Engineering Interface
colors:
  surface: '#0d1516'
  surface-dim: '#0d1516'
  surface-bright: '#333a3c'
  surface-container-lowest: '#080f11'
  surface-container-low: '#151d1e'
  surface-container: '#192122'
  surface-container-high: '#242b2d'
  surface-container-highest: '#2e3638'
  on-surface: '#dce4e5'
  on-surface-variant: '#bac9cc'
  inverse-surface: '#dce4e5'
  inverse-on-surface: '#2a3233'
  outline: '#849396'
  outline-variant: '#3b494c'
  surface-tint: '#00daf3'
  primary: '#c3f5ff'
  on-primary: '#00363d'
  primary-container: '#00e5ff'
  on-primary-container: '#00626e'
  inverse-primary: '#006875'
  secondary: '#c2c7d0'
  on-secondary: '#2c3138'
  secondary-container: '#42474f'
  on-secondary-container: '#b1b5bf'
  tertiary: '#ffeac0'
  on-tertiary: '#3e2e00'
  tertiary-container: '#fec931'
  on-tertiary-container: '#6f5500'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#9cf0ff'
  primary-fixed-dim: '#00daf3'
  on-primary-fixed: '#001f24'
  on-primary-fixed-variant: '#004f58'
  secondary-fixed: '#dee2ec'
  secondary-fixed-dim: '#c2c7d0'
  on-secondary-fixed: '#171c23'
  on-secondary-fixed-variant: '#42474f'
  tertiary-fixed: '#ffdf96'
  tertiary-fixed-dim: '#f3bf26'
  on-tertiary-fixed: '#251a00'
  on-tertiary-fixed-variant: '#594400'
  background: '#0d1516'
  on-background: '#dce4e5'
  surface-variant: '#2e3638'
typography:
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  data-mono:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '700'
    lineHeight: 12px
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 1px
  panel-padding: 12px
  container-gap: 8px
  sidebar-width: 280px
  toolbar-height: 48px
---

## Brand & Style
The design system embodies a high-precision, industrial CAD aesthetic tailored for engineering workflows. It prioritizes technical clarity and functional density over decorative elements, catering to professionals who require an efficient, distraction-free environment for wave soldering fixture design.

The visual language is rooted in **Minimalism** with a **Technical/Precise** focus. It avoids modern consumer trends like heavy shadows or rounded "pill" shapes in favor of sharp edges, tight layouts, and a "dark mode" environment that reduces eye strain during long design sessions. The emotional response is one of reliability, accuracy, and professional rigor.

## Colors
The palette is engineered for high contrast in a low-light "Dark Mode" environment. 

- **Foundation:** The deep Graphite background (#101317) provides a non-reflective base, while Blue-Grey panels (#1C2128) define distinct functional zones without the need for heavy borders.
- **Interaction:** Bright Cyan serves as the primary action color, ensuring immediate visibility against the dark backdrop.
- **CAD Semantics:** A specific secondary palette is reserved strictly for 2D/3D geometry representation. These colors must not be used for UI icons or buttons to avoid cognitive overlap with the technical design workspace.
- **Feedback:** Standardized semantic colors (Green, Yellow, Red) are used for process status, validation errors, and safety warnings.

## Typography
The typography system uses a tiered approach to balance readability with a technical feel.

- **Headlines:** Uses Hanken Grotesk for a clean, contemporary feel in navigation and panel titles.
- **Body:** Inter is the workhorse for all descriptions, settings, and general UI text, chosen for its exceptional legibility at small scales.
- **Technical Data:** JetBrains Mono is utilized for coordinate readouts, dimensions, CAD layer names, and AI-generated parameters. 
- **Scale:** Sizes are kept small (10px–14px) to maximize the information density required for complex engineering tools.

## Layout & Spacing
The layout follows a **Fixed-Panel Grid** system reminiscent of classic CAD environments. 

- **Structure:** A central 3D viewport is flanked by persistent sidebars for "Properties," "Layers," and "AI Constraints." 
- **Rhythm:** A 4px base unit governs all spacing. Use tight 8px gaps between UI elements to maintain high density.
- **Separation:** Panels are separated by 1px borders or subtle tonal shifts rather than whitespace.
- **Density:** Every pixel is valuable. Minimize padding within lists and tables to ensure as many data points as possible are visible without scrolling.

## Elevation & Depth
In this design system, depth is conveyed through **Tonal Layering** and **Ghost Outlines** rather than shadows.

- **Z-Index Strategy:** The background (#101317) is the lowest level. Active panels use #1C2128. Popovers or context menus use a slightly lighter #30363D with a 1px solid border (#484F58).
- **No Shadows:** Shadows are disabled to maintain the "flat" industrial feel. 
- **Focus States:** Active input fields or selected components are highlighted with a 1px Cyan border, creating a "glow" effect without using actual blur.

## Shapes
The shape language is strictly **Soft-Industrial**. 

- **Primary Corners:** A 4px (0.25rem) radius is the maximum allowed for buttons and input fields, providing just enough definition to separate elements from the background.
- **Panel Edges:** Outer panel containers should remain at 0px (Sharp) to integrate seamlessly with the window edges and toolbars.
- **Indicators:** Small status dots or CAD markers use 0px squares or 45-degree chamfers where possible to maintain the technical aesthetic.

## Components

### Buttons
- **Primary:** Solid Cyan background with black text. Sharp 2px corners.
- **Secondary:** Transparent background with 1px Grey border. White text.
- **Icon Buttons:** No background, Cyan icon on hover.

### Inputs & Fields
- **Data Inputs:** Background #0D1117 with 1px #30363D border. Use JetBrains Mono for the value text. Include a unit suffix (e.g., "mm") pinned to the right.
- **Sliders:** Minimalist 2px height track in Grey, with a square 8px Cyan thumb.

### Data Grids & Tables
- **Engineering Tables:** Header row with #1C2128 background. Row height 28px. 1px horizontal dividers only. Monospaced numeric data.

### Toolbars
- **Vertical Tool Palette:** Pinned to the left of the viewport. Square 32x32px buttons with 20px icons. Active tools indicated by a 2px Cyan left-border stripe.

### Status Indicators
- **AI Processing:** A subtle, non-rounded progress bar at the very top of the viewport or bottom status bar using a Cyan pulse effect.
- **Layer Toggles:** Use the CAD-specific colors as small square color chips next to the layer name.