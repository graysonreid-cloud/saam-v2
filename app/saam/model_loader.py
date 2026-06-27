import joblib

# ---------------------------------------------------------
# SAAM v2 Model Loader
# ---------------------------------------------------------

# Load the trained Perceptron model from disk
# The pickle file should contain: {"model": <sklearn_model>}
MODEL = joblib.load("models/perceptron.pkl")["model"]
