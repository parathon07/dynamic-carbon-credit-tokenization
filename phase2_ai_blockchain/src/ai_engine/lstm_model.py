"""
Deep Learning Emission Prediction — Step 2.2a
===============================================
Replaces Random Forest with LSTM (PyTorch) for 
time-series sequence modeling of dynamic emissions.
"""

import numpy as np
import torch
import torch.nn as nn
import logging
from typing import Dict, Any, List

logger = logging.getLogger("ai_engine.lstm_model")

class LSTMEmissionNet(nn.Module):
    """Underlying PyTorch LSTM neural network."""
    def __init__(self, input_dim=7, hidden_dim=64, num_layers=2, output_dim=1):
        super(LSTMEmissionNet, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True, dropout=0.2)
        self.fc = nn.Linear(hidden_dim, output_dim)
        
    def forward(self, x):
        # x shape (batch, seq_len, features)
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        
        out, _ = self.lstm(x, (h0, c0))
        # Decode the hidden state of the last time step
        out = self.fc(out[:, -1, :])
        return out


class EmissionLSTM:
    """Wrapper class for managing training and inference."""
    def __init__(self, sequence_length=10):
        self.seq_len = sequence_length
        self.model = LSTMEmissionNet()
        self.criterion = nn.MSELoss()
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        self.is_trained = False
        
    def train(self, X_train: np.ndarray, y_train: np.ndarray, epochs=50):
        """
        Train the LSTM on 3D sequence data: (samples, seq_len, features)
        """
        self.model.train()
        
        # Convert to torch tensors
        X_t = torch.tensor(X_train, dtype=torch.float32)
        y_t = torch.tensor(y_train, dtype=torch.float32).view(-1, 1)
        
        for epoch in range(epochs):
            self.optimizer.zero_grad()
            outputs = self.model(X_t)
            loss = self.criterion(outputs, y_t)
            loss.backward()
            self.optimizer.step()
            
        self.is_trained = True
        logger.info(f"LSTM training completed. Final Loss: {loss.item():.4f}")
        return loss.item()

    def predict(self, X_sequence: np.ndarray) -> float:
        """Predict exactly one output given a sequence of recent readings."""
        if not self.is_trained:
            logger.warning("LSTM predict called without training, using initialized weights!")
            
        self.model.eval()
        with torch.no_grad():
            x_t = torch.tensor(X_sequence, dtype=torch.float32).unsqueeze(0) # (1, seq_len, features)
            pred = self.model(x_t).item()
            
        return max(0.0, pred)  # Prevent negative emissions
