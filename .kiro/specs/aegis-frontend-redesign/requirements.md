# Requirements Document: Aegis Frontend Redesign

## Introduction

This document specifies the requirements for redesigning the Aegis frontend to match the premium "Cybersecurity Command Center" aesthetic defined in Design.md. The redesign will transform the existing Next.js application with a comprehensive visual overhaul while maintaining all current functionality. The implementation will add full light/dark mode support, integrate custom typography, implement a sophisticated color system, and add micro-animations to create a polished, professional security operations center interface.

## Glossary

- **Frontend_Application**: The Next.js (App Router) web application located in the `aegis-frontend/` directory
- **Design_Reference**: The complete HTML design specification in `Design/Design.md`
- **Design_Plan**: The phased implementation guide in `Design/Design_plan.md`
- **Theme_System**: The next-themes library integration for light/dark mode switching
- **Design_Tokens**: CSS custom properties (variables) that define colors, spacing, typography, and other design values
- **Typography_System**: The three-font combination: Syne (display), Share Tech Mono (monospace), and DM Sans (body)
- **Color_Palette**: The semantic color system with dark mode (void backgrounds, neon accents) and light mode (crisp whites, muted accents)
- **Component_Library**: The shadcn/ui components customized to match the Aegis aesthetic
- **Glassmorphism**: UI technique using backdrop-blur and semi-transparent backgrounds
- **Bento_Layout**: Grid-based layout pattern with bordered cells separated by 1px dividers
- **Micro_Animations**: Small, purposeful animations including pulsing dots, marquee scrolling, and scanning lines
- **WCAG_Compliance**: Web Content Accessibility Guidelines ensuring sufficient color contrast ratios

## Requirements

### Requirement 1: Typography System Integration

**User Story:** As a developer, I want to integrate the three custom fonts from Design.md, so that the application matches the exact typographic hierarchy of the reference design.

#### Acceptance Criteria

1. THE Frontend_Application SHALL load Syne font from Google Fonts with weights 400, 700, and 800
2. THE Frontend_Application SHALL load Share Tech Mono font from Google Fonts
3. THE Frontend_Application SHALL load DM Sans font from Google Fonts with weights 300, 400, and 500
4. THE Frontend_Application SHALL configure fonts using next/font/google in app/layout.tsx
5. THE Frontend_Application SHALL define CSS variables --font-display, --font-mono, and --font-body mapping to the respective fonts
6. THE Frontend_Application SHALL apply Syne to all h1, h2, h3 heading elements
7. THE Frontend_Application SHALL apply Share Tech Mono to code blocks, metrics, agent tags, and terminal outputs
8. THE Frontend_Application SHALL apply DM Sans to all body text, paragraphs, and descriptions
9. THE Frontend_Application SHALL remove the existing Inter font configuration

### Requirement 2: Dark Mode Color System

**User Story:** As a designer, I want to implement the exact dark mode color palette from Design.md, so that the application has the premium cybersecurity aesthetic.

#### Acceptance Criteria

1. THE Frontend_Application SHALL define CSS variable --color-void with value #06080B for the deepest background layer
2. THE Frontend_Application SHALL define CSS variable --color-surface with value #0C1017 for secondary backgrounds
3. THE Frontend_Application SHALL define CSS variable --color-card with value #111820 for card surfaces
4. THE Frontend_Application SHALL define CSS variable --color-border with value #1E2D3D for structural borders
5. THE Frontend_Application SHALL define CSS variable --color-neon-green with value #00E87A for success states and primary actions
6. THE Frontend_Application SHALL define CSS variable --color-alert-red with value #FF2B4A for critical threats and errors
7. THE Frontend_Application SHALL define CSS variable --color-info-blue with value #4CB8FF for informational states
8. THE Frontend_Application SHALL define CSS variable --color-warning-amber with value #FFB800 for warning states
9. THE Frontend_Application SHALL define CSS variable --color-text with value #E8EFF7 for primary text
10. THE Frontend_Application SHALL define CSS variable --color-muted with value #5A7A94 for secondary text
11. THE Frontend_Application SHALL define alpha variants (e.g., --color-neon-green-dim with 20% opacity) for each semantic color
12. THE Frontend_Application SHALL apply these color tokens to the .dark class selector in globals.css

### Requirement 3: Light Mode Color System

**User Story:** As a user, I want a light mode option with proper contrast, so that I can use the application in bright environments.

#### Acceptance Criteria

1. THE Frontend_Application SHALL define CSS variable --color-void with value #FFFFFF for light mode backgrounds
2. THE Frontend_Application SHALL define CSS variable --color-surface with value #F8FAFC for light mode secondary surfaces
3. THE Frontend_Application SHALL define CSS variable --color-card with value #FFFFFF for light mode cards
4. THE Frontend_Application SHALL define CSS variable --color-border with value #E2E8F0 for light mode borders
5. THE Frontend_Application SHALL define CSS variable --color-neon-green with value #059669 for light mode success (muted from dark mode)
6. THE Frontend_Application SHALL define CSS variable --color-alert-red with value #DC2626 for light mode errors
7. THE Frontend_Application SHALL define CSS variable --color-info-blue with value #0284C7 for light mode info
8. THE Frontend_Application SHALL define CSS variable --color-warning-amber with value #D97706 for light mode warnings
9. THE Frontend_Application SHALL define CSS variable --color-text with value #0F172A for light mode primary text
10. THE Frontend_Application SHALL define CSS variable --color-muted with value #64748B for light mode secondary text
11. THE Frontend_Application SHALL apply these color tokens to the :root selector in globals.css
12. FOR ALL color combinations in light mode, THE Frontend_Application SHALL maintain WCAG AA contrast ratio of at least 4.5:1 for normal text

### Requirement 4: Theme Switching Infrastructure

**User Story:** As a user, I want to toggle between light and dark modes, so that I can choose my preferred visual experience.

#### Acceptance Criteria

1. THE Frontend_Application SHALL install next-themes package as a dependency
2. THE Frontend_Application SHALL create a ThemeProvider component wrapping the application in app/layout.tsx
3. THE Frontend_Application SHALL configure ThemeProvider with attribute="class" to use class-based theme switching
4. THE Frontend_Application SHALL configure ThemeProvider with defaultTheme="system" to respect user OS preferences
5. THE Frontend_Application SHALL configure ThemeProvider with enableSystem={true} to enable system theme detection
6. THE Frontend_Application SHALL create a ThemeToggle component in components/ThemeToggle.tsx
7. THE ThemeToggle component SHALL display three options: Light, Dark, and System
8. THE ThemeToggle component SHALL use lucide-react icons: Sun for light, Moon for dark, Monitor for system
9. THE ThemeToggle component SHALL call setTheme() from useTheme hook when user selects an option
10. THE ThemeToggle component SHALL visually indicate the currently active theme
11. THE Frontend_Application SHALL add ThemeToggle to the navigation bar on all pages
12. WHEN a user selects a theme, THE Frontend_Application SHALL persist the choice in localStorage
13. WHEN a user refreshes the page, THE Frontend_Application SHALL restore the previously selected theme

### Requirement 5: Tailwind Configuration Update

**User Story:** As a developer, I want Tailwind configured with the Design.md tokens, so that I can use semantic color classes throughout the codebase.

#### Acceptance Criteria

1. THE Frontend_Application SHALL extend Tailwind theme with custom colors mapping to CSS variables
2. THE Frontend_Application SHALL define colors.void as 'var(--color-void)'
3. THE Frontend_Application SHALL define colors.surface as 'var(--color-surface)'
4. THE Frontend_Application SHALL define colors.neonGreen as 'var(--color-neon-green)'
5. THE Frontend_Application SHALL define colors.alertRed as 'var(--color-alert-red)'
6. THE Frontend_Application SHALL define colors.infoBlue as 'var(--color-info-blue)'
7. THE Frontend_Application SHALL define colors.warningAmber as 'var(--color-warning-amber)'
8. THE Frontend_Application SHALL extend Tailwind theme with fontFamily.display, fontFamily.mono, and fontFamily.body
9. THE Frontend_Application SHALL set default borderRadius to 0.5rem (8px) for sharp, professional aesthetic
10. THE Frontend_Application SHALL enable dark mode with darkMode: 'class' in tailwind.config.js

### Requirement 6: Shadcn Component Customization

**User Story:** As a developer, I want shadcn components styled to match Design.md, so that all UI elements have a consistent aesthetic.

#### Acceptance Criteria

1. THE Frontend_Application SHALL update components.json with style: "default" and baseColor: "slate"
2. THE Frontend_Application SHALL customize Button component with 1px borders and minimal border radius
3. THE Frontend_Application SHALL customize Card component with glassmorphism effect (backdrop-blur-sm)
4. THE Frontend_Application SHALL customize Badge component with uppercase text and letter-spacing
5. THE Frontend_Application SHALL customize Dialog component with card background and border styling
6. THE Frontend_Application SHALL ensure all shadcn components use the Design_Tokens color variables
7. THE Frontend_Application SHALL ensure all shadcn components adapt correctly to both light and dark themes
8. THE Frontend_Application SHALL test Button hover states with subtle transform and glow effects

### Requirement 7: Live Threat Banner Component

**User Story:** As a user, I want to see a scrolling threat intelligence banner at the top of the page, so that I'm aware of live security activity.

#### Acceptance Criteria

1. THE Frontend_Application SHALL create a ThreatBanner component in components/ThreatBanner.tsx
2. THE ThreatBanner component SHALL display a fixed banner at the top of the viewport
3. THE ThreatBanner component SHALL use alert-red background with 20% opacity
4. THE ThreatBanner component SHALL display a "LIVE THREATS" label in Share Tech Mono font
5. THE ThreatBanner component SHALL implement infinite horizontal marquee scrolling animation
6. THE ThreatBanner component SHALL display threat items including CVE IDs, agent names, and severity levels
7. THE ThreatBanner component SHALL duplicate threat content to create seamless infinite scroll
8. THE ThreatBanner component SHALL complete one full scroll cycle in 28 seconds
9. THE ThreatBanner component SHALL highlight CVE IDs and severity levels in alert-red color
10. THE ThreatBanner component SHALL adapt colors appropriately in light mode
11. THE ThreatBanner component SHALL remain visible when scrolling down the page
12. THE Frontend_Application SHALL add ThreatBanner to the root layout above all page content

### Requirement 8: Navigation Bar Redesign

**User Story:** As a user, I want a sleek navigation bar with glassmorphism, so that the interface feels modern and premium.

#### Acceptance Criteria

1. THE Frontend_Application SHALL create a Navigation component in components/Navigation.tsx
2. THE Navigation component SHALL use fixed positioning at the top of the viewport
3. THE Navigation component SHALL apply backdrop-filter: blur(12px) for glassmorphism effect
4. THE Navigation component SHALL use semi-transparent background (card color with 85% opacity)
5. THE Navigation component SHALL display the Aegis logo in Syne font with neon-green accent
6. THE Navigation component SHALL display navigation links in Share Tech Mono font with uppercase styling
7. THE Navigation component SHALL include links to Dashboard, Repositories, Analytics, and Scans
8. THE Navigation component SHALL display ThemeToggle component on the right side
9. THE Navigation component SHALL display user avatar or sign-in button on the far right
10. WHEN a user hovers over navigation links, THE Navigation component SHALL transition color to neon-green
11. THE Navigation component SHALL include a 1px bottom border using the border color token
12. THE Navigation component SHALL maintain 48px horizontal padding on desktop
13. THE Navigation component SHALL stack vertically on mobile viewports below 768px width

### Requirement 9: Hero Section Redesign

**User Story:** As a visitor, I want an impressive hero section with animated grid background, so that I understand the product's premium positioning immediately.

#### Acceptance Criteria

1. THE Frontend_Application SHALL update the hero section in app/page.tsx to match Design.md
2. THE hero section SHALL display an animated grid background using CSS background-image with linear gradients
3. THE hero section SHALL animate the grid background position continuously over 20 seconds
4. THE hero section SHALL display a scanning line that moves from top to bottom over 4 seconds
5. THE hero section SHALL display corner brackets in all four corners using neon-green borders
6. THE hero section SHALL display a "System Operational" badge with pulsing green dot
7. THE hero section SHALL display the main heading in Syne font at 90px on desktop
8. THE hero section SHALL highlight "Vulnerability" in neon-green color
9. THE hero section SHALL display the subheading in Share Tech Mono with uppercase and letter-spacing
10. THE hero section SHALL display body text in DM Sans at 17px with muted color
11. THE hero section SHALL display two CTA buttons: primary (filled) and ghost (outlined)
12. THE hero section SHALL display four metric cards below the CTAs in a horizontal row
13. THE hero section SHALL apply radial gradient vignette overlay to darken edges
14. THE hero section SHALL ensure all animations perform smoothly at 60fps

### Requirement 10: Agent Grid Redesign

**User Story:** As a user, I want to see the agent showcase in a bento-box grid layout, so that I can understand each agent's role clearly.

#### Acceptance Criteria

1. THE Frontend_Application SHALL update the agent showcase section in app/page.tsx
2. THE agent grid SHALL use CSS Grid with auto-fit and minmax(280px, 1fr) for responsive columns
3. THE agent grid SHALL use 1px gap with border color as the gap background (bento effect)
4. THE agent grid SHALL wrap the entire grid with a 1px border
5. WHEN displaying an agent card, THE Frontend_Application SHALL show agent ID in Share Tech Mono
6. WHEN displaying an agent card, THE Frontend_Application SHALL show agent icon as a large emoji or symbol
7. WHEN displaying an agent card, THE Frontend_Application SHALL show agent name in Syne font at 20px
8. WHEN displaying an agent card, THE Frontend_Application SHALL show agent role in Share Tech Mono uppercase
9. WHEN displaying an agent card, THE Frontend_Application SHALL show agent description in DM Sans at 14px
10. WHEN displaying an agent card, THE Frontend_Application SHALL show model badge in Share Tech Mono with border
11. WHEN displaying an agent card, THE Frontend_Application SHALL show large faint background letter (A, B, C, D)
12. WHEN displaying an agent card, THE Frontend_Application SHALL apply 2px colored top border matching agent color
13. WHEN a user hovers over an agent card, THE Frontend_Application SHALL increase the top border height to 3px
14. WHEN a user hovers over an agent card, THE Frontend_Application SHALL slightly lighten the background
15. THE agent cards SHALL use staggered entrance animation with 120ms delay between cards

### Requirement 11: Live Activity Feed Component

**User Story:** As a user, I want to see a terminal-style live activity feed, so that I can monitor agent actions in real-time.

#### Acceptance Criteria

1. THE Frontend_Application SHALL create a LiveActivityFeed component in components/LiveActivityFeed.tsx
2. THE LiveActivityFeed component SHALL display a bordered panel with card background
3. THE LiveActivityFeed component SHALL display a header with "Swarm Activity Feed — Live" title
4. THE LiveActivityFeed component SHALL display a pulsing green dot next to the title
5. THE LiveActivityFeed component SHALL display a live clock in HH:MM:SS format in the header
6. THE LiveActivityFeed component SHALL display log entries in a scrollable container with max-height 280px
7. WHEN displaying a log entry, THE LiveActivityFeed component SHALL show timestamp in muted color
8. WHEN displaying a log entry, THE LiveActivityFeed component SHALL show agent badge with agent-specific color
9. WHEN displaying a log entry, THE LiveActivityFeed component SHALL show log message in Share Tech Mono
10. WHEN displaying a log entry, THE LiveActivityFeed component SHALL show status badge (OK, WARN, CRIT, INFO)
11. WHEN displaying a log entry, THE LiveActivityFeed component SHALL highlight keywords in semantic colors
12. THE LiveActivityFeed component SHALL apply fade-in animation to new log entries
13. THE LiveActivityFeed component SHALL auto-scroll to bottom when new entries appear
14. THE LiveActivityFeed component SHALL simulate live activity by cycling through predefined log messages
15. THE LiveActivityFeed component SHALL use terminal-style styling with scanline overlay effect

### Requirement 12: Pipeline Visualization Component

**User Story:** As a user, I want to see the agent pipeline as a horizontal flow diagram, so that I understand the data flow through the system.

#### Acceptance Criteria

1. THE Frontend_Application SHALL create a PipelineVisualization component in components/PipelineVisualization.tsx
2. THE PipelineVisualization component SHALL display pipeline nodes in a horizontal flexbox layout
3. WHEN displaying a pipeline node, THE PipelineVisualization component SHALL show node label in Share Tech Mono
4. WHEN displaying a pipeline node, THE PipelineVisualization component SHALL show node name in Syne font
5. WHEN displaying a pipeline node, THE PipelineVisualization component SHALL apply colored border matching node type
6. WHEN displaying a pipeline node, THE PipelineVisualization component SHALL use card background with 1px border
7. THE PipelineVisualization component SHALL display arrow connectors between nodes using → symbol
8. THE PipelineVisualization component SHALL animate arrows with pulsing opacity
9. THE PipelineVisualization component SHALL display parallel agents (D, A, E) in a vertical sub-grid
10. WHEN a node is active, THE PipelineVisualization component SHALL display pulsing ring animations
11. WHEN a node is active, THE PipelineVisualization component SHALL apply glow effect with node color
12. THE PipelineVisualization component SHALL display feedback loop indicator below the main pipeline
13. THE PipelineVisualization component SHALL use dashed line for feedback loop with amber color
14. THE PipelineVisualization component SHALL ensure horizontal scrolling on mobile viewports

### Requirement 13: Metrics Display Component

**User Story:** As a user, I want to see key metrics in large, prominent cards, so that I can quickly assess system performance.

#### Acceptance Criteria

1. THE Frontend_Application SHALL create a MetricsRow component in components/MetricsRow.tsx
2. THE MetricsRow component SHALL display metrics in a CSS Grid with 4 equal columns
3. THE MetricsRow component SHALL use 1px gap with border color (bento effect)
4. THE MetricsRow component SHALL wrap the grid with a 1px border
5. WHEN displaying a metric, THE MetricsRow component SHALL show the numeric value in Syne font at 52px
6. WHEN displaying a metric, THE MetricsRow component SHALL highlight key numbers in neon-green
7. WHEN displaying a metric, THE MetricsRow component SHALL show the label in Share Tech Mono uppercase
8. WHEN displaying a metric, THE MetricsRow component SHALL display a large faint background symbol
9. THE MetricsRow component SHALL use surface background color for each cell
10. THE MetricsRow component SHALL apply count-up animation when metrics first appear
11. THE MetricsRow component SHALL stack into 2 columns on tablet viewports
12. THE MetricsRow component SHALL stack into 1 column on mobile viewports

### Requirement 14: Dashboard Bento Layout

**User Story:** As a user, I want the dashboard organized in a bento-box layout, so that information is clearly separated and scannable.

#### Acceptance Criteria

1. THE Frontend_Application SHALL redesign app/dashboard/page.tsx using CSS Grid
2. THE dashboard SHALL define a grid with areas for stats, repositories, and activity
3. THE dashboard SHALL use 1px gaps between grid cells with border color
4. THE dashboard SHALL display global stats in the top row spanning full width
5. THE dashboard SHALL display repository list in the left column (2/3 width)
6. THE dashboard SHALL display activity feed in the right column (1/3 width)
7. THE dashboard SHALL use card background for each grid cell
8. THE dashboard SHALL apply 1px borders to all grid cells
9. THE dashboard SHALL ensure grid collapses to single column on mobile viewports
10. THE dashboard SHALL maintain consistent padding (32px) within each grid cell

### Requirement 15: Repository Card Redesign

**User Story:** As a user, I want repository cards styled to match the stack-cell aesthetic, so that the dashboard feels cohesive.

#### Acceptance Criteria

1. THE Frontend_Application SHALL update repository cards to use card background
2. THE repository card SHALL display repo name in Syne font at 18px
3. THE repository card SHALL display repo URL in Share Tech Mono at 11px with muted color
4. THE repository card SHALL display status badge with colored background (green for active, amber for scanning)
5. THE repository card SHALL display last scan timestamp in Share Tech Mono
6. THE repository card SHALL display vulnerability count with alert-red color if count > 0
7. THE repository card SHALL display action buttons with ghost styling
8. WHEN a user hovers over a repository card, THE repository card SHALL apply subtle transform translateY(-2px)
9. WHEN a user hovers over a repository card, THE repository card SHALL apply glow shadow effect
10. THE repository card SHALL use 1px border with border color
11. THE repository card SHALL include a colored left accent bar matching status

### Requirement 16: Scan Details Page Redesign

**User Story:** As a user, I want the scan details page to use the terminal aesthetic, so that technical information is presented clearly.

#### Acceptance Criteria

1. THE Frontend_Application SHALL redesign app/scans/[id]/page.tsx with bento layout
2. THE scan details page SHALL display pipeline status in the top section
3. THE scan details page SHALL display agent logs in a terminal-style panel
4. THE scan details page SHALL display code diffs in a bordered panel with syntax highlighting
5. THE scan details page SHALL display findings in a grid of stack-cells
6. THE agent logs panel SHALL use Share Tech Mono font
7. THE agent logs panel SHALL use near-black background (#050508)
8. THE agent logs panel SHALL apply scanline overlay animation
9. THE agent logs panel SHALL apply horizontal line pattern for CRT effect
10. THE code diff panel SHALL use theme-aware syntax highlighting (light theme in light mode, dark in dark mode)
11. THE findings grid SHALL use 1px gaps and borders (bento effect)
12. WHEN displaying a finding, THE scan details page SHALL show severity badge with semantic color
13. WHEN displaying a finding, THE scan details page SHALL show CWE ID in Share Tech Mono
14. WHEN displaying a finding, THE scan details page SHALL show description in DM Sans

### Requirement 17: Animation System Implementation

**User Story:** As a developer, I want reusable animation utilities, so that micro-animations are consistent across the application.

#### Acceptance Criteria

1. THE Frontend_Application SHALL define @keyframes pulse-ring in globals.css for concentric pulsing rings
2. THE Frontend_Application SHALL define @keyframes pulse-ring-2 in globals.css for staggered secondary ring
3. THE Frontend_Application SHALL define @keyframes pipeline-fill in globals.css for left-to-right gradient fill
4. THE Frontend_Application SHALL define @keyframes scanline-drift in globals.css for downward CRT scanline
5. THE Frontend_Application SHALL define @keyframes status-glow in globals.css for pulsing glow effect
6. THE Frontend_Application SHALL define @keyframes pulse-glow in globals.css for opacity pulsing
7. THE Frontend_Application SHALL define @keyframes agent-appear in globals.css for entrance animation
8. THE Frontend_Application SHALL define @keyframes shimmer-sweep in globals.css for button shimmer
9. THE Frontend_Application SHALL define @keyframes marquee in globals.css for horizontal scrolling
10. THE Frontend_Application SHALL define utility class .aegis-pipeline-node-active that applies pulse-ring animations
11. THE Frontend_Application SHALL define utility class .aegis-terminal that applies scanline effects
12. THE Frontend_Application SHALL define utility class .aegis-btn-shimmer that applies shimmer on hover
13. THE Frontend_Application SHALL define utility class .animate-agent-appear with staggered delays
14. THE Frontend_Application SHALL ensure all animations use cubic-bezier easing for smooth motion

### Requirement 18: Glassmorphism Utility Classes

**User Story:** As a developer, I want glassmorphism utility classes, so that I can easily apply the effect to components.

#### Acceptance Criteria

1. THE Frontend_Application SHALL define utility class .aegis-glass in globals.css
2. THE .aegis-glass class SHALL apply background with card color at 70% opacity
3. THE .aegis-glass class SHALL apply backdrop-filter: blur(12px)
4. THE .aegis-glass class SHALL apply -webkit-backdrop-filter: blur(12px) for Safari support
5. THE .aegis-glass class SHALL apply 1px border with 8% white opacity
6. THE Frontend_Application SHALL define utility class .aegis-glass-nav for navigation bars
7. THE .aegis-glass-nav class SHALL use 85% opacity for stronger background
8. THE Frontend_Application SHALL test glassmorphism effect over various backgrounds
9. THE Frontend_Application SHALL ensure glassmorphism adapts correctly in light mode

### Requirement 19: Background Pattern Utilities

**User Story:** As a developer, I want background pattern utilities, so that I can add visual texture to sections.

#### Acceptance Criteria

1. THE Frontend_Application SHALL define utility class .aegis-grid-pattern in globals.css
2. THE .aegis-grid-pattern class SHALL create a grid using linear-gradient with 60px spacing
3. THE .aegis-grid-pattern class SHALL use 4% white opacity for grid lines
4. THE Frontend_Application SHALL define utility class .aegis-hex-pattern in globals.css
5. THE .aegis-hex-pattern class SHALL use SVG data URI for hexagon pattern
6. THE .aegis-hex-pattern class SHALL use 3% white opacity for hexagons
7. THE Frontend_Application SHALL define utility class .aegis-noise in globals.css
8. THE .aegis-noise class SHALL apply SVG noise filter as ::before pseudo-element
9. THE .aegis-noise class SHALL use 15% opacity for subtle texture
10. THE Frontend_Application SHALL ensure patterns adapt appropriately in light mode

### Requirement 20: Glow Effect Utilities

**User Story:** As a developer, I want glow effect utilities, so that I can highlight active or important elements.

#### Acceptance Criteria

1. THE Frontend_Application SHALL define utility class .aegis-glow in globals.css
2. THE .aegis-glow class SHALL apply box-shadow with info-blue color at 20% and 7% opacity
3. THE Frontend_Application SHALL define utility class .aegis-glow-red for critical elements
4. THE .aegis-glow-red class SHALL apply box-shadow with alert-red color
5. THE Frontend_Application SHALL define utility class .aegis-glow-emerald for success elements
6. THE .aegis-glow-emerald class SHALL apply box-shadow with neon-green color
7. THE Frontend_Application SHALL define utility class .aegis-glow-amber for warning elements
8. THE .aegis-glow-amber class SHALL apply box-shadow with warning-amber color
9. THE Frontend_Application SHALL ensure glow effects are visible but not overwhelming
10. THE Frontend_Application SHALL reduce glow intensity in light mode for subtlety

### Requirement 21: Gradient Text Utilities

**User Story:** As a developer, I want gradient text utilities, so that I can create eye-catching headings.

#### Acceptance Criteria

1. THE Frontend_Application SHALL define utility class .aegis-gradient-text in globals.css
2. THE .aegis-gradient-text class SHALL apply linear-gradient from info-blue to neon-green at 135deg
3. THE .aegis-gradient-text class SHALL apply background-clip: text
4. THE .aegis-gradient-text class SHALL apply -webkit-background-clip: text for Safari support
5. THE .aegis-gradient-text class SHALL apply -webkit-text-fill-color: transparent
6. THE Frontend_Application SHALL define utility class .aegis-gradient-text-danger
7. THE .aegis-gradient-text-danger class SHALL apply linear-gradient from alert-red to warning-amber
8. THE Frontend_Application SHALL ensure gradient text remains readable in both themes

### Requirement 22: Responsive Design Implementation

**User Story:** As a user, I want the application to work perfectly on mobile devices, so that I can monitor security on the go.

#### Acceptance Criteria

1. THE Frontend_Application SHALL use responsive breakpoints: sm (640px), md (768px), lg (1024px), xl (1280px)
2. WHEN viewport width is below 768px, THE Frontend_Application SHALL stack navigation links vertically
3. WHEN viewport width is below 768px, THE Frontend_Application SHALL collapse agent grid to 1 column
4. WHEN viewport width is below 768px, THE Frontend_Application SHALL collapse metrics row to 2 columns
5. WHEN viewport width is below 640px, THE Frontend_Application SHALL collapse metrics row to 1 column
6. WHEN viewport width is below 768px, THE Frontend_Application SHALL collapse dashboard grid to 1 column
7. WHEN viewport width is below 768px, THE Frontend_Application SHALL reduce hero heading font size to 44px
8. WHEN viewport width is below 768px, THE Frontend_Application SHALL reduce horizontal padding to 24px
9. WHEN viewport width is below 768px, THE Frontend_Application SHALL enable horizontal scrolling for pipeline
10. THE Frontend_Application SHALL test all layouts at 375px, 768px, 1024px, and 1440px widths
11. THE Frontend_Application SHALL ensure touch targets are at least 44x44px on mobile
12. THE Frontend_Application SHALL ensure text remains readable at all viewport sizes

### Requirement 23: Accessibility Compliance

**User Story:** As a user with visual impairments, I want the application to meet accessibility standards, so that I can use it effectively.

#### Acceptance Criteria

1. FOR ALL text on colored backgrounds in dark mode, THE Frontend_Application SHALL maintain WCAG AA contrast ratio of 4.5:1
2. FOR ALL text on colored backgrounds in light mode, THE Frontend_Application SHALL maintain WCAG AA contrast ratio of 4.5:1
3. THE Frontend_Application SHALL ensure focus indicators are visible on all interactive elements
4. THE Frontend_Application SHALL ensure focus indicators have 3:1 contrast ratio against background
5. THE Frontend_Application SHALL provide aria-label attributes for icon-only buttons
6. THE Frontend_Application SHALL provide alt text for all decorative images
7. THE Frontend_Application SHALL ensure animations respect prefers-reduced-motion media query
8. WHEN prefers-reduced-motion is set, THE Frontend_Application SHALL disable marquee scrolling
9. WHEN prefers-reduced-motion is set, THE Frontend_Application SHALL disable pulsing animations
10. WHEN prefers-reduced-motion is set, THE Frontend_Application SHALL disable scanning line animation
11. THE Frontend_Application SHALL ensure keyboard navigation works for all interactive elements
12. THE Frontend_Application SHALL ensure screen readers can access all content

### Requirement 24: Performance Optimization

**User Story:** As a user, I want the application to load quickly and run smoothly, so that I have a responsive experience.

#### Acceptance Criteria

1. THE Frontend_Application SHALL load fonts using font-display: swap to prevent blocking
2. THE Frontend_Application SHALL preload critical fonts in the document head
3. THE Frontend_Application SHALL use CSS containment for independent components
4. THE Frontend_Application SHALL use will-change property only on actively animating elements
5. THE Frontend_Application SHALL ensure animations run at 60fps on modern devices
6. THE Frontend_Application SHALL lazy-load components below the fold
7. THE Frontend_Application SHALL optimize SVG patterns for minimal file size
8. THE Frontend_Application SHALL use CSS transforms instead of position changes for animations
9. THE Frontend_Application SHALL debounce scroll event listeners
10. THE Frontend_Application SHALL measure and maintain Lighthouse performance score above 90

### Requirement 25: Theme Persistence and System Integration

**User Story:** As a user, I want my theme preference to persist across sessions and respect my OS settings, so that I have a consistent experience.

#### Acceptance Criteria

1. WHEN a user selects a theme, THE Theme_System SHALL store the preference in localStorage with key "theme"
2. WHEN a user refreshes the page, THE Theme_System SHALL read localStorage and apply the stored theme
3. WHEN a user selects "System" theme, THE Theme_System SHALL detect OS preference using prefers-color-scheme
4. WHEN OS theme changes while "System" is selected, THE Theme_System SHALL update the application theme automatically
5. WHEN no theme preference exists, THE Theme_System SHALL default to "System" mode
6. THE Theme_System SHALL apply theme class to html element before first paint to prevent flash
7. THE Theme_System SHALL use next-themes suppressHydrationWarning to prevent SSR mismatch
8. THE Frontend_Application SHALL test theme switching with no visible flash or layout shift
