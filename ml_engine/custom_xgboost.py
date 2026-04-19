import numpy as np
import pandas as pd

class DecisionNode:
    def __init__(self, X_matrix, gradients, hessians, row_indices, col_sample_rate=0.8, min_samples=5, min_hessian_sum=1, max_depth=10, reg_lambda=1, split_gamma=1, bin_eps=0.1):
        self.X_matrix, self.gradients, self.hessians = X_matrix, gradients, hessians
        self.row_indices = row_indices 
        self.max_depth = max_depth
        self.min_samples = min_samples
        self.reg_lambda = reg_lambda
        self.split_gamma  = split_gamma
        self.min_hessian_sum = min_hessian_sum
        self.n_rows = len(row_indices)
        self.n_cols = X_matrix.shape[1]
        self.col_sample_rate = col_sample_rate
        self.bin_eps = bin_eps
        self.active_features = np.random.permutation(self.n_cols)[:round(self.col_sample_rate * self.n_cols)]
        self.leaf_weight = self._compute_weight(self.gradients[self.row_indices], self.hessians[self.row_indices])
        self.max_gain = float('-inf')
        self._evaluate_splits()
        
    def _compute_weight(self, grad_array, hess_array):
        return (-np.sum(grad_array) / (np.sum(hess_array) + self.reg_lambda))
        
    def _evaluate_splits(self):
        for feature_idx in self.active_features: 
            self._search_exact_split(feature_idx)
        if self.is_terminal: 
            return
        split_column = self.split_array
        left_mask = np.nonzero(split_column <= self.split_threshold)[0]
        right_mask = np.nonzero(split_column > self.split_threshold)[0]
        self.left_child = DecisionNode(X_matrix=self.X_matrix, gradients=self.gradients, hessians=self.hessians, row_indices=self.row_indices[left_mask], min_samples=self.min_samples, max_depth=self.max_depth-1, reg_lambda=self.reg_lambda, split_gamma=self.split_gamma, min_hessian_sum=self.min_hessian_sum, bin_eps=self.bin_eps, col_sample_rate=self.col_sample_rate)
        self.right_child = DecisionNode(X_matrix=self.X_matrix, gradients=self.gradients, hessians=self.hessians, row_indices=self.row_indices[right_mask], min_samples=self.min_samples, max_depth=self.max_depth-1, reg_lambda=self.reg_lambda, split_gamma=self.split_gamma, min_hessian_sum=self.min_hessian_sum, bin_eps=self.bin_eps, col_sample_rate=self.col_sample_rate)
        
    def _search_exact_split(self, feature_idx):
        feature_vals = self.X_matrix[self.row_indices, feature_idx]
        for row in range(self.n_rows):
            left_bool = feature_vals <= feature_vals[row]
            right_bool = feature_vals > feature_vals[row]
            left_idx = np.nonzero(feature_vals <= feature_vals[row])[0]
            right_idx = np.nonzero(feature_vals > feature_vals[row])[0]
            
            if (right_bool.sum() < self.min_samples or left_bool.sum() < self.min_samples 
                or self.hessians[left_idx].sum() < self.min_hessian_sum
                or self.hessians[right_idx].sum() < self.min_hessian_sum): 
                continue

            current_gain = self._calculate_gain(left_bool, right_bool)
            if current_gain > self.max_gain: 
                self.best_feature_idx = feature_idx
                self.max_gain = current_gain
                self.split_threshold = feature_vals[row]
                
    def _search_approx_split(self, feature_idx):
        feature_vals = self.X_matrix[self.row_indices, feature_idx]
        local_hessians = self.hessians[self.row_indices]
        stats_df = pd.DataFrame({'val': feature_vals, 'h': local_hessians})
        stats_df.sort_values(by=['val'], ascending=True, inplace=True)
        total_h = stats_df['h'].sum() 
        stats_df['rank_score'] = stats_df.apply(lambda row_val: (1/total_h) * sum(stats_df[stats_df['val'] < row_val['val']]['h']), axis=1)
        
        for i in range(stats_df.shape[0]-1):
            rank_j, rank_j_next = stats_df['rank_score'].iloc[i:i+2]
            if abs(rank_j - rank_j_next) >= self.bin_eps:
                continue
                
            candidate_threshold = (stats_df['rank_score'].iloc[i+1] + stats_df['rank_score'].iloc[i]) / 2
            left_bool = feature_vals <= candidate_threshold
            right_bool = feature_vals > candidate_threshold
            
            left_idx = np.nonzero(feature_vals <= candidate_threshold)[0]
            right_idx = np.nonzero(feature_vals > candidate_threshold)[0]
            
            if (right_bool.sum() < self.min_samples or left_bool.sum() < self.min_samples 
                or self.hessians[left_idx].sum() < self.min_hessian_sum
                or self.hessians[right_idx].sum() < self.min_hessian_sum): 
                continue
                
            current_gain = self._calculate_gain(left_bool, right_bool)
            if current_gain > self.max_gain: 
                self.best_feature_idx = feature_idx
                self.max_gain = current_gain
                self.split_threshold = candidate_threshold
                
    def _calculate_gain(self, left_mask, right_mask):
        local_grad = self.gradients[self.row_indices]
        local_hess = self.hessians[self.row_indices]
        
        sum_grad_l = local_grad[left_mask].sum()
        sum_hess_l = local_hess[left_mask].sum()
        sum_grad_r = local_grad[right_mask].sum()
        sum_hess_r = local_hess[right_mask].sum()
        
        term_left = (sum_grad_l ** 2) / (sum_hess_l + self.reg_lambda)
        term_right = (sum_grad_r ** 2) / (sum_hess_r + self.reg_lambda)
        term_root = ((sum_grad_l + sum_grad_r) ** 2) / (sum_hess_l + sum_hess_r + self.reg_lambda)
        
        return 0.5 * (term_left + term_right - term_root) - self.split_gamma
                
    @property
    def split_array(self):
        return self.X_matrix[self.row_indices, self.best_feature_idx]
                
    @property
    def is_terminal(self):
        return self.max_gain == float('-inf') or self.max_depth <= 0                 

    def predict_matrix(self, X_eval):
        return np.array([self._predict_single(vector) for vector in X_eval])
    
    def _predict_single(self, vector):
        if self.is_terminal:
            return self.leaf_weight
        next_node = self.left_child if vector[self.best_feature_idx] <= self.split_threshold else self.right_child
        return next_node._predict_single(vector)

class GradientTree:
    def fit(self, X_train, grads, hesss, col_sample_rate=0.8, min_samples=5, min_hessian_sum=1, max_depth=10, reg_lambda=1, split_gamma=1, bin_eps=0.1):
        self.root_node = DecisionNode(X_train, grads, hesss, np.array(np.arange(len(X_train))), col_sample_rate, min_samples, min_hessian_sum, max_depth, reg_lambda, split_gamma, bin_eps)
        return self
    
    def predict(self, X_eval):
        return self.root_node.predict_matrix(X_eval)
   
class CustomXGBClassifier:
    def __init__(self):
        self.tree_ensemble = []
    
    @staticmethod
    def _apply_sigmoid(matrix):
        return 1 / (1 + np.exp(-matrix))
    
    def _compute_gradients(self, raw_preds, targets):
        probs = self._apply_sigmoid(raw_preds)
        return (probs - targets)
    
    def _compute_hessians(self, raw_preds, targets):
        probs = self._apply_sigmoid(raw_preds)
        return (probs * (1 - probs))
    
    @staticmethod
    def compute_log_odds(target_vector):
        count_pos = np.count_nonzero(target_vector == 1)
        count_neg = np.count_nonzero(target_vector == 0)
        return np.log(count_pos / count_neg)
    
    def fit(self, X_train, y_train, col_sample_rate=0.8, min_hessian_sum=1, max_depth=5, min_samples=5, eta=0.4, n_trees=5, reg_lambda=1.5, split_gamma=1, bin_eps=0.1):
        self.X_train, self.y_train = X_train, y_train
        self.max_depth = max_depth
        self.col_sample_rate = col_sample_rate
        self.bin_eps = bin_eps
        self.min_hessian_sum = min_hessian_sum 
        self.min_samples = min_samples
        self.eta = eta
        self.n_trees = n_trees 
        self.reg_lambda = reg_lambda
        self.split_gamma = split_gamma
    
        self.current_preds = np.full((X_train.shape[0], 1), 1).flatten().astype('float64')
    
        for _ in range(self.n_trees):
            g_vector = self._compute_gradients(self.current_preds, self.y_train)
            h_vector = self._compute_hessians(self.current_preds, self.y_train)
            new_tree = GradientTree().fit(self.X_train, g_vector, h_vector, max_depth=self.max_depth, min_samples=self.min_samples, reg_lambda=self.reg_lambda, split_gamma=self.split_gamma, bin_eps=self.bin_eps, min_hessian_sum=self.min_hessian_sum, col_sample_rate=self.col_sample_rate)
            self.current_preds += self.eta * new_tree.predict(self.X_train)
            self.tree_ensemble.append(new_tree)
          
    def predict_probabilities(self, X_eval):
        raw_output = np.zeros(X_eval.shape[0])
        for tree in self.tree_ensemble:
            raw_output += self.eta * tree.predict(X_eval) 
        return self._apply_sigmoid(np.full((X_eval.shape[0], 1), 1).flatten().astype('float64') + raw_output)
    
    def predict(self, X_eval):
        raw_output = np.zeros(X_eval.shape[0])
        for tree in self.tree_ensemble:
            raw_output += self.eta * tree.predict(X_eval) 
        final_probs = self._apply_sigmoid(np.full((X_eval.shape[0], 1), 1).flatten().astype('float64') + raw_output)
        return np.where(final_probs > np.mean(final_probs), 1, 0)

class CustomXGBRegressor:
    def __init__(self):
        self.tree_ensemble = []
    
    @staticmethod
    def _compute_gradients(raw_preds, targets):
        return 2 * (raw_preds - targets)
    
    @staticmethod
    def _compute_hessians(raw_preds, targets):
        return np.full((raw_preds.shape[0], 1), 2).flatten().astype('float64')
    
    def fit(self, X_train, y_train, col_sample_rate=0.8, min_hessian_sum=1, max_depth=5, min_samples=5, eta=0.4, n_trees=5, reg_lambda=1.5, split_gamma=1, bin_eps=0.1):
        self.X_train, self.y_train = X_train, y_train
        self.max_depth = max_depth
        self.col_sample_rate = col_sample_rate
        self.bin_eps = bin_eps
        self.min_hessian_sum = min_hessian_sum 
        self.min_samples = min_samples
        self.eta = eta
        self.n_trees = n_trees 
        self.reg_lambda = reg_lambda
        self.split_gamma = split_gamma
    
        self.current_preds = np.full((X_train.shape[0], 1), np.mean(y_train)).flatten().astype('float64')
    
        for _ in range(self.n_trees):
            g_vector = self._compute_gradients(self.current_preds, self.y_train)
            h_vector = self._compute_hessians(self.current_preds, self.y_train)
            new_tree = GradientTree().fit(self.X_train, g_vector, h_vector, max_depth=self.max_depth, min_samples=self.min_samples, reg_lambda=self.reg_lambda, split_gamma=self.split_gamma, bin_eps=self.bin_eps, min_hessian_sum=self.min_hessian_sum, col_sample_rate=self.col_sample_rate)
            self.current_preds += self.eta * new_tree.predict(self.X_train)
            self.tree_ensemble.append(new_tree)
          
    def predict(self, X_eval):
        raw_output = np.zeros(X_eval.shape[0])
        for tree in self.tree_ensemble:
            raw_output += self.eta * tree.predict(X_eval) 
        return np.full((X_eval.shape[0], 1), np.mean(self.y_train)).flatten().astype('float64') + raw_output