/**
 * Advanced Timeline Component
 * Inspired by Autodesk Construction Cloud Design Collaboration
 * 
 * Features:
 * - Hybrid Rendering: Canvas for Axis/Grid (Performance), DOM for Nodes (Interactivity/A11y)
 * - Continuous Zoom (Years -> Minutes)
 * - Dynamic Clustering
 * - Focal Zoom
 */

class Timeline {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) throw new Error(`Container ${containerId} not found`);

        // Configuration
        this.options = Object.assign({
            minClusterDistance: 30, // px
            zoomSpeed: 0.001,
            rowHeight: 60,
            eventColor: '#10b981', // emerald-500
            clusterColor: '#059669', // emerald-600
        }, options);

        // State
        this.width = this.container.clientWidth;
        this.height = this.container.clientHeight;
        this.events = [];
        this.clusters = [];

        // Viewport (Time in ms)
        // Default to last 30 days
        const now = Date.now();
        this.viewport = {
            start: now - (30 * 24 * 60 * 60 * 1000),
            end: now + (2 * 24 * 60 * 60 * 1000) // Padding
        };

        this.isDragging = false;
        this.lastMouseX = 0;

        this.initDOM();
        this.bindEvents();

        // Start Loop
        this.render();
    }

    initDOM() {
        this.container.innerHTML = '';
        this.container.style.position = 'relative';
        this.container.style.overflow = 'hidden';
        this.container.style.userSelect = 'none';

        // 1. Canvas Layer (Axis, Grid)
        this.canvas = document.createElement('canvas');
        this.canvas.style.position = 'absolute';
        this.canvas.style.top = '0';
        this.canvas.style.left = '0';
        this.canvas.style.zIndex = '0';
        this.container.appendChild(this.canvas);
        this.ctx = this.canvas.getContext('2d');

        // 2. Event Layer (DOM Nodes)
        this.eventLayer = document.createElement('div');
        this.eventLayer.style.position = 'absolute';
        this.eventLayer.style.top = '0';
        this.eventLayer.style.left = '0';
        this.eventLayer.style.width = '100%';
        this.eventLayer.style.height = '100%';
        this.eventLayer.style.zIndex = '10';
        this.eventLayer.style.pointerEvents = 'none'; // Let clicks pass to SVG/Buttons specifically
        this.container.appendChild(this.eventLayer);

        // Resize Observer
        this.resizeObserver = new ResizeObserver(() => this.handleResize());
        this.resizeObserver.observe(this.container);

        this.handleResize();
    }

    bindEvents() {
        // Wheel Zoom
        this.container.addEventListener('wheel', (e) => this.handleWheel(e), { passive: false });

        // Pan
        this.container.addEventListener('mousedown', (e) => {
            this.isDragging = true;
            this.lastMouseX = e.clientX;
            this.container.style.cursor = 'grabbing';
        });

        window.addEventListener('mousemove', (e) => {
            if (!this.isDragging) return;
            const dx = e.clientX - this.lastMouseX;
            this.lastMouseX = e.clientX;
            this.pan(dx);
        });

        window.addEventListener('mouseup', () => {
            if (this.isDragging) {
                this.isDragging = false;
                this.container.style.cursor = 'default';
            }
        });
    }

    handleResize() {
        this.width = this.container.clientWidth;
        this.height = this.container.clientHeight;

        // Higher DPI for Canvas
        const dpr = window.devicePixelRatio || 1;
        this.canvas.width = this.width * dpr;
        this.canvas.height = this.height * dpr;
        this.canvas.style.width = `${this.width}px`;
        this.canvas.style.height = `${this.height}px`;
        this.ctx.scale(dpr, dpr);

        this.requestRender();
    }

    setEvents(eventsData) {
        console.log("Timeline.setEvents received:", eventsData);
        // Expected [{id, timestamp, title, ...}]
        this.events = eventsData.map(e => {
            const ts = new Date(e.timestamp).getTime();
            if (isNaN(ts)) {
                console.warn("Invalid timestamp for event:", e);
                return null;
            }
            return {
                ...e,
                timestamp: ts
            };
        }).filter(e => e !== null).sort((a, b) => a.timestamp - b.timestamp);

        this.requestRender();
    }

    timeToX(time) {
        const range = this.viewport.end - this.viewport.start;
        return ((time - this.viewport.start) / range) * this.width;
    }

    xToTime(x) {
        const range = this.viewport.end - this.viewport.start;
        return this.viewport.start + (x / this.width) * range;
    }

    pan(dxPx) {
        const range = this.viewport.end - this.viewport.start;
        const dt = (dxPx / this.width) * range;

        this.viewport.start -= dt;
        this.viewport.end -= dt;
        this.requestRender();
    }

    handleWheel(e) {
        e.preventDefault();

        const zoomFactor = Math.exp(-e.deltaY * this.options.zoomSpeed);
        const rect = this.container.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;

        // Focal Zoom: Time under mouse should stay under mouse
        const timeUnderMouse = this.xToTime(mouseX);

        const currentRange = this.viewport.end - this.viewport.start;
        const newRange = currentRange / zoomFactor;

        // Clamp zoom (e.g. max 100 years, min 1 minute)
        const MIN_RANGE = 60 * 1000; // 1 min
        const MAX_RANGE = 100 * 365 * 24 * 60 * 60 * 1000; // 100 years

        if (newRange < MIN_RANGE || newRange > MAX_RANGE) return;

        // Calculate new start/end based on ratio of mouse position
        const mouseRatio = mouseX / this.width;

        this.viewport.start = timeUnderMouse - (newRange * mouseRatio);
        this.viewport.end = timeUnderMouse + (newRange * (1 - mouseRatio));

        this.requestRender();
    }

    updateClusters() {
        this.clusters = [];
        if (this.events.length === 0) return;

        let currentCluster = {
            events: [this.events[0]],
            x: this.timeToX(this.events[0].timestamp)
        };

        for (let i = 1; i < this.events.length; i++) {
            const evt = this.events[i];
            const x = this.timeToX(evt.timestamp);

            // If inside viewport + padding (for off-screen sorting)
            // Just check pixel distance
            if (Math.abs(x - currentCluster.x) < this.options.minClusterDistance) {
                // Merge
                currentCluster.events.push(evt);
                // Update cluster visual center (average? or stay anchored left? Average is better)
                // Actually keep it simple: First item anchors. or center physics.
                // Let's re-average x to keep it centered
                // currentCluster.x = (currentCluster.x * (currentCluster.events.length-1) + x) / currentCluster.events.length;
            } else {
                // Finalize prev
                this.clusters.push(currentCluster);
                // Start new
                currentCluster = {
                    events: [evt],
                    x: x
                };
            }
        }
        this.clusters.push(currentCluster);
    }

    drawAxis() {
        this.ctx.clearRect(0, 0, this.width, this.height);

        const range = this.viewport.end - this.viewport.start;
        const rangeDays = range / (24 * 60 * 60 * 1000);

        // Determine Scale
        let tickInterval, dateFmt;

        // Heuristic thresholds
        if (rangeDays > 730) { tickInterval = 'year'; }
        else if (rangeDays > 120) { tickInterval = 'month'; }
        else if (rangeDays > 30) { tickInterval = 'week'; }
        else if (rangeDays > 2) { tickInterval = 'day'; }
        else if (rangeDays * 24 > 12) { tickInterval = 'hour'; }
        else { tickInterval = 'minute'; }

        // Generate Ticks
        this.ctx.strokeStyle = '#e2e8f0'; // slate-200
        this.ctx.fillStyle = '#64748b'; // slate-500
        this.ctx.font = '10px Inter, sans-serif';
        this.ctx.textAlign = 'center';
        this.ctx.lineWidth = 1;

        // Draw horizontal baseline
        const axisY = this.height - 30;
        this.ctx.beginPath();
        this.ctx.moveTo(0, axisY);
        this.ctx.lineTo(this.width, axisY);
        this.ctx.stroke();

        const ticks = this.generateTicks(this.viewport.start, this.viewport.end, tickInterval);

        ticks.forEach(t => {
            const x = this.timeToX(t.time);

            // Tick line
            this.ctx.beginPath();
            this.ctx.moveTo(x, axisY);
            this.ctx.lineTo(x, axisY + 6);
            this.ctx.stroke();

            // Label
            this.ctx.fillText(t.label, x, axisY + 18);

            // Vertical Grid (Optional, faint)
            this.ctx.save();
            this.ctx.strokeStyle = '#f8fafc'; // slate-50 very light
            this.ctx.setLineDash([5, 5]);
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, axisY);
            this.ctx.stroke();
            this.ctx.restore();
        });
    }

    generateTicks(start, end, interval) {
        const ticks = [];
        const date = new Date(start);

        // Align to boundary
        switch (interval) {
            case 'year': date.setMonth(0, 1); date.setHours(0, 0, 0, 0); break;
            case 'month': date.setDate(1); date.setHours(0, 0, 0, 0); break;
            case 'week': {
                const day = date.getDay();
                const diff = date.getDate() - day + (day == 0 ? -6 : 1); // Adjust to Monday
                date.setDate(diff); date.setHours(0, 0, 0, 0);
                break;
            }
            case 'day': date.setHours(0, 0, 0, 0); break;
            case 'hour': date.setMinutes(0, 0, 0); break;
            case 'minute': date.setSeconds(0, 0); break;
        }

        // Loop
        while (date.getTime() <= end) {
            const t = date.getTime();
            if (t >= start) {
                ticks.push({
                    time: t,
                    label: this.formatDate(date, interval)
                });
            }
            // Increment
            switch (interval) {
                case 'year': date.setFullYear(date.getFullYear() + 1); break;
                case 'month': date.setMonth(date.getMonth() + 1); break;
                case 'week': date.setDate(date.getDate() + 7); break;
                case 'day': date.setDate(date.getDate() + 1); break;
                case 'hour': date.setHours(date.getHours() + 1); break;
                case 'minute': date.setMinutes(date.getMinutes() + 1); break;
            }

            // Safety break
            if (ticks.length > 100) break; // Don't crash if interval logic fails
        }
        return ticks;
    }

    formatDate(date, interval) {
        const span = document.createElement('span'); // Dummy for translation if needed? No, just string
        const lang = 'es-ES'; // Spanish
        switch (interval) {
            case 'year': return date.getFullYear();
            case 'month': return date.toLocaleDateString(lang, { month: 'short', year: 'numeric' });
            case 'week': return `Sem ${this.getWeekNumber(date)}`;
            case 'day': return date.toLocaleDateString(lang, { weekday: 'short', day: 'numeric' });
            case 'hour': return date.toLocaleTimeString(lang, { hour: '2-digit', minute: '2-digit' });
            case 'minute': return date.toLocaleTimeString(lang, { hour: '2-digit', minute: '2-digit' });
        }
        return date.toString();
    }

    getWeekNumber(d) {
        d = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
        d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7));
        const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
        return Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
    }

    drawEvents() {
        this.updateClusters();

        // Diffing DOM or clearing? For < 500 items, clearing is fast enough and safer.
        this.eventLayer.innerHTML = '';

        const fragment = document.createDocumentFragment();

        const axisY = this.height - 30;
        const eventY = axisY - 20; // 20px above axis

        this.clusters.forEach(cluster => {
            const x = this.timeToX(cluster.events[0].timestamp); // Anchor to first or average?

            // Skip offscreen
            if (x < -50 || x > this.width + 50) return;

            const el = document.createElement('div');
            el.className = 'absolute transform -translate-x-1/2 -translate-y-1/2 transition-transform duration-200 hover:scale-110 cursor-pointer flex items-center justify-center shadow-sm';
            el.style.left = `${x}px`;
            el.style.top = `${eventY}px`;
            el.style.pointerEvents = 'auto'; // Re-enable clicks

            if (cluster.events.length > 1) {
                // Cluster Node
                el.className += ' bg-emerald-600 text-white rounded-full font-bold text-xs border-2 border-white';
                el.style.width = '28px';
                el.style.height = '28px';
                el.innerText = `${cluster.events.length}`;
                el.onclick = (e) => this.zoomToCluster(cluster, e);
                el.title = `${cluster.events.length} eventos`;
            } else {
                // Single Node
                const evt = cluster.events[0];
                el.className += ' bg-white border-2 border-emerald-500 rounded-full';
                el.style.width = '14px';
                el.style.height = '14px';
                el.onclick = (e) => this.emitSelect(evt, e);
                el.title = `${evt.title || 'Evento'} - ${new Date(evt.timestamp).toLocaleString()}`;

                // Optional: Icon inside?
            }

            fragment.appendChild(el);
        });

        this.eventLayer.appendChild(fragment);
    }

    zoomToCluster(cluster, e) {
        e.stopPropagation();

        // Find min/max time in cluster
        let min = Infinity, max = -Infinity;
        cluster.events.forEach(ev => {
            if (ev.timestamp < min) min = ev.timestamp;
            if (ev.timestamp > max) max = ev.timestamp;
        });

        // Add padding (20%)
        const range = max - min;
        const padding = Math.max(range * 0.2, 1000 * 60 * 60); // Min 1 hour padding

        this.animateViewport(min - padding, max + padding);
    }

    animateViewport(targetStart, targetEnd) {
        const startStart = this.viewport.start;
        const startEnd = this.viewport.end;
        const startTime = Date.now();
        const msg = "Animating...";
        const duration = 500; // ms

        const animate = () => {
            const now = Date.now();
            const p = Math.min((now - startTime) / duration, 1);
            const ease = 1 - Math.pow(1 - p, 3); // Cubic ease out

            this.viewport.start = startStart + (targetStart - startStart) * ease;
            this.viewport.end = startEnd + (targetEnd - startEnd) * ease;

            this.requestRender();

            if (p < 1) requestAnimationFrame(animate);
        };
        requestAnimationFrame(animate);
    }

    emitSelect(evt, nativeEvent) {
        nativeEvent.stopPropagation();
        // Custom event or callback
        if (this.options.onSelect) {
            this.options.onSelect(evt);
        }

        const domEvent = new CustomEvent('timeline-select', { detail: evt });
        this.container.dispatchEvent(domEvent);
    }

    requestRender() {
        if (!this.ticking) {
            requestAnimationFrame(() => {
                this.render();
                this.ticking = false;
            });
            this.ticking = true;
        }
    }

    fitToEvents() {
        if (this.events.length === 0) return;

        let min = Infinity;
        let max = -Infinity;

        this.events.forEach(e => {
            if (e.timestamp < min) min = e.timestamp;
            if (e.timestamp > max) max = e.timestamp;
        });

        // Add 10% padding on each side
        const range = max - min;
        const padding = Math.max(range * 0.1, 1000 * 60 * 60 * 24 * 7); // Min 1 week padding

        // If single event or very short range, center it
        if (range === 0) {
            const now = min;
            this.viewport = {
                start: now - (1000 * 60 * 60 * 24 * 30), // -30 days
                end: now + (1000 * 60 * 60 * 24 * 30)   // +30 days
            };
        } else {
            this.viewport = {
                start: min - padding,
                end: max + padding
            };
        }

        this.requestRender();
    }

    fitToEvents() {
        if (this.events.length === 0) return;

        let min = Infinity;
        let max = -Infinity;

        this.events.forEach(e => {
            if (e.timestamp < min) min = e.timestamp;
            if (e.timestamp > max) max = e.timestamp;
        });

        // Add 10% padding on each side
        const range = max - min;
        const padding = Math.max(range * 0.1, 1000 * 60 * 60 * 24 * 7); // Min 1 week padding

        // If single event or very short range, center it
        if (range === 0) {
            const now = min;
            this.viewport = {
                start: now - (1000 * 60 * 60 * 24 * 30), // -30 days
                end: now + (1000 * 60 * 60 * 24 * 30)   // +30 days
            };
        } else {
            this.viewport = {
                start: min - padding,
                end: max + padding
            };
        }

        this.requestRender();
    }

    render() {
        this.drawAxis();
        this.drawEvents();
    }
}

// Make global
window.Timeline = Timeline;
