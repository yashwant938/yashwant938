"""A self-contained SVG snake that follows the calendar's empty cells."""

from collections import deque
from datetime import timedelta
from math import hypot


def neighbors(point):
    x, y = point
    return ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1))


def empty_route(days, grid_start, week_count, updated):
    """Return a closed walk in the largest connected region of empty cells."""
    available = set()
    calendar_year = (grid_start + timedelta(days=6)).year
    for column in range(week_count):
        for row in range(7):
            day_date = grid_start + timedelta(days=column * 7 + row)
            if day_date.year != calendar_year:
                continue
            day = days.get(day_date)
            if day_date > updated or (day is not None and day['count'] == 0):
                available.add((column, row))
    remaining = set(available)
    components = []
    while remaining:
        seed = min(remaining)
        component = {seed}
        queue = deque([seed])
        remaining.remove(seed)
        while queue:
            for point in neighbors(queue.popleft()):
                if point in remaining:
                    remaining.remove(point)
                    component.add(point)
                    queue.append(point)
        components.append(component)
    if not components:
        return []
    available = max(components, key=len)
    if len(available) < 12:
        return []

    def nearest(target):
        return min(available, key=lambda p: (abs(p[0] - target[0]) + abs(p[1] - target[1]), p))

    def connect(start, end):
        queue = deque([start])
        parents = {start: None}
        while queue and end not in parents:
            here = queue.popleft()
            candidates = sorted(neighbors(here), key=lambda p: (abs(p[0] - end[0]) + abs(p[1] - end[1]), p))
            for point in candidates:
                if point in available and point not in parents:
                    parents[point] = here
                    queue.append(point)
        path = [end]
        while path[-1] != start:
            path.append(parents[path[-1]])
        return list(reversed(path))

    left, right = 2, week_count - 3
    targets = [(left, 1), (right, 1), (right, 5), (left, 5), (left, 3), (right - 3, 3), (right - 3, 0), (left + 5, 0)]
    waypoints = [nearest(target) for target in targets]
    walk = [waypoints[0]]
    for target in waypoints[1:] + waypoints[:1]:
        walk.extend(connect(walk[-1], target)[1:])
    assert walk[0] == walk[-1]
    assert all(point in available for point in walk)
    return walk


def rounded_path(walk, grid_x, grid_y, step, cell):
    """Round only inside traversed cells, preserving the obstacle-free route."""
    points = [(grid_x + x * step + cell / 2, grid_y + y * step + cell / 2) for x, y in walk[:-1]]
    if len(points) < 3:
        return ''

    def toward(point, other, distance=4):
        dx, dy = other[0] - point[0], other[1] - point[1]
        length = hypot(dx, dy)
        return point[0] + dx * distance / length, point[1] + dy * distance / length

    def pair(point):
        return f'{point[0]:g},{point[1]:g}'

    path = [f'M{pair(toward(points[0], points[-1]))}']
    for index, point in enumerate(points):
        previous, following = points[index - 1], points[(index + 1) % len(points)]
        entry, exit_point = toward(point, previous), toward(point, following)
        path.extend([f'L{pair(entry)}', f'Q{pair(point)} {pair(exit_point)}'])
    path.append('Z')
    return ' '.join(path)


def snake_markup(days, grid_start, week_count, updated, grid_x, grid_y, step, cell):
    walk = empty_route(days, grid_start, week_count, updated)
    if not walk:
        return [], []
    path = rounded_path(walk, grid_x, grid_y, step, cell)
    length = (len(walk) - 1) * step
    duration = max(16, length / 100)
    spacing_seconds = 3.2 / (length / duration)
    definitions = [
        '  <defs>',
        f'    <path id="snake-route" d="{path}"/>',
        '  </defs>',
        '  <style>@media (prefers-reduced-motion: reduce){.snake-motion,.snake-label{display:none}}</style>',
    ]
    output = [
        '    <g class="snake-label" aria-hidden="true">',
        '      <circle cx="838" cy="94" r="2.5" fill="#ff6b81"/>',
        '      <text x="850" y="98" fill="#b78a99" font-size="10" letter-spacing="1.3">SNAKE LOOP</text>',
        '    </g>',
        '    <g class="snake-motion" aria-label="A neon snake slithers through empty calendar cells">',
    ]

    def motion(delay):
        return f'<animateMotion dur="{duration:.3f}s" begin="-{delay:.4f}s" repeatCount="indefinite" rotate="auto"><mpath href="#snake-route"/></animateMotion>'

    # Draw from tail to head. Delayed samples follow the same route at a
    # constant speed, keeping the body together through every turn.
    for index in range(23, -1, -1):
        fraction = 1 - index / 23
        radius = 0.9 + 2.65 * fraction
        color = '#8b5cf6' if index > 16 else ('#d946ef' if index > 10 else ('#ff4164' if index > 4 else '#ff8da7'))
        output.extend([
            '      <g>',
            f'        <circle r="{radius + 2.3:.2f}" fill="{color}" opacity="0.11"/>',
            f'        <circle r="{radius:.2f}" fill="{color}"/>',
            f'        {motion(5 - index * spacing_seconds)}',
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
        f'        {motion(5)}',
        '      </g>',
        '    </g>',
    ])
    return definitions, output
