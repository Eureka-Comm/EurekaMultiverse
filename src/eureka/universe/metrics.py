from typing import List

def compute_mse(actuals: List[float], predicteds: List[float]) -> float:
    """
    Mean Squared Error.
    MSE = (1/n) * sum((y_i - y_hat_i)^2)
    Must strictly be computed from historical ground truth and actual predictions.
    """
    if not actuals or not predicteds:
        raise ValueError("Cannot compute MSE: lists are empty.")
    if len(actuals) != len(predicteds):
        raise ValueError("Cannot compute MSE: lists have different lengths.")
    
    n = len(actuals)
    squared_errors = [(y - y_hat) ** 2 for y, y_hat in zip(actuals, predicteds)]
    return sum(squared_errors) / float(n)
