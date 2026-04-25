/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans:    ['var(--font-dm-sans)', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono:    ['var(--font-share-tech-mono)', 'ui-monospace', 'SFMono-Regular', 'monospace'],
        display: ['var(--font-syne)', 'var(--font-dm-sans)', 'sans-serif'],
      },
      colors: {
        // Base
        background: 'var(--background)',
        surface:    'var(--surface)',
        card:       { DEFAULT: 'var(--card)', foreground: 'var(--foreground)' },
        foreground: 'var(--foreground)',
        muted:      { DEFAULT: 'var(--muted)', foreground: 'var(--muted)' },
        border:     'var(--border)',
        input:      'var(--input)',
        ring:       'var(--ring)',

        // Semantic accents
        green:  { DEFAULT: 'var(--green)', dim: 'var(--green-dim)' },
        red:    { DEFAULT: 'var(--red)',   dim: 'var(--red-dim)' },
        blue:   { DEFAULT: 'var(--blue)',  dim: 'var(--blue-dim)' },
        amber:  { DEFAULT: 'var(--amber)', dim: 'var(--amber-dim)' },
        violet: { DEFAULT: 'var(--violet)',dim: 'var(--violet-dim)' },

        // shadcn compatibility
        primary:     { DEFAULT: 'var(--primary)', foreground: 'var(--primary-foreground)' },
        secondary:   { DEFAULT: 'var(--secondary)', foreground: 'var(--secondary-foreground)' },
        destructive: { DEFAULT: 'var(--destructive)', foreground: 'var(--destructive-foreground)' },
        accent:      { DEFAULT: 'var(--accent)', foreground: 'var(--accent-foreground)' },
        popover:     { DEFAULT: 'var(--popover)', foreground: 'var(--popover-foreground)' },

        // Agent identity
        'agent-finder':    'var(--agent-finder)',
        'agent-exploiter': 'var(--agent-exploiter)',
        'agent-engineer':  'var(--agent-engineer)',
        'agent-verifier':  'var(--agent-verifier)',

        // Chart
        'chart-1': 'var(--chart-1)',
        'chart-2': 'var(--chart-2)',
        'chart-3': 'var(--chart-3)',
        'chart-4': 'var(--chart-4)',
        'chart-5': 'var(--chart-5)',
      },
      borderRadius: {
        DEFAULT: '4px',
        none: '0',
        sm:   '2px',
        md:   '4px',
        lg:   '6px',
        xl:   '8px',
        '2xl':'10px',
        full: '9999px',
      },
      boxShadow: {
        'green-glow': '0 0 20px rgba(0,232,122,0.2), 0 0 60px rgba(0,232,122,0.07)',
        'red-glow':   '0 0 20px rgba(255,43,74,0.25), 0 0 50px rgba(255,43,74,0.1)',
        'blue-glow':  '0 0 20px rgba(76,184,255,0.25)',
        'amber-glow': '0 0 20px rgba(255,184,0,0.25)',
      },
      animation: {
        'pulse-ring':  'pulse-ring 1.8s ease-out infinite',
        'pulse-ring-2':'pulse-ring-2 1.8s ease-out infinite 0.4s',
        'scanline':    'scanline-drift 6s linear infinite',
        'marquee':     'marquee 28s linear infinite',
        'arrow-pulse': 'arrowPulse 2s ease infinite',
        'status-glow': 'status-glow 2.5s ease-in-out infinite',
        'agent-appear':'agent-appear 0.5s cubic-bezier(0.16,1,0.3,1) both',
        'gradient-sweep':'gradient-sweep 3s linear infinite',
        'count-up':    'count-up 0.4s cubic-bezier(0.16,1,0.3,1) both',
        'cursor-blink':'cursor-blink 1s step-end infinite',
        'status-ping': 'status-ping 1.5s ease-out infinite',
        'grid-shift':  'gridShift 20s linear infinite',
        'scan-down':   'scanDown 4s ease-in-out infinite',
        'fade-in-up':  'fadeInUp 0.4s ease both',
        'shimmer':     'shimmerSweep 0.6s ease forwards',
        'pipeline-fill':'pipeline-fill 0.6s cubic-bezier(0.16,1,0.3,1) both',
      },
      keyframes: {
        gridShift: {
          '0%':   { backgroundPosition: '0 0, 0 0' },
          '100%': { backgroundPosition: '60px 60px, 60px 60px' },
        },
        scanDown: {
          '0%':   { top: '-2px', opacity: '0' },
          '10%':  { opacity: '0.6' },
          '90%':  { opacity: '0.6' },
          '100%': { top: '100%', opacity: '0' },
        },
        arrowPulse: {
          '0%, 100%': { opacity: '0.3' },
          '50%':       { opacity: '1' },
        },
        fadeInUp: {
          from: { opacity: '0', transform: 'translateY(-4px)' },
          to:   { opacity: '1', transform: 'none' },
        },
        shimmerSweep: {
          '0%':   { transform: 'translateX(-100%) skewX(-15deg)' },
          '100%': { transform: 'translateX(200%) skewX(-15deg)' },
        },
        'pulse-ring': {
          '0%':        { transform: 'scale(1)',   opacity: '0.7' },
          '70%, 100%': { transform: 'scale(1.8)', opacity: '0' },
        },
        'pulse-ring-2': {
          '0%':        { transform: 'scale(1)',   opacity: '0.5' },
          '70%, 100%': { transform: 'scale(2.2)', opacity: '0' },
        },
        'pipeline-fill': {
          '0%':   { clipPath: 'inset(0 100% 0 0)' },
          '100%': { clipPath: 'inset(0 0% 0 0)' },
        },
        'scanline-drift': {
          '0%':   { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(200%)' },
        },
        'status-glow': {
          '0%, 100%': { boxShadow: '0 0 0 1px rgba(0,232,122,0.3), 0 0 20px rgba(0,232,122,0.08)' },
          '50%':       { boxShadow: '0 0 0 1px rgba(0,232,122,0.6), 0 0 30px rgba(0,232,122,0.15)' },
        },
        'agent-appear': {
          '0%':   { opacity: '0', transform: 'translateY(16px) scale(0.97)' },
          '100%': { opacity: '1', transform: 'none' },
        },
        'gradient-sweep': {
          '0%':   { backgroundPosition: '0% 50%' },
          '50%':  { backgroundPosition: '100% 50%' },
          '100%': { backgroundPosition: '0% 50%' },
        },
        'count-up': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to:   { opacity: '1', transform: 'none' },
        },
        'cursor-blink': {
          '0%, 50%':   { opacity: '1' },
          '51%, 100%': { opacity: '0' },
        },
        'status-ping': {
          '0%':         { transform: 'scale(1)', opacity: '0.8' },
          '75%, 100%':  { transform: 'scale(2)', opacity: '0' },
        },
        marquee: {
          from: { transform: 'translateX(0)' },
          to:   { transform: 'translateX(-50%)' },
        },
      },
    },
  },
  plugins: [],
}
