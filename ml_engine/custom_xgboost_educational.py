import numpy as np
import pandas as pd

class DecisionNode:
    def __init__(self, X_matrix, gradients, hessians, row_indices, col_sample_rate=0.8, 
                 min_samples=5, min_hessian_sum=1, max_depth=5, reg_lambda=1, 
                 split_gamma=1):
        self.X_matrix = X_matrix
        self.gradients = gradients
        self.hessians = hessians
        self.row_indices = row_indices 
        self.max_depth = max_depth
        self.min_samples = min_samples
        self.reg_lambda = reg_lambda
        self.split_gamma = split_gamma
        self.min_hessian_sum = min_hessian_sum
        
        self.n_rows = len(row_indices)
        self.n_cols = X_matrix.shape[1]
        self.col_sample_rate = col_sample_rate
        
        self.active_features = np.random.permutation(self.n_cols)[:max(1, round(self.col_sample_rate * self.n_cols))]
        
        self.leaf_weight = self._compute_weight(self.gradients[self.row_indices], self.hessians[self.row_indices])
        
        self.max_gain = float('-inf')
        self.best_feature_idx = None
        self.split_threshold = None
        
        if self.max_depth > 0 and self.n_rows >= 2 * self.min_samples:
            self._evaluate_splits_vectorized()
            
        if not self.is_terminal:
            self._create_children()

    def _compute_weight(self, grad_array, hess_array):
        return (-np.sum(grad_array) / (np.sum(hess_array) + self.reg_lambda))

    def _evaluate_splits_vectorized(self):
        for feature_idx in self.active_features:
            f_vals = self.X_matrix[self.row_indices, feature_idx]
            g = self.gradients[self.row_indices]
            h = self.hessians[self.row_indices]

            sort_idx = np.argsort(f_vals)
            f_sorted = f_vals[sort_idx]
            g_sorted = g[sort_idx]
            h_sorted = h[sort_idx]

            G_l = np.cumsum(g_sorted)
            H_l = np.cumsum(h_sorted)
            G_total, H_total = G_l[-1], H_l[-1]
            G_r, H_r = G_total - G_l, H_total - H_l

            gain = 0.5 * (
                (G_l**2 / (H_l + self.reg_lambda)) + 
                (G_r**2 / (H_r + self.reg_lambda)) - 
                (G_total**2 / (H_total + self.reg_lambda))
            ) - self.split_gamma

            mask = (np.arange(self.n_rows) >= self.min_samples) & \
                   (np.arange(self.n_rows) <= (self.n_rows - self.min_samples)) & \
                   (H_l >= self.min_hessian_sum) & (H_r >= self.min_hessian_sum)

            if np.any(mask):
                best_idx_in_mask = np.argmax(gain[mask])
                actual_idx = np.where(mask)[0][best_idx_in_mask]
                
                if gain[actual_idx] > self.max_gain:
                    self.max_gain = gain[actual_idx]
                    self.best_feature_idx = feature_idx
                    self.split_threshold = f_sorted[actual_idx]

    def _create_children(self):
        split_col = self.X_matrix[self.row_indices, self.best_feature_idx]
        left_idx = np.where(split_col <= self.split_threshold)[0]
        right_idx = np.where(split_col > self.split_threshold)[0]
        
        self.left_child = DecisionNode(self.X_matrix, self.gradients, self.hessians, self.row_indices[left_idx], 
                                       self.col_sample_rate, self.min_samples, self.min_hessian_sum, 
                                       self.max_depth - 1, self.reg_lambda, self.split_gamma)
        self.right_child = DecisionNode(self.X_matrix, self.gradients, self.hessians, self.row_indices[right_idx], 
                                        self.col_sample_rate, self.min_samples, self.min_hessian_sum, 
                                        self.max_depth - 1, self.reg_lambda, self.split_gamma)

    @property
    def is_terminal(self):
        return self.best_feature_idx is None or self.max_depth <= 0

    def predict_vectorized(self, X):
        preds = np.zeros(X.shape[0])
        self._predict_recursive(X, np.arange(X.shape[0]), preds)
        return preds

    def _predict_recursive(self, X, indices, preds):
        if self.is_terminal:
            preds[indices] = self.leaf_weight
            return
        
        feat_vals = X[indices, self.best_feature_idx]
        left_mask = feat_vals <= self.split_threshold
        
        if np.any(left_mask):
            self.left_child._predict_recursive(X, indices[left_mask], preds)
        if np.any(~left_mask):
            self.right_child._predict_recursive(X, indices[~left_mask], preds)

class CustomXGBRegressor:
    def __init__(self):
        self.tree_ensemble = []
        self.base_pred = None

    def fit(self, X_train, y_train, n_trees=10, max_depth=3, eta=0.3, reg_lambda=1.0, 
            split_gamma=0.1, min_samples=5, col_sample_rate=0.8):
        
        X_train = np.array(X_train)
        y_train = np.array(y_train)
        self.base_pred = np.mean(y_train)
        current_preds = np.full(y_train.shape, self.base_pred)

        for i in range(n_trees):
            grads = 2 * (current_preds - y_train)
            hesss = np.full(y_train.shape, 2.0)
            
            tree = DecisionNode(X_train, grads, hesss, np.arange(len(X_train)), 
                                col_sample_rate, min_samples, 1, max_depth, 
                                reg_lambda, split_gamma)
            
            tree_preds = tree.predict_vectorized(X_train)
            current_preds += eta * tree_preds
            self.tree_ensemble.append((tree, eta))

    def predict(self, X):
        X = np.array(X)
        preds = np.full(X.shape[0], self.base_pred)
        for tree, eta in self.tree_ensemble:
            preds += eta * tree.predict_vectorized(X)
        return preds
    
class CustomXGBClassifier:
    def __init__(self):
        self.tree_ensemble = []
        self.base_score = 0.0

    @staticmethod
    def _apply_sigmoid(x):
        return 1 / (1 + np.exp(-x))

    def fit(self, X_train, y_train, n_trees=10, max_depth=3, eta=0.3, reg_lambda=1.0, 
            split_gamma=0.1, min_samples=5, col_sample_rate=0.8):
        
        X_train = np.array(X_train)
        y_train = np.array(y_train)
        current_preds = np.full(y_train.shape, self.base_score)

        for _ in range(n_trees):
            probs = self._apply_sigmoid(current_preds)
            grads = probs - y_train
            hesss = probs * (1 - probs)
            
            tree = DecisionNode(X_train, grads, hesss, np.arange(len(X_train)), 
                                col_sample_rate, min_samples, 1, max_depth, 
                                reg_lambda, split_gamma)
            
            current_preds += eta * tree.predict_vectorized(X_train)
            self.tree_ensemble.append((tree, eta))

    def predict_proba(self, X):
        X = np.array(X)
        raw_output = np.full(X.shape[0], self.base_score)
        for tree, eta in self.tree_ensemble:
            raw_output += eta * tree.predict_vectorized(X)
        return self._apply_sigmoid(raw_output)

    def predict(self, X):
        return (self.predict_proba(X) > 0.5).astype(int)