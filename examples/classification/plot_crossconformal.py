"""
======================================================
Introducing cross-conformal methods for classification
======================================================

In this tutorial, we estimate the impact of the
training/calibration split on the prediction sets and
on the resulting coverage estimated by
:class:`mapie.classification.MapieClassifier`.
We then adopt a cross-validation approach in which the
conformity scores of all calibration sets are used to
estimate the quantile. We demonstrate that this second
"cross-conformal" approach gives more robust prediction
sets with accurate calibration plots.

The two-dimensional dataset used here is the one presented
by Sadinle et al. (2019)

We start the tutorial by splitting our training dataset
in $K$ folds and sequentially use each fold as a
calibration set, the $K-1$ folds remaining folds are
used for training the base model using
the ``cv="prefit"`` option of
:class:`mapie.classification.MapieClassifier`.
"""


import numpy as np
import matplotlib.pyplot as plt
from sklearn.naive_bayes import GaussianNB
from sklearn.model_selection import KFold
from mapie.classification import MapieClassifier
from mapie.metrics import classification_coverage_score


##############################################################################
# 1. Estimating the impact of train/calibration split on the prediction sets
# --------------------------------------------------------------------------
#
# We start by generating the two-dimensional dataset and extracting training
# and test sets. Two test sets are created, one with the same distribution
# as the training set and a second one with a regular mesh for visualization.
# The dataset is two-dimensional with three classes, data points of each class
# are obtained from a normal distribution.


centers = [(0, 3.5), (-2, 0), (2, 0)]
covs = [[[1, 0], [0, 1]], [[2, 0], [0, 2]], [[5, 0], [0, 1]]]
x_min, x_max, y_min, y_max, step = -5, 7, -5, 7, 0.1
n_samples = 500
n_classes = 3
n_cv = 5
np.random.seed(42)

X_train = np.vstack([
    np.random.multivariate_normal(center, cov, n_samples)
    for center, cov in zip(centers, covs)
])
y_train = np.hstack([np.full(n_samples, i) for i in range(n_classes)])

X_test_distrib = np.vstack([
    np.random.multivariate_normal(center, cov, 10*n_samples)
    for center, cov in zip(centers, covs)
])
y_test_distrib = np.hstack(
    [np.full(10*n_samples, i) for i in range(n_classes)]
)

xx, yy = np.meshgrid(
    np.arange(x_min, x_max, step), np.arange(x_min, x_max, step)
)
X_test = np.stack([xx.ravel(), yy.ravel()], axis=1)


##############################################################################
# Let's visualize the two-dimensional dataset.


colors = {0: "#1f77b4", 1: "#ff7f0e", 2: "#2ca02c", 3: "#d62728"}
y_train_col = list(map(colors.get, y_train))
fig = plt.figure(figsize=(7, 6))
plt.scatter(
    X_train[:, 0],
    X_train[:, 1],
    color=y_train_col,
    marker="o",
    s=10,
    edgecolor="k",
)
plt.xlabel("X")
plt.ylabel("Y")
plt.show()


##############################################################################
# We split our training dataset into 5 folds and use each fold as a
# calibration set. Each calibration set is therefore used to estimate the
# conformity scores and the given quantiles for the two methods implemented in
# :class:`mapie.classification.MapieClassifier`.


kf = KFold(n_splits=5, shuffle=True)
clfs, mapies, y_preds, y_ps_mapies = {}, {}, {}, {}
methods = ["score", "cumulated_score"]
alpha = np.arange(0.01, 1, 0.01)
for method in methods:
    clfs2, mapies2, y_preds2, y_ps_mapies2 = {}, {}, {}, {}
    for i, (train_index, calib_index) in enumerate(kf.split(X_train)):
        clf = GaussianNB().fit(X_train[train_index], y_train[train_index])
        clfs2[i] = clf
        mapie = MapieClassifier(estimator=clf, cv="prefit", method=method)
        mapie.fit(X_train[calib_index], y_train[calib_index])
        mapies2[i] = mapie
        y_pred_mapie, y_ps_mapie = mapie.predict(
            X_test_distrib, alpha=alpha, include_last_label="randomized"
        )
        y_preds2[i], y_ps_mapies2[i] = y_pred_mapie, y_ps_mapie
    clfs[method], mapies[method], y_preds[method], y_ps_mapies[method] = (
        clfs2, mapies2, y_preds2, y_ps_mapies2
    )


##############################################################################
# Let's now plot the distribution of conformity scores for each calibration
# set and the estimated quantile for `alpha` = 0.1.


fig, axs = plt.subplots(1, len(mapies["score"]), figsize=(20, 4))
for i, (key, mapie) in enumerate(mapies["score"].items()):
    axs[i].set_xlabel("Conformity scores")
    axs[i].hist(mapie.conformity_scores_)
    axs[i].axvline(mapie.quantiles_[9], ls="--", color="k")
    axs[i].set_title(f"split={key}\nquantile={mapie.quantiles_[9]:.3f}")
plt.suptitle(
    "Distribution of scores on each calibration fold for the "
    f"{methods[0]} method",
    y=1.04
)
plt.show()


##############################################################################
# We notice that the estimated quantile slightly varies among the calibration
# sets for the two methods explored here, suggesting that the
# train/calibration splitting can slightly impact our results.
# 
# Let's now visualize this impact on the number of labels included in each
# prediction set induced by the different calibration sets.


def plot_results(mapies, X_test, X_test2, y_test2, alpha, method):
    tab10 = plt.cm.get_cmap('Purples', 4)
    fig, axs = plt.subplots(1, len(mapies), figsize=(20, 4))
    for i, (key, mapie) in enumerate(mapies.items()):
        y_pi_sums = mapie.predict(
            X_test,
            alpha=alpha,
            include_last_label=True
        )[1][:, :, 0].sum(axis=1)
        axs[i].scatter(
            X_test[:, 0],
            X_test[:, 1],
            c=y_pi_sums,
            marker='.',
            s=10,
            alpha=1,
            cmap=tab10,
            vmin=0,
            vmax=3
        )
        coverage = classification_coverage_score(
            y_test2, mapie.predict(X_test2, alpha=alpha)[1][:, :, 0]
        )
        plt.suptitle(
            "Number of labels in prediction sets "
            f"for the {method} method", y=1.04
        )
        axs[i].set_title(f"coverage = {coverage:.3f}")


##############################################################################
# The prediction sets and the resulting coverages slightly vary among
# calibration sets. Let's now visualize the coverage score and the
# prediction set size as function of the `alpha` parameter.


plot_results(
    mapies["score"],
    X_test,
    X_test_distrib,
    y_test_distrib,
    alpha[9],
    "score"
)

plot_results(
    mapies["cumulated_score"],
    X_test,
    X_test_distrib,
    y_test_distrib,
    alpha[9],
    "cumulated_score"
)


##############################################################################
# Let's now compare the coverages and prediction set sizes obtained with the
# different folds as calibration sets.


def plot_coverage_width(alpha, coverages, widths):
    _, axes = plt.subplots(nrows=1, ncols=2, figsize=(12, 5))
    axes[0].set_xlabel("1 - alpha")
    axes[0].set_ylabel("Effective coverage")
    for i, cov in enumerate(coverages):
        axes[0].plot(1-alpha, cov, label=f"Split {i+1}")
    axes[0].plot([0, 1], [0, 1], ls="--", color="k")
    axes[0].legend()
    axes[1].set_xlabel("1 - alpha")
    axes[1].set_ylabel("Average of prediction set sizes")
    for i, width in enumerate(widths):
        axes[1].plot(1-alpha, width, label=f"Split {i+1}")
    axes[1].legend()


coverages = np.array(
    [
        [
            [
                classification_coverage_score(
                    y_test_distrib, y_ps[:, :, ia]
                ) for ia, _ in enumerate(alpha)]
            for _, y_ps in y_ps2.items()
        ] for _, y_ps2 in y_ps_mapies.items()
    ]
)

widths = np.array(
    [
        [
            [y_ps[:, :, ia].sum(axis=1).mean() for ia, _ in enumerate(alpha)]
            for _, y_ps in y_ps2.items()
        ] for _, y_ps2 in y_ps_mapies.items()
    ]
)

plot_coverage_width(alpha, coverages[0], widths[0])

plot_coverage_width(alpha, coverages[1], widths[1])


##############################################################################
# One can notice that the train/calibration indeed impacts the coverage and
# prediction set.
#
# In conclusion, the split-conformal method has two main limitations:
# - It prevents us to use the whole training set for training our base model
# - The prediction sets are impacted by the way we extract the calibration set

##############################################################################
# 2. Aggregating the conformity scores through cross-validation
# -------------------------------------------------------------
#
# It is possible to "aggregate" the predictions through cross-validation
# mainly via two methods:
#
# 1. Aggregating the conformity scores for all training points and then simply
#    averaging the score for a new test point
#
# 2. Comparing individually the conformity scores of the training points with
#    the conformity scores from the associated model for a new test point
#    (as presented in Romano et al. 2020 for the "cumulated_score" method)
#
# Let's explore the two possibilites with the "score" method using
# :class:`mapie.classification.MapieClassifier`.
#
# All we need to do is to provide with the `cv` argument a cross-validation
# object or an integer giving the number of folds.
# When estimating the prediction sets, we define how the scores are aggregated
# with the ``agg_scores``` attribute.


kf = KFold(n_splits=5, shuffle=True)
mapie_clf = MapieClassifier(estimator=clf, cv=kf, method="score")
mapie_clf.fit(X_train, y_train)

_, y_ps_score_mean = mapie_clf.predict(
    X_test_distrib,
    alpha=alpha,
    agg_scores="mean"
)
_, y_ps_score_crossval = mapie_clf.predict(
    X_test_distrib,
    alpha=alpha,
    agg_scores="crossval"
)


##############################################################################
# Next, we estimate the coverages and widths of prediction sets for both
# aggregation methods.


coverages_score_mean = np.array(
    [
        classification_coverage_score(
            y_test_distrib,
            y_ps_score_mean[:, :, ia]
        ) for ia, _ in enumerate(alpha)
    ]
)

widths_score_mean = np.array(
    [
        y_ps_score_mean[:, :, ia].sum(axis=1).mean()
        for ia, _ in enumerate(alpha)
    ]
)

coverages_score_crossval = np.array(
    [
        classification_coverage_score(
            y_test_distrib,
            y_ps_score_crossval[:, :, ia]
        ) for ia, _ in enumerate(alpha)
    ]
)

widths_score_crossval = np.array(
    [
        y_ps_score_crossval[:, :, ia].sum(axis=1).mean()
        for ia, _ in enumerate(alpha)
    ]
)


##############################################################################
# Next, we visualize their coverages and prediction set sizes as function of
# the `alpha` parameter.


_, axes = plt.subplots(nrows=1, ncols=2, figsize=(12, 5))
axes[0].set_xlabel("1 - alpha")
axes[0].set_ylabel("Effective coverage")
for i, cov in enumerate([coverages_score_mean, coverages_score_crossval]):
    axes[0].plot(1 - alpha, cov)
axes[0].plot([0, 1], [0, 1], ls="--", color="k")
axes[1].set_xlabel("1 - alpha")
axes[1].set_ylabel("Average of prediction set sizes")
for i, widths in enumerate([widths_score_mean, widths_score_crossval]):
    axes[1].plot(1-alpha, widths)
axes[1].legend(["mean", "crossval"], loc=[1, 0])
plt.show()


##############################################################################
# Both methods give here the same coverages and prediction set sizes for this
# example. In practice, we obtain very similar results for datasets containing
# a high number of points. This is not the case for small datasets.
#
# The calibration plots obtained with the cross-conformal methods seem to be
# more robust than with the split-conformal used above. Let's check this first
# impression by estimating the deviation from the "perfect" coverage as
# function of the `alpha` parameter.


plt.figure(figsize=(7, 5))
label = f"Cross-conf: {np.abs(coverages_score_mean - (1 - alpha)).mean(): .3f}"
plt.plot(
    1 - alpha,
    coverages_score_mean - (1 - alpha),
    color="k",
    label=label
)
for i, cov in enumerate(coverages[0]):
    label = f"Split {i+1}: {np.abs(cov - (1 - alpha)).mean(): .3f}"
    plt.plot(1-alpha, cov - (1-alpha), label=label)
plt.axhline(0, color="k", ls=":")
plt.xlabel("1 - alpha")
plt.xlabel("Deviation from perfect calibration")
plt.legend(loc=[1, 0])
plt.show()
