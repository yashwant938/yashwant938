"""A neon snake eats calendar tiles as a decorative, self-resetting SVG loop."""

from collections import deque
from math import hypot

SPEED = 140.0
LEAD_IN = 0.65
SEGMENT_SPACING = 2.6


def neighbors(point):
    x, y = point
    return ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1))


def shortest_path(start, goals, allowed, blocked):
    queue = deque([start])
    parents = {start: None}
    while queue:
        point = queue.popleft()
        if point in goals:
            path = [point]
            while parents[path[-1]] is not None:
                path.append(parents[path[-1]])
            return list(reversed(path))
        for adjacent in neighbors(point):
            if adjacent in allowed and adjacent not in blocked and adjacent not in parents:
                parents[adjacent] = point
                queue.append(adjacent)
    return None


def plan_hunt(days, grid_start, week_count, updated):
    """Hunt nearest remaining tiles while keeping a route to the tail open."""
    foods = {}
    for day_date, day in days.items():
        column, row = divmod((day_date - grid_start).days, 7)
        if day_date <= updated and day['count'] > 0 and 0 <= column < week_count:
            foods[(column, row)] = day_date
    original = dict(foods)
    allowed = {(x, y) for x in range(week_count) for y in range(7)}
    body = [(-1 - index, 0) for index in range(5)]
    walk, bites = [body[0]], []
    last_bite = 0
    for _ in range(week_count * 7 * 3):
        if not foods:
            if bites:
                return walk, bites
            break
        preferred = shortest_path(body[0], foods, allowed, set(body[1:-1]))
        candidates = ([preferred[1]] if preferred and len(preferred) > 1 else []) + list(neighbors(body[0]))
        selected = None
        for point in dict.fromkeys(candidates):
            if point not in allowed or point in body[:-1]:
                continue
            grows = point in foods and (len(bites) + 1) % 8 == 0 and len(body) < 8
            trial = [point] + body
            if not grows:
                trial.pop()
            if all(segment in allowed for segment in trial) and len(foods) > int(point in foods):
                if not shortest_path(trial[0], {trial[-1]}, allowed, set(trial[1:-1])):
                    continue
            selected, body = point, trial
            break
        if selected is None or len(walk) - last_bite > week_count * 7:
            break
        walk.append(selected)
        if selected in foods:
            bites.append((len(walk) - 1, selected, foods.pop(selected)))
            last_bite = len(walk) - 1

    # A non-intersecting sweep handles dense/awkward calendars and empty patrols.
    walk, bites = [(-1, 0)], []
    for row in range(7):
        columns = range(week_count) if row % 2 == 0 else range(week_count - 1, -1, -1)
        for column in columns:
            point = (column, row)
            walk.append(point)
            if point in original:
                bites.append((len(walk) - 1, point, original[point]))
    return walk, bites


def rounded_path(walk, grid_x, grid_y, step, cell):
    """Return a smooth open path and each visit's arc-length position."""
    points = [(grid_x + x * step + cell / 2, grid_y + y * step + cell / 2) for x, y in walk]

    def pair(point):
        return f'{point[0]:g},{point[1]:g}'

    def toward(point, other):
        dx, dy = other[0] - point[0], other[1] - point[1]
        length = hypot(dx, dy)
        return point[0] + dx * 4 / length, point[1] + dy * 4 / length

    path, visits, total = [f'M{pair(points[0])}'], [0.0], 0.0
    cursor = points[0]
    for index in range(1, len(points) - 1):
        point = points[index]
        entry, exit_point = toward(point, points[index - 1]), toward(point, points[index + 1])
        total += hypot(entry[0] - cursor[0], entry[1] - cursor[1])
        path.extend([f'L{pair(entry)}', f'Q{pair(point)} {pair(exit_point)}'])
        # Sample the tiny bend to synchronize bites with paced SVG motion.
        previous, arc, halfway = entry, 0.0, 0.0
        for sample in range(1, 33):
            t = sample / 32
            current = tuple((1 - t) ** 2 * entry[axis] + 2 * (1 - t) * t * point[axis] + t ** 2 * exit_point[axis] for axis in (0, 1))
            arc += hypot(current[0] - previous[0], current[1] - previous[1])
            if sample == 16:
                halfway = arc
            previous = current
        visits.append(total + halfway)
        total += arc
        cursor = exit_point
    if len(points) > 1:
        total += hypot(points[-1][0] - cursor[0], points[-1][1] - cursor[1])
        path.append(f'L{pair(points[-1])}')
        visits.append(total)
    return ' '.join(path), total, visits


def animate(attribute, frames, period, discrete=False):
    values = ';'.join(f'{value:g}' for _, value in frames)
    times = ';'.join(f'{time / period:.9f}' for time, _ in frames)
    mode = 'discrete' if discrete else 'linear'
    return f'<animate attributeName="{attribute}" values="{values}" keyTimes="{times}" calcMode="{mode}" dur="{period:.6f}s" repeatCount="indefinite"/>'


def snake_markup(days, grid_start, week_count, updated, grid_x, grid_y, step, cell):
    walk, bites = plan_hunt(days, grid_start, week_count, updated)
    if len(walk) < 2:
        return [], []
    path, length, visits = rounded_path(walk, grid_x, grid_y, step, cell)
    move_end = LEAD_IN + length / SPEED
    reset = move_end + 0.55
    period = move_end + 1.65
    meal_times = [LEAD_IN + visits[index] / SPEED for index, _, _ in bites]
    definitions = [
        '  <defs>',
        f'    <path id="snake-route" d="{path}"/>',
        f'    <clipPath id="snake-grid"><rect x="{grid_x - 6}" y="{grid_y - 6}" width="{week_count * step + 8}" height="{7 * step + 8}"/></clipPath>',
        '  </defs>',
        '  <style>@media (prefers-reduced-motion: reduce){.snake-motion,.snake-label,.snake-effects{display:none}}</style>',
    ]
    output = ['    <g class="snake-effects" aria-hidden="true" pointer-events="none" clip-path="url(#snake-grid)">']
    for (_, (column, row), day_date), when in zip(bites, meal_times):
        x, y = grid_x + column * step, grid_y + row * step
        output.extend([
            f'      <rect data-food-date="{day_date.isoformat()}" data-eaten-at="{when:.6f}" x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.5" fill="#161b22" opacity="0">',
            '        ' + animate('opacity', [(0, 0), (when, 0), (when + 0.12, 1), (reset, 1), (period, 0)], period),
            '      </rect>',
            f'      <circle cx="{x + cell / 2}" cy="{y + cell / 2}" r="3" fill="none" stroke="#ff8da7" stroke-width="1.2" opacity="0">',
            '        ' + animate('opacity', [(0, 0), (when, 0), (when + 0.05, 0.55), (when + 0.42, 0), (period, 0)], period),
            '        ' + animate('r', [(0, 3), (when, 3), (when + 0.42, 11), (period, 11)], period),
            '      </circle>',
        ])
    output.append('    </g>')
    label = 'NEON FEAST' if bites else 'SNAKE PATROL'
    output.extend([
        '    <g class="snake-label" aria-hidden="true">',
        '      <circle cx="836" cy="82" r="2.5" fill="#ff6b81"/>',
        f'      <text x="928" y="86" text-anchor="end" fill="#b78a99" font-size="10" letter-spacing="1.2">{label}</text>',
    ])
    for eaten in range(len(bites) + 1):
        start = meal_times[eaten - 1] if eaten else 0
        end = meal_times[eaten] if eaten < len(bites) else period
        frames = [(0, int(eaten == 0))]
        if start > 0:
            frames.append((start, 1))
        if end < period:
            frames.append((end, 0))
        frames.append((period, 0))
        output.extend([
            f'      <text data-eaten-value="{eaten}" x="928" y="104" text-anchor="end" font-size="11" fill="#ff9bae" opacity="{int(eaten == 0)}">{eaten:02d} / {len(bites):02d} tiles',
            '        ' + animate('opacity', frames, period, discrete=True),
            '      </text>',
        ])
    output.extend([
        '    </g>',
        '    <g class="snake-motion" aria-label="A neon snake eats red tiles; the grid refills each round" clip-path="url(#snake-grid)">',
        '      ' + animate('opacity', [(0, 0), (0.3, 1), (move_end + 0.02, 1), (move_end + 0.28, 0), (period, 0)], period),
    ])

    def motion(delay):
        times = f'0;{(LEAD_IN + delay) / period:.9f};{(move_end + delay) / period:.9f};1'
        return f'<animateMotion dur="{period:.6f}s" begin="0s" keyTimes="{times}" keyPoints="0;0;1;1" calcMode="linear" repeatCount="indefinite" rotate="auto"><mpath href="#snake-route"/></animateMotion>'

    segment_count = 24 + 4 * min(3, len(bites) // 8)
    for index in range(segment_count - 1, -1, -1):
        radius = 0.9 + 2.65 * (1 - index / (segment_count - 1))
        color = '#8b5cf6' if index > 16 else ('#d946ef' if index > 10 else ('#ff4164' if index > 4 else '#ff8da7'))
        output.append(f'      <g data-snake-segment="{index}" opacity="{int(index < 24)}">')
        if index >= 24:
            when = meal_times[7 + 8 * ((index - 24) // 4)]
            output.append('        ' + animate('opacity', [(0, 0), (when, 0), (when + 0.18, 1), (move_end + 0.3, 1), (period, 0)], period))
        output.extend([
            f'        <circle r="{radius + 2.3:.2f}" fill="{color}" opacity="0.11"/>',
            f'        <circle r="{radius:.2f}" fill="{color}"/>',
            '        ' + motion(index * SEGMENT_SPACING / SPEED),
            '      </g>',
        ])
    output.extend([
        '      <g id="snake-head">',
        '        <ellipse rx="9" ry="7" fill="#ff4164" opacity="0.12"/>',
        '        <path d="M-4.5,-4 Q2,-5 6,-2 Q8,0 6,2 Q2,5 -4.5,4Z" fill="#fff1f2" stroke="#ff8da7" stroke-width="0.7"/>',
        '        <circle cx="2.5" cy="-2.15" r="1.25" fill="#101827"/>',
        '        <circle cx="2.5" cy="2.15" r="1.25" fill="#101827"/>',
        '        <circle cx="2.85" cy="-2.35" r="0.5" fill="#7df9ff"/>',
        '        <circle cx="2.85" cy="1.95" r="0.5" fill="#7df9ff"/>',
        '        <path d="M7,0 H10 M10,0 L12,-1.5 M10,0 L12,1.5" fill="none" stroke="#ff6b81" stroke-width="0.8" stroke-linecap="round"/>',
        '        ' + motion(0),
        '      </g>',
        '    </g>',
    ])
    return definitions, output
