#!/usr/bin/env python3
"""
02_baseline.py — Baseline Model Training and Evaluation

Trains three baselines:
  (a) Logistic Regression on gene expression
  (b) MLP on gene expression
  (c) MLP on gene module features

Evaluates: AUROC (macro), weighted F1, accuracy, ECE (calibration).
Computes bootstrap 95% CIs for all metrics.

Run from project root:
    python notebooks/02_baseline.py
"""

import os
import sys
import json
import warnings
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, f1_score, roc_auc_score, log_loss,
)
from sklearn.preprocessing import label_binarize

warnings.filterwarnings("ignore", category=UserWarning)

# ─── Configuration ───────────────────────────────────────────────────────────
SEED = 42
np.random.seed(SEED)
torch.manual_seed(SEED)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, "artifacts")

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"Device: {DEVICE}")

BATCH_SIZE = 128
N_EPOCHS = 50
LR = 1e-3
PATIENCE = 10  # early stopping patience
N_BOOTSTRAP = 1000

# ─── Load Data ───────────────────────────────────────────────────────────────
print("=" * 70)
print("Loading preprocessed data and splits")
print("=" * 70)

X_expr = np.load(os.path.join(ARTIFACTS_DIR, "modality1_gene_expr.npy"))
X_morph = np.load(os.path.join(ARTIFACTS_DIR, "modality2_gene_modules.npy"))
labels = np.load(os.path.join(ARTIFACTS_DIR, "labels.npy"))

with open(os.path.join(ARTIFACTS_DIR, "splits.json")) as f:
    splits = json.load(f)

train_idx = np.array(splits["train_idx"])
val_idx = np.array(splits["val_idx"])
test_idx = np.array(splits["test_idx"])
n_classes = splits["n_classes"]
class_names = splits["class_names"]

print(f"  Gene expression: {X_expr.shape}")
print(f"  Gene modules: {X_morph.shape}")
print(f"  Classes: {n_classes} — {class_names}")
print(f"  Train: {len(train_idx)}, Val: {len(val_idx)}, Test: {len(test_idx)}")

# Split data
X_expr_train, X_expr_val, X_expr_test = X_expr[train_idx], X_expr[val_idx], X_expr[test_idx]
X_morph_train, X_morph_val, X_morph_test = X_morph[train_idx], X_morph[val_idx], X_morph[test_idx]
y_train, y_val, y_test = labels[train_idx], labels[val_idx], labels[test_idx]


# ─── Metrics Utilities ───────────────────────────────────────────────────────
def compute_ece(y_true, y_prob, n_bins=15):
    """Expected Calibration Error."""
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (y_prob >= bin_boundaries[i]) & (y_prob < bin_boundaries[i + 1])
        if mask.sum() == 0:
            continue
        bin_conf = y_prob[mask].mean()
        bin_acc = y_true[mask].mean()
        ece += mask.sum() * np.abs(bin_acc - bin_conf)
    return ece / len(y_true)


def compute_multiclass_ece(y_true, y_prob, n_bins=15):
    """ECE averaged across classes (one-vs-rest)."""
    n_classes = y_prob.shape[1]
    y_onehot = label_binarize(y_true, classes=list(range(n_classes)))
    ece_per_class = []
    for c in range(n_classes):
        ece_c = compute_ece(y_onehot[:, c], y_prob[:, c], n_bins)
        ece_per_class.append(ece_c)
    return float(np.mean(ece_per_class))


def evaluate_predictions(y_true, y_pred, y_prob):
    """Compute all metrics for a set of predictions."""
    acc = accuracy_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)
    try:
        auroc = roc_auc_score(
            y_true, y_prob, multi_class="ovr", average="macro"
        )
    except ValueError:
        auroc = float("nan")
    ece = compute_multiclass_ece(y_true, y_prob)
    return {"accuracy": acc, "f1_weighted": f1, "auroc_macro": auroc, "ece": ece}


def bootstrap_metrics(y_true, y_pred, y_prob, n_bootstrap=N_BOOTSTRAP, seed=SEED):
    """Compute bootstrap 95% CIs for all metrics."""
    rng = np.random.default_rng(seed)
    n = len(y_true)
    results = {"accuracy": [], "f1_weighted": [], "auroc_macro": [], "ece": []}

    for _ in range(n_bootstrap):
        idx = rng.choice(n, size=n, replace=True)
        # Ensure at least 2 classes in bootstrap sample
        if len(np.unique(y_true[idx])) < 2:
            continue
        m = evaluate_predictions(y_true[idx], y_pred[idx], y_prob[idx])
        for k, v in m.items():
            if not np.isnan(v):
                results[k].append(v)

    ci = {}
    for k, vals in results.items():
        if len(vals) > 0:
            ci[f"{k}_ci_lo"] = float(np.percentile(vals, 2.5))
            ci[f"{k}_ci_hi"] = float(np.percentile(vals, 97.5))
        else:
            ci[f"{k}_ci_lo"] = float("nan")
            ci[f"{k}_ci_hi"] = float("nan")
    return ci


# ─── MLP Definition ─────────────────────────────────────────────────────────
class BaselineMLP(nn.Module):
    def __init__(self, in_dim, n_classes, hidden_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, n_classes),
        )

    def forward(self, x):
        return self.net(x)


def train_mlp(model, train_loader, val_loader, n_epochs=N_EPOCHS, lr=LR, patience=PATIENCE):
    """Train MLP with early stopping on validation loss."""
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=5
    )
    criterion = nn.CrossEntropyLoss()

    best_val_loss = float("inf")
    best_state = None
    epochs_no_improve = 0

    for epoch in range(n_epochs):
        # Train
        model.train()
        train_loss = 0.0
        n_batches = 0
        for xb, yb in train_loader:
            xb, yb = xb.to(DEVICE), yb.to(DEVICE)
            optimizer.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            n_batches += 1

        # Validate
        model.eval()
        val_loss = 0.0
        val_batches = 0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(DEVICE), yb.to(DEVICE)
                loss = criterion(model(xb), yb)
                val_loss += loss.item()
                val_batches += 1

        avg_train_loss = train_loss / max(n_batches, 1)
        avg_val_loss = val_loss / max(val_batches, 1)
        scheduler.step(avg_val_loss)

        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1

        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(f"    Epoch {epoch+1:3d}/{n_epochs} — "
                  f"train_loss={avg_train_loss:.4f}, val_loss={avg_val_loss:.4f}")

        if epochs_no_improve >= patience:
            print(f"    Early stopping at epoch {epoch+1} (patience={patience})")
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    return model


def predict_mlp(model, data_loader):
    """Get predictions and probabilities from MLP."""
    model.eval()
    all_preds = []
    all_probs = []
    with torch.no_grad():
        for xb, _ in data_loader:
            xb = xb.to(DEVICE)
            logits = model(xb)
            probs = torch.softmax(logits, dim=1)
            all_preds.extend(logits.argmax(1).cpu().numpy())
            all_probs.append(probs.cpu().numpy())
    return np.array(all_preds), np.vstack(all_probs)


# ─── Create DataLoaders ─────────────────────────────────────────────────────
def make_loaders(X_train, X_val, X_test, y_train, y_val, y_test, batch_size=BATCH_SIZE):
    train_ds = TensorDataset(
        torch.tensor(X_train, dtype=torch.float32),
        torch.tensor(y_train, dtype=torch.long),
    )
    val_ds = TensorDataset(
        torch.tensor(X_val, dtype=torch.float32),
        torch.tensor(y_val, dtype=torch.long),
    )
    test_ds = TensorDataset(
        torch.tensor(X_test, dtype=torch.float32),
        torch.tensor(y_test, dtype=torch.long),
    )
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size)
    test_loader = DataLoader(test_ds, batch_size=batch_size)
    return train_loader, val_loader, test_loader


# ─── Baseline (a): Logistic Regression on Gene Expression ───────────────────
print("\n" + "=" * 70)
print("BASELINE (a): Logistic Regression on gene expression")
print("=" * 70)

lr_model = LogisticRegression(
    max_iter=1000,
    multi_class="multinomial",
    solver="lbfgs",
    random_state=SEED,
    C=1.0,
)
lr_model.fit(X_expr_train, y_train)

lr_pred = lr_model.predict(X_expr_test)
lr_prob = lr_model.predict_proba(X_expr_test)

lr_metrics = evaluate_predictions(y_test, lr_pred, lr_prob)
lr_ci = bootstrap_metrics(y_test, lr_pred, lr_prob)
lr_metrics.update(lr_ci)
lr_metrics["model"] = "LogReg_GeneExpr"

print(f"  Accuracy:    {lr_metrics['accuracy']:.4f} "
      f"[{lr_metrics['accuracy_ci_lo']:.4f}, {lr_metrics['accuracy_ci_hi']:.4f}]")
print(f"  F1 weighted: {lr_metrics['f1_weighted']:.4f} "
      f"[{lr_metrics['f1_weighted_ci_lo']:.4f}, {lr_metrics['f1_weighted_ci_hi']:.4f}]")
print(f"  AUROC macro: {lr_metrics['auroc_macro']:.4f} "
      f"[{lr_metrics['auroc_macro_ci_lo']:.4f}, {lr_metrics['auroc_macro_ci_hi']:.4f}]")
print(f"  ECE:         {lr_metrics['ece']:.4f} "
      f"[{lr_metrics['ece_ci_lo']:.4f}, {lr_metrics['ece_ci_hi']:.4f}]")


# ─── Baseline (b): MLP on Gene Expression ───────────────────────────────────
print("\n" + "=" * 70)
print("BASELINE (b): MLP on gene expression")
print("=" * 70)

expr_train_loader, expr_val_loader, expr_test_loader = make_loaders(
    X_expr_train, X_expr_val, X_expr_test, y_train, y_val, y_test
)

mlp_expr = BaselineMLP(X_expr.shape[1], n_classes, hidden_dim=256).to(DEVICE)
print(f"  Parameters: {sum(p.numel() for p in mlp_expr.parameters()):,}")
mlp_expr = train_mlp(mlp_expr, expr_train_loader, expr_val_loader)

mlp_expr_pred, mlp_expr_prob = predict_mlp(mlp_expr, expr_test_loader)
mlp_expr_metrics = evaluate_predictions(y_test, mlp_expr_pred, mlp_expr_prob)
mlp_expr_ci = bootstrap_metrics(y_test, mlp_expr_pred, mlp_expr_prob)
mlp_expr_metrics.update(mlp_expr_ci)
mlp_expr_metrics["model"] = "MLP_GeneExpr"

print(f"  Accuracy:    {mlp_expr_metrics['accuracy']:.4f} "
      f"[{mlp_expr_metrics['accuracy_ci_lo']:.4f}, {mlp_expr_metrics['accuracy_ci_hi']:.4f}]")
print(f"  F1 weighted: {mlp_expr_metrics['f1_weighted']:.4f} "
      f"[{mlp_expr_metrics['f1_weighted_ci_lo']:.4f}, {mlp_expr_metrics['f1_weighted_ci_hi']:.4f}]")
print(f"  AUROC macro: {mlp_expr_metrics['auroc_macro']:.4f} "
      f"[{mlp_expr_metrics['auroc_macro_ci_lo']:.4f}, {mlp_expr_metrics['auroc_macro_ci_hi']:.4f}]")
print(f"  ECE:         {mlp_expr_metrics['ece']:.4f} "
      f"[{mlp_expr_metrics['ece_ci_lo']:.4f}, {mlp_expr_metrics['ece_ci_hi']:.4f}]")

# Save best MLP on gene expression
torch.save(mlp_expr.state_dict(), os.path.join(ARTIFACTS_DIR, "baseline_mlp_expr.pt"))


# ─── Baseline (c): MLP on Gene Module Features ──────────────────────────────
print("\n" + "=" * 70)
print("BASELINE (c): MLP on gene module features")
print("=" * 70)

morph_train_loader, morph_val_loader, morph_test_loader = make_loaders(
    X_morph_train, X_morph_val, X_morph_test, y_train, y_val, y_test
)

mlp_morph = BaselineMLP(X_morph.shape[1], n_classes, hidden_dim=128).to(DEVICE)
print(f"  Parameters: {sum(p.numel() for p in mlp_morph.parameters()):,}")
mlp_morph = train_mlp(mlp_morph, morph_train_loader, morph_val_loader)

mlp_morph_pred, mlp_morph_prob = predict_mlp(mlp_morph, morph_test_loader)
mlp_morph_metrics = evaluate_predictions(y_test, mlp_morph_pred, mlp_morph_prob)
mlp_morph_ci = bootstrap_metrics(y_test, mlp_morph_pred, mlp_morph_prob)
mlp_morph_metrics.update(mlp_morph_ci)
mlp_morph_metrics["model"] = "MLP_GeneModules"

print(f"  Accuracy:    {mlp_morph_metrics['accuracy']:.4f} "
      f"[{mlp_morph_metrics['accuracy_ci_lo']:.4f}, {mlp_morph_metrics['accuracy_ci_hi']:.4f}]")
print(f"  F1 weighted: {mlp_morph_metrics['f1_weighted']:.4f} "
      f"[{mlp_morph_metrics['f1_weighted_ci_lo']:.4f}, {mlp_morph_metrics['f1_weighted_ci_hi']:.4f}]")
print(f"  AUROC macro: {mlp_morph_metrics['auroc_macro']:.4f} "
      f"[{mlp_morph_metrics['auroc_macro_ci_lo']:.4f}, {mlp_morph_metrics['auroc_macro_ci_hi']:.4f}]")
print(f"  ECE:         {mlp_morph_metrics['ece']:.4f} "
      f"[{mlp_morph_metrics['ece_ci_lo']:.4f}, {mlp_morph_metrics['ece_ci_hi']:.4f}]")

# Save MLP on gene modules
torch.save(mlp_morph.state_dict(), os.path.join(ARTIFACTS_DIR, "baseline_mlp_morph.pt"))


# ─── Save All Baseline Metrics ──────────────────────────────────────────────
print("\n" + "=" * 70)
print("Saving baseline metrics")
print("=" * 70)

all_metrics = pd.DataFrame([lr_metrics, mlp_expr_metrics, mlp_morph_metrics])
metrics_path = os.path.join(ARTIFACTS_DIR, "baseline_metrics.csv")
all_metrics.to_csv(metrics_path, index=False)
print(f"  Saved: {metrics_path}")

# Print summary table
print("\n  Summary:")
print("  " + "-" * 68)
print(f"  {'Model':<20} {'Accuracy':>10} {'F1 (wt)':>10} {'AUROC':>10} {'ECE':>10}")
print("  " + "-" * 68)
for _, row in all_metrics.iterrows():
    print(f"  {row['model']:<20} {row['accuracy']:>10.4f} {row['f1_weighted']:>10.4f} "
          f"{row['auroc_macro']:>10.4f} {row['ece']:>10.4f}")
print("  " + "-" * 68)

# Save model configs for reproducibility
config = {
    "seed": SEED,
    "batch_size": BATCH_SIZE,
    "n_epochs": N_EPOCHS,
    "lr": LR,
    "patience": PATIENCE,
    "n_bootstrap": N_BOOTSTRAP,
    "device": DEVICE,
    "n_classes": n_classes,
    "gene_expr_dim": int(X_expr.shape[1]),
    "gene_module_dim": int(X_morph.shape[1]),
}
with open(os.path.join(ARTIFACTS_DIR, "baseline_config.json"), "w") as f:
    json.dump(config, f, indent=2)
print(f"  Saved: artifacts/baseline_config.json")

print("\nBASELINE TRAINING COMPLETE")
