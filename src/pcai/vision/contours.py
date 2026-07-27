"""Contour extraction and geometry helpers for P.C.A.I. vision Cells."""

from __future__ import annotations

import math

import cv2
import numpy as np


def external_contours(mask: np.ndarray) -> tuple[np.ndarray, ...]:
    """Return external contours in deterministic top-to-bottom, left-to-right order."""
    contours, _hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    ordered = sorted(contours, key=lambda contour: (cv2.boundingRect(contour)[1], cv2.boundingRect(contour)[0]))
    return tuple(ordered)


def contour_circularity(contour: np.ndarray) -> float:
    """Return 4πA/P², or zero for a degenerate contour."""
    area = float(cv2.contourArea(contour))
    perimeter = float(cv2.arcLength(contour, True))
    if perimeter == 0.0:
        return 0.0
    return float((4.0 * math.pi * area) / (perimeter * perimeter))


def contour_solidity(contour: np.ndarray) -> float:
    """Return contour area divided by convex-hull area."""
    area = float(cv2.contourArea(contour))
    hull = cv2.convexHull(contour)
    hull_area = float(cv2.contourArea(hull))
    if hull_area == 0.0:
        return 0.0
    return area / hull_area


def contour_centroid(contour: np.ndarray) -> tuple[float, float]:
    """Return contour centroid, falling back to bounding-box centre when degenerate."""
    moments = cv2.moments(contour)
    if moments["m00"] != 0.0:
        return (float(moments["m10"] / moments["m00"]), float(moments["m01"] / moments["m00"]))
    x, y, width, height = cv2.boundingRect(contour)
    return (x + width / 2.0, y + height / 2.0)
