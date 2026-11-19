"""Unilateral affine pressure on rectangular supports and linearly elastic guide beams."""

from functools import lru_cache
from math import fsum


def clipped(rectangle, coefficients):
    a, b, c = coefficients
    polygon = []
    for (y, z), (yy, zz) in zip(rectangle, rectangle[1:] + rectangle[:1]):
        first, second = a + b * y + c * z, a + b * yy + c * zz
        if first >= 0:
            polygon.append((y, z))
        if (first < 0) != (second < 0):
            t = first / (first - second)
            polygon.append((y + t * (yy - y), z + t * (zz - z)))
    return polygon


def integrate(polygon):
    """Integrate [1,y,z] outer product exactly with degree-two triangle quadrature."""
    terms = [[] for _ in range(6)]
    for first, second in zip(polygon[1:], polygon[2:]):
        triangle = (polygon[0], first, second)
        (y0, z0), (y1, z1), (y2, z2) = triangle
        weight = abs((y1 - y0) * (z2 - z0) - (y2 - y0) * (z1 - z0)) / 6
        for y, z in triangle:
            yy, zz = (y0 + y1 + y2 + 3 * y) / 6, (z0 + z1 + z2 + 3 * z) / 6
            for bucket, value in zip(terms, (1, yy, zz, yy * yy, yy * zz, zz * zz)):
                bucket.append(weight * value)
    a, y, z, yy, yz, zz = map(fsum, terms)
    return ((a, y, z), (y, yy, yz), (z, yz, zz))


def solve(matrix, rhs):
    rows = [list(row) + [value] for row, value in zip(matrix, rhs)]
    for i in range(3):
        j = max(range(i, 3), key=lambda j: abs(rows[j][i]))
        rows[i], rows[j] = rows[j], rows[i]
        rows[i] = [x / rows[i][i] for x in rows[i]]
        for j in set(range(3)) - {i}:
            rows[j] = [a - rows[j][i] * b for a, b in zip(rows[j], rows[i])]
    return tuple(row[-1] for row in rows)


@lru_cache(maxsize=None)
def unit_contact(rectangles, ey, ez):
    # Normalize lengths for a well-scaled active-set solve with 1 N total load.
    scale = max(abs(x) for rect in rectangles for point in rect for x in point)
    polygons = [tuple((y / scale, z / scale) for y, z in rect) for rect in rectangles]
    target = (1.0, ey / scale, ez / scale)
    coefficients = (1.0, 0.0, 0.0)
    for _ in range(50):
        parts = [integrate(clipped(rect, coefficients)) for rect in polygons]
        stiffness = [[fsum(m[i][j] for m in parts) for j in range(3)] for i in range(3)]
        actual = [fsum(a * b for a, b in zip(row, coefficients)) for row in stiffness]
        if max(abs(a - b) for a, b in zip(actual, target)) < 1e-12:
            break
        coefficients = solve(stiffness, target)
    else:
        raise ValueError(f"Receiver contact failed to converge at offset {(ey, ez)}")
    a, b, c = coefficients
    return tuple({
        "contact_area_mm2": matrix[0][0] * scale**2,
        "peak_MPa_per_N": max(0, max(a + b * y + c * z for y, z in rect)) / scale**2,
        "force_per_N": fsum(x * y for x, y in zip(matrix[0], coefficients)),
        "first_moment_y_mm_per_N": scale * fsum(x * y for x, y in zip(matrix[1], coefficients)),
        "first_moment_z_mm_per_N": scale * fsum(x * y for x, y in zip(matrix[2], coefficients)),
    } for matrix, rect in zip(parts, polygons))


def contact(rectangles, ey, ez, force):
    return [{
        "area_mm2": part["contact_area_mm2"],
        "peak_MPa": force * part["peak_MPa_per_N"],
        "force_N": force * part["force_per_N"],
        "first_moment_y_Nmm": force * part["first_moment_y_mm_per_N"],
        "first_moment_z_Nmm": force * part["first_moment_z_mm_per_N"],
    } for part in unit_contact(rectangles, ey, ez)]


def rectangle(y0, y1, height):
    z = height / 2
    return ((y0, -z), (y1, -z), (y1, z), (y0, z))


def beam_end(load, a, length, fixed):
    """Two transmitted end loads and corresponding moment levers in the load direction."""
    b = length - a
    if fixed:
        return (load * b**2 * (3 * a + b) / length**3, load * a**2 * (3 * b + a) / length**3,
                load * a * b**2 / length**2, -load * a**2 * b / length**2)
    return load * b / length, load * a / length, 0.0, 0.0


def deflection(load, a, x, length, ei, fixed):
    rear, _, moment, _ = beam_end(load, a, length, fixed)
    linear = 0 if fixed else (load * (length - a)**3 - rear * length**3) / (6 * length)
    return (load * max(x - a, 0)**3 / 6 - rear * x**3 / 6 + moment * x**2 / 2 - linear * x) / ei
