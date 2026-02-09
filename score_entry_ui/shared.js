/* ==========================================================
   Gymfest Shared Utilities
   Common JavaScript used across all score dashboard pages.
   Import via: <script src="/shared.js"></script>
   ========================================================== */

// ---- Score Formatting ----

/** Format score as plain text, always 3 decimal places (e.g. "9.325", "9.400") */
function formatScoreDisplay(val) {
    if (val === null || val === undefined) return '\u2013';
    const num = typeof val === 'string' ? parseFloat(val) : val;
    if (isNaN(num)) return '\u2013';
    const rounded = Math.round(num * 1000) / 1000;
    return rounded.toFixed(3);
}

/**
 * Format score as HTML with major/minor split and dimmed trailing zeros.
 * Major = integer part (full size), Minor = decimals (slightly smaller).
 * Trailing zeros get a dimmed opacity class.
 * @param {*} val - The score value
 * @param {number} [decimals=3] - Number of decimal places to display
 */
function formatScoreHtml(val, decimals) {
    if (decimals === undefined) decimals = 3;
    if (val === null || val === undefined) return '\u2013';
    const num = typeof val === 'string' ? parseFloat(val) : val;
    if (isNaN(num)) return '\u2013';
    const factor = Math.pow(10, decimals);
    const rounded = Math.round(num * factor) / factor;
    const full = rounded.toFixed(decimals);
    const dotIdx = full.indexOf('.');
    if (dotIdx === -1) return `<span class="score-major">${full}</span>`;
    const major = full.slice(0, dotIdx);
    const decStr = full.slice(dotIdx + 1);
    const stripped = decStr.replace(/0+$/, '');
    const sig = stripped || '';
    const trail = decStr.slice(stripped.length);
    let minorHtml = '.';
    if (sig) minorHtml += sig;
    if (trail) minorHtml += `<span class="score-trail">${trail}</span>`;
    return `<span class="score-major">${major}</span><span class="score-minor">${minorHtml}</span>`;
}

/**
 * Safe number formatting helper. Returns '-' for null/undefined/NaN.
 * Handles string decimals from PostgreSQL.
 */
function toFixed(val, decimals) {
    if (val === null || val === undefined) return '-';
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return isNaN(num) ? '-' : num.toFixed(decimals);
}

// ---- Date Formatting ----

/** Parse a date string, handling ISO and date-only formats. Returns Date or null. */
function parseDate(dateStr) {
    if (!dateStr) return null;
    let date;
    if (typeof dateStr === 'string') {
        date = new Date(dateStr.includes('T') ? dateStr : dateStr + 'T00:00:00');
    } else {
        date = new Date(dateStr);
    }
    return isNaN(date.getTime()) ? null : date;
}

/** Format a single date string for display (e.g. "Jan 15, 2026"). Returns '-' on failure. */
function formatDate(dateStr) {
    const date = parseDate(dateStr);
    if (!date) return '-';
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

/** Format an array of date strings. Shows abbreviated list or "date + N more". */
function formatMeetDates(dates) {
    if (!dates || dates.length === 0) return '-';
    if (dates.length === 1) return formatDate(dates[0]);
    const formatted = dates.map(d => {
        const date = parseDate(d);
        if (!date) return '';
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }).filter(d => d);
    if (formatted.length === 0) return '-';
    if (formatted.length <= 3) return formatted.join(', ');
    return `${formatted[0]} + ${dates.length - 1} more`;
}

// ---- Level Helpers ----

const LEVEL_ORDER = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'XB', 'XS', 'XG', 'XP', 'XD', 'XSA'];

const LEVEL_GRADIENT_STOPS = [
    [235, 100, 100], [235, 160, 75], [220, 210, 70], [90, 210, 100],
    [70, 210, 210], [90, 140, 235], [155, 100, 235], [220, 110, 210]
];

const XCEL_COLORS = {
    'XB': { text: '#cd7f32', bg: 'rgba(205,127,50,0.15)' },
    'XS': { text: '#c0c0c0', bg: 'rgba(192,192,192,0.15)' },
    'XG': { text: '#ffd700', bg: 'rgba(255,215,0,0.12)' },
    'XP': { text: '#e5e4e2', bg: 'rgba(229,228,226,0.12)' },
    'XD': { text: '#64d2ff', bg: 'rgba(100,210,255,0.12)' },
    'XSA': { text: '#4f8fcc', bg: 'rgba(15,82,186,0.18)' }
};

function _interpolateLevelColor(level) {
    const num = parseInt(level);
    if (isNaN(num) || num < 1 || num > 10) return null;
    const t = Math.max(0, Math.min(1, (num - 3) / 7));
    const idx = t * (LEVEL_GRADIENT_STOPS.length - 1);
    const lo = Math.floor(idx), hi = Math.min(lo + 1, LEVEL_GRADIENT_STOPS.length - 1), f = idx - lo;
    const r = Math.round(LEVEL_GRADIENT_STOPS[lo][0] + (LEVEL_GRADIENT_STOPS[hi][0] - LEVEL_GRADIENT_STOPS[lo][0]) * f);
    const g = Math.round(LEVEL_GRADIENT_STOPS[lo][1] + (LEVEL_GRADIENT_STOPS[hi][1] - LEVEL_GRADIENT_STOPS[lo][1]) * f);
    const b = Math.round(LEVEL_GRADIENT_STOPS[lo][2] + (LEVEL_GRADIENT_STOPS[hi][2] - LEVEL_GRADIENT_STOPS[lo][2]) * f);
    return { r, g, b };
}

/** Get level color as { text, bg } for badges and inline styles. */
function getLevelColor(level) {
    if (XCEL_COLORS[level]) return XCEL_COLORS[level];
    const rgb = _interpolateLevelColor(level);
    if (rgb) return { text: `rgb(${rgb.r},${rgb.g},${rgb.b})`, bg: `rgba(${rgb.r},${rgb.g},${rgb.b},0.12)` };
    return { text: '#64d2ff', bg: 'rgba(100,210,255,0.12)' };
}

/** Get level color as a single CSS color string (for chart lines, etc). */
function getLevelChartColor(level) {
    const xcelSolid = {
        'XB': '#cd7f32', 'XS': '#c0c0c0', 'XG': '#ffd700',
        'XP': '#e5e4e2', 'XD': '#64d2ff', 'XSA': '#4f8fcc'
    };
    if (xcelSolid[level]) return xcelSolid[level];
    const rgb = _interpolateLevelColor(level);
    if (rgb) return `rgb(${rgb.r},${rgb.g},${rgb.b})`;
    return '#64d2ff';
}

/** Numeric sort order for levels. Unknown levels sort last. */
function getLevelSortOrder(level) {
    const idx = LEVEL_ORDER.indexOf(level);
    return idx >= 0 ? idx : 999;
}

// ---- Misc Helpers ----

/** Position a tooltip element above (or below) its parent cell within the viewport. */
function positionTooltip(event) {
    const cell = event.currentTarget;
    const tooltip = cell.querySelector('.tooltip');
    if (!tooltip) return;
    const rect = cell.getBoundingClientRect();
    const tr = tooltip.getBoundingClientRect();
    let left = rect.left + (rect.width / 2) - (tr.width / 2);
    let top = rect.top - tr.height - 10;
    if (left < 10) left = 10;
    if (left + tr.width > window.innerWidth - 10) left = window.innerWidth - tr.width - 10;
    if (top < 10) top = rect.bottom + 10;
    tooltip.style.left = left + 'px';
    tooltip.style.top = top + 'px';
}

/** Get the display string for a placement number. */
function getPlaceDisplay(place) {
    if (!place) return '';
    return `${place}`;
}

/** Extract first name from a full name string. */
function firstName(fullName) {
    return (fullName || '').split(' ')[0];
}
