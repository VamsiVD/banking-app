---
name: Institutional Trust
colors:
  surface: '#f7fafd'
  surface-dim: '#d7dadd'
  surface-bright: '#f7fafd'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f1f4f7'
  surface-container: '#ebeef1'
  surface-container-high: '#e5e8eb'
  surface-container-highest: '#e0e3e6'
  on-surface: '#181c1e'
  on-surface-variant: '#43474d'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eef1f4'
  outline: '#74777e'
  outline-variant: '#c4c6ce'
  surface-tint: '#49607e'
  primary: '#000f22'
  on-primary: '#ffffff'
  primary-container: '#0a2540'
  on-primary-container: '#768dad'
  inverse-primary: '#b0c8eb'
  secondary: '#004ccc'
  on-secondary: '#ffffff'
  secondary-container: '#0762ff'
  on-secondary-container: '#f3f3ff'
  tertiary: '#050e1d'
  on-tertiary: '#ffffff'
  tertiary-container: '#1a2434'
  on-tertiary-container: '#818b9f'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d2e4ff'
  primary-fixed-dim: '#b0c8eb'
  on-primary-fixed: '#001c37'
  on-primary-fixed-variant: '#314865'
  secondary-fixed: '#dbe1ff'
  secondary-fixed-dim: '#b4c5ff'
  on-secondary-fixed: '#00174b'
  on-secondary-fixed-variant: '#003ea8'
  tertiary-fixed: '#d9e3f9'
  tertiary-fixed-dim: '#bdc7dc'
  on-tertiary-fixed: '#121c2b'
  on-tertiary-fixed-variant: '#3d4759'
  background: '#f7fafd'
  on-background: '#181c1e'
  surface-variant: '#e0e3e6'
typography:
  display:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 14px
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
  lg: 48px
  xl: 80px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 64px
  max-width: 1280px
---

## Brand & Style

The design system is anchored in the principles of institutional security, technical precision, and absolute clarity. Targeted at a high-stakes financial audience, the UI must evoke an emotional response of stability and reliability. 

The aesthetic is **Corporate / Modern**, characterized by a rigorous adherence to a grid, purposeful use of whitespace to reduce cognitive load, and a refined "high-finish" execution. The visual language avoids decorative flourishes in favor of functional elegance, ensuring that every element on the screen serves a clear informational or transactional purpose. The interface should feel like a high-end tool—sharp, responsive, and indestructible.

## Colors

The palette is dominated by **Deep Navy (#0A2540)**, used for primary headings, navigation bars, and critical UI anchors to establish an immediate sense of authority. **Trust Blue (#0061FF)** serves as the primary action color, used sparingly for buttons, links, and active states to guide the user's eye through the "secure path."

The background utilizes a series of ultra-clean neutrals. A base of pure white (#FFFFFF) is used for content cards, while a subtle off-white/light-gray (#F6F9FC) is used for the page canvas to create soft contrast. Success and Error states are handled with high-chroma emerald and ruby tones, ensuring that security alerts and confirmation messages are unmistakable.

## Typography

The typography system relies exclusively on **Inter** to leverage its systematic, utilitarian, and highly legible characteristics. The scale is built on a tight ratio to maintain a professional, information-dense environment without feeling cluttered.

- **Headlines:** Use tighter letter spacing and heavier weights (600-700) to project strength.
- **Body Text:** Standard weight (400) with generous line heights (1.5x) to ensure financial data is easily digestible.
- **Data Display:** Numerical data should utilize Inter’s tabular lining features to ensure columns of figures align perfectly for easy comparison.
- **Labels:** Use `label-sm` with a slight tracking increase and uppercase transform for category headers and metadata.

## Layout & Spacing

The layout follows a **Fixed Grid** philosophy for desktop to maintain a controlled, professional presentation of sensitive data, transitioning to a fluid model for mobile devices. 

- **Grid:** A 12-column grid is used for desktop (1280px max-width) with 24px gutters. Content should be grouped into logical modules (spanning 3, 4, or 6 columns).
- **Rhythm:** Spacing is strictly based on an 8px modular scale. Internal component padding should default to 16px or 24px to ensure the "precise and robust" feel.
- **Adaptive Rules:** On mobile, margins reduce to 16px and complex data tables must reflow into vertical "card" stacks to maintain readability. Use `xl` (80px) vertical spacing between major sections to emphasize the "clean and airy" corporate aesthetic.

## Elevation & Depth

Elevation is used strategically to indicate "active" layers of security and focus. This design system avoids heavy shadows, instead opting for **Tonal Layers** combined with **Ambient Shadows**.

- **Surface Tiers:** The main canvas is `neutral-light`. Content containers (cards) are pure white with a 1px border (#E6E9EF). 
- **Elevation Shadows:** Only used to lift interactive elements like modals, dropdowns, or "hovered" cards. These shadows are extra-diffused, using the Primary Deep Navy color at 5-8% opacity to prevent a "dirty" look and maintain a crisp technical feel.
- **Depth Hierarchy:** 
    - Level 0: Background Canvas.
    - Level 1: Content Cards (Flat, 1px border).
    - Level 2: Interactive elements (Soft shadow on hover).
    - Level 3: Overlays/Modals (Deep, diffused shadow + background dimming).

## Shapes

The shape language is **Soft (0.25rem)**. This subtle rounding removes the aggressive "sharpness" of pure brutalism while maintaining a much more disciplined and professional look than "bubbly" consumer apps. 

- **Standard Elements:** Buttons, inputs, and small widgets use the base 4px radius.
- **Large Containers:** Dashboard cards and modals use `rounded-lg` (8px) to soften the overall layout.
- **Avatars:** Strictly circular to contrast against the geometric grid.
- **Stroke:** Use consistent 1px or 1.5px stroke weights for all icons and borders to maintain a "technical drawing" aesthetic.

## Components

Components are designed for "high-touch" precision.

- **Buttons:** Primary buttons are solid `Trust Blue` with white text. Secondary buttons use a `Deep Navy` outline with a subtle hover fill. All buttons have a fixed height (48px for primary) to ensure they feel substantial and easy to trigger.
- **Input Fields:** Use a 1px border in a medium-gray tone (#D1D5DB). On focus, the border transitions to `Trust Blue` with a subtle 2px glow (inner-shadow) of the same color to signal "Active Secure Entry."
- **Cards:** White backgrounds, 1px borders, and internal padding of `md` (24px). Headers within cards should have a subtle bottom divider.
- **Chips/Status Indicators:** Used for transaction statuses (Pending, Cleared, Flagged). These utilize "Low-Contrast Outlines" where the fill is a 10% opacity version of the status color and the text is the full-strength color.
- **Data Tables:** High-density with 1px horizontal dividers only. Row hovering should trigger a very subtle background change to `neutral-light`.
- **Progress Indicators:** Linear, thin bars using `Trust Blue` to show completion of multi-step security verifications.