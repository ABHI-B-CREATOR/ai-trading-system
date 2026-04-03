import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
import joblib
import os


class ModelTrainingPipeline:

    def __init__(self, config: dict):

        self.config = config
        self.model_save_path = config.get(
            "model_path",
            "4_AI_DECISION_LAYER/signal_probability_model.pkl"
        )

        self.last_training_time = None
        self.model = None

    # ---------- DATA PREP ----------
    def prepare_training_data(self, trade_dataset: pd.DataFrame):

        """
        Expected columns:
        features..., target_outcome
        """

        if trade_dataset.empty:
            return None, None

        X = trade_dataset.drop(columns=["target_outcome"])
        y = trade_dataset["target_outcome"]

        return X, y

    # ---------- TRAIN MODEL ----------
    def train_probability_model(self, trade_dataset: pd.DataFrame):

        X, y = self.prepare_training_data(trade_dataset)

        if X is None:
            return False

        self.model = RandomForestClassifier(
            n_estimators=self.config.get("rf_trees", 120),
            max_depth=self.config.get("rf_depth", 6),
            random_state=42
        )

        self.model.fit(X, y)

        return True

    # ---------- SAVE MODEL ----------
    def save_model(self):

        if self.model is None:
            return False

        os.makedirs(os.path.dirname(self.model_save_path), exist_ok=True)

        joblib.dump(self.model, self.model_save_path)

        self.last_training_time = datetime.now()

        return True

    # ---------- FULL PIPELINE ----------
    def run_training_cycle(self, trade_dataset: pd.DataFrame):

        trained = self.train_probability_model(trade_dataset)

        if not trained:
            return False

        saved = self.save_model()

        return saved

    # ---------- HEALTH ----------
    def training_status(self):

        return {
            "last_training_time": self.last_training_time,
            "model_ready": self.model is not None
        }