---
name: Power Play Elite
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#3a3939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1c1b1b'
  surface-container: '#201f1f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353534'
  on-surface: '#e5e2e1'
  on-surface-variant: '#c4c7c8'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#8e9192'
  outline-variant: '#444748'
  surface-tint: '#c6c6c7'
  primary: '#ffffff'
  on-primary: '#2f3131'
  primary-container: '#e2e2e2'
  on-primary-container: '#636565'
  inverse-primary: '#5d5f5f'
  secondary: '#bfc7d1'
  on-secondary: '#293138'
  secondary-container: '#424a52'
  on-secondary-container: '#b1b9c2'
  tertiary: '#ffffff'
  on-tertiary: '#303030'
  tertiary-container: '#e5e2e1'
  on-tertiary-container: '#656464'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e2e2e2'
  primary-fixed-dim: '#c6c6c7'
  on-primary-fixed: '#1a1c1c'
  on-primary-fixed-variant: '#454747'
  secondary-fixed: '#dbe3ed'
  secondary-fixed-dim: '#bfc7d1'
  on-secondary-fixed: '#151c23'
  on-secondary-fixed-variant: '#40484f'
  tertiary-fixed: '#e5e2e1'
  tertiary-fixed-dim: '#c8c6c5'
  on-tertiary-fixed: '#1b1c1c'
  on-tertiary-fixed-variant: '#474746'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353534'
typography:
  display-lg:
    fontFamily: Barlow Condensed
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Barlow Condensed
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Barlow Condensed
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.2'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  label-caps:
    fontFamily: Barlow Condensed
    fontSize: 14px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.05em
  stat-numeric:
    fontFamily: Barlow Condensed
    fontSize: 20px
    fontWeight: '700'
    lineHeight: '1'
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 12px
  md: 24px
  lg: 40px
  xl: 64px
  gutter: 16px
  margin-mobile: 16px
  margin-desktop: 32px
---

## Brand & Style

This design system is engineered for the high-intensity, fast-paced world of professional hockey. It evokes the atmosphere of a night game under the arena lights—high contrast, cold aesthetics, and absolute precision. The target audience includes die-hard fans, fantasy league players, and sports analysts who require immediate access to dense data without sacrificing visual impact.

The style is **Corporate / Modern** with a **High-Contrast** edge. It utilizes a "Metallic Industrial" aesthetic, characterized by pitch-black backgrounds that make white text and silver accents pop with clinical clarity. It avoids soft, organic shapes in favor of sharp, aggressive lines and rigid structural grids that mirror the geometry of the rink.

## Colors

The palette is strictly dark-mode, anchored by a "Pitch Black" (#000000) base for maximum contrast. 

- **Primary White:** Used for critical information, headlines, and primary actions.
- **Metallic Silver:** Used for secondary labels, iconography, and decorative borders to provide a premium, machined-steel feel.
- **Deep Charcoal:** Used for surface containers and card backgrounds to create subtle depth against the pitch-black base.
- **Team Accents:** While the core system is monochromatic, a reserved "Team Accent" variable should be applied to specific data points (like a team's primary color in a matchup) to provide immediate orientation.

## Typography

Typography is used as a structural element. **Barlow Condensed** is the primary choice for headlines and labels, providing an authoritative, "stadium-scoreboard" feel that maximizes horizontal space for names and scores.

**Inter** is used for body text and descriptive content to ensure high legibility in dense data environments. For player statistics and live scores, use the `stat-numeric` style, which emphasizes the condensed verticality of the numbers. All labels and headlines should default to uppercase to maintain a disciplined, aggressive hierarchy.

## Layout & Spacing

The design system utilizes a **12-column fixed grid** for desktop and a **4-column fluid grid** for mobile. Spacing is governed by an 8px base unit.

Layouts should be dense but organized. Use "Heavy Stacking" for data-rich views like standings or player stats. Vertical rhythm is critical; maintain consistent 24px (md) gaps between major content blocks. In data tables, use a "Condensed Row" height of 40px to ensure maximum information density without sacrificing touch targets on mobile.

## Elevation & Depth

This system avoids ambient shadows, which can feel too soft for a sports environment. Instead, depth is achieved through **Tonal Layering** and **Metallic Outlines**:

1.  **Level 0 (Base):** Pitch Black (#000000) - The main background.
2.  **Level 1 (Surface):** Deep Charcoal (#111111) - Used for scorecards and list items.
3.  **Level 2 (Active):** Dark Grey (#222222) - Used for hovered states or active navigation elements.

To highlight "Live" or "Featured" content, use a 1px solid border in Silver or the Team Accent color. Subtle linear gradients (top-to-bottom) can be applied to buttons and headers to simulate the sheen of polished metal or ice.

## Shapes

The shape language is sharp and decisive. The default border-radius is 4px (`roundedness: 1`), providing just enough "finish" to feel professional without losing the aggressive, angular nature of the brand.

Containers and buttons should never be fully pill-shaped, with the sole exception of "Live" status indicators or small tags. Circular elements are reserved exclusively for player avatars and the circular progress indicators used for performance metrics.

## Components

### Scorecards
Large, high-impact cards with a Deep Charcoal background. Home and Away teams should be clearly separated by a thin 1px vertical divider. Scores use the `display-lg` type style.

### Standings Tables
Compact, no-border tables with alternating row tints (Pitch Black and Deep Charcoal). Column headers use `label-caps` in Silver. The "Current Team" row should be highlighted with a Silver left-border.

### Playoffs Brackets
Visualized with 2px thick "Piping" lines in Silver. Active paths use White; eliminated paths use Deep Charcoal. 

### Circular Progress
Used for player "Power Ratings." Use a 4px stroke width. The track should be Deep Charcoal, and the progress fill should be a Metallic Silver gradient.

### Input Fields & Buttons
Buttons are strictly rectangular or slightly rounded (4px). Primary buttons use White backgrounds with Black text. Secondary buttons use a ghost style (1px Silver border) with White text. Input fields use a Pitch Black fill and a 1px Charcoal border that turns Silver on focus.