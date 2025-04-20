def confidence_to_distance(confidence: float) -> float:
    return confidence * 2 - 1

def distance_to_confidence(distance: float) -> float:
    return (distance + 1) / 2
