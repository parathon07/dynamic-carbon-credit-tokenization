"""
AI Fraud Detection Ensemble — Step 2.3
=========================================
Implements an Ensemble Voting mechanism for anomaly/fraud detection 
using LSTM Autoencoder (Deep), Isolation Forest (Unsupervised tree),
and Random Forest (Supervised proxy).
"""

import numpy as np
import logging
from sklearn.ensemble import IsolationForest, RandomForestClassifier
import torch
import torch.nn as nn
from typing import List, Dict, Any

logger = logging.getLogger("ai_engine.anomaly_ensemble")

class LSTMAutoencoder(nn.Module):
    """LSTM-based Autoencoder for detecting temporal anomalies in sensor streams."""
    def __init__(self, input_dim=7, hidden_dim=32, num_layers=1):
        super(LSTMAutoencoder, self).__init__()
        # Encoder
        self.encoder = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)
        # Decoder
        self.decoder = nn.LSTM(hidden_dim, input_dim, num_layers, batch_first=True)
        
    def forward(self, x):
        # x is (batch, seq_len, features)
        encoded, _ = self.encoder(x)
        decoded, _ = self.decoder(encoded)
        return decoded
        
    def train_ae(self, X_train: np.ndarray, epochs=30):
        optimizer = torch.optim.Adam(self.parameters(), lr=0.005)
        criterion = nn.MSELoss()
        self.train()
        X_t = torch.tensor(X_train, dtype=torch.float32)
        
        loss = None
        for epoch in range(epochs):
            optimizer.zero_grad()
            reconstructed = self(X_t)
            loss = criterion(reconstructed, X_t)
            loss.backward()
            optimizer.step()
            
        logger.info(f"LSTM-AE Training Complete. Final Recon Loss: {loss.item():.4f}")
        return loss.item()
        
    def reconstruct_error(self, X_seq: np.ndarray) -> float:
        """Returns the MSE reconstruction error. High error = anomaly."""
        self.eval()
        with torch.no_grad():
            x_t = torch.tensor(X_seq, dtype=torch.float32)
            if x_t.dim() == 2:
                x_t = x_t.unsqueeze(0)
            reconstructed = self(x_t)
            error = nn.functional.mse_loss(reconstructed, x_t)
        return error.item()


class FraudDetectionEnsemble:
    """Ensemble Voter: LSTM-AE + Isolation Forest + Random Forest"""
    def __init__(self, ae_threshold=0.05):
        self.lstm_ae = LSTMAutoencoder()
        self.iforest = IsolationForest(n_estimators=100, contamination=0.01, random_state=42)
        # RF Acts as a rule-based expert system proxy using known fraud labels
        self.rf = RandomForestClassifier(n_estimators=50, random_state=42)
        self.ae_threshold = ae_threshold
        self.is_trained = False
        
    def train(self, X_seq_normal: np.ndarray, X_tabular_all: np.ndarray, y_fraud_labels: np.ndarray):
        """Train all three models appropriately."""
        # 1. Train Autoencoder only on normal temporal sequences
        self.lstm_ae.train_ae(X_seq_normal)
        
        # 2. Train Isolation Forest unconditionally on all tabular data
        self.iforest.fit(X_tabular_all)
        
        # 3. Train RF on labeled data
        self.rf.fit(X_tabular_all, y_fraud_labels)
        self.is_trained = True
        logger.info("Ensemble successfully fit to data.")
        
    def predict(self, X_seq: np.ndarray, X_tabular_single: np.ndarray) -> Dict[str, Any]:
        """
        Ensemble Voting Logic.
        Returns aggregate anomaly score and boolean flag.
        """
        if not self.is_trained:
            logger.warning("Predicting with untrained Ensemble!")

        # 1. LSTM Autoencoder Error
        recon_error = self.lstm_ae.reconstruct_error(X_seq)
        vote_ae = 1 if recon_error > self.ae_threshold else 0
        
        # 2. Isolation Forest (returns -1 for anomaly, 1 for normal. So flip)
        # Reshape tabular
        x_tab = X_tabular_single.reshape(1, -1)
        if_out = self.iforest.predict(x_tab)[0]
        vote_if = 1 if if_out == -1 else 0
        
        # 3. Random Forest (returns 1 for fraud)
        cf_out = self.rf.predict(x_tab)[0]
        vote_rf = int(cf_out)
        
        # Hard Voting
        total_votes = vote_ae + vote_if + vote_rf
        is_fraud = total_votes >= 2  # Majority rules
        
        return {
            "is_fraud": is_fraud,
            "confidence": total_votes / 3.0,
            "votes": {
                "lstm_ae": vote_ae,
                "isolation_forest": vote_if,
                "random_forest": vote_rf
            },
            "ae_mse_error": round(recon_error, 5)
        }
