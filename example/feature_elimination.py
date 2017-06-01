"""Script to test descriptors for the ML model."""
from __future__ import print_function
from __future__ import absolute_import

from ase.ga.data import DataConnection
from atoml.data_setup import get_unique, get_train
from atoml.fingerprint_setup import return_fpv
from atoml.feature_preprocess import normalize
from atoml.feature_elimination import FeatureScreening
from atoml.particle_fingerprint import ParticleFingerprintGenerator
from atoml.standard_fingerprint import StandardFingerprintGenerator
from atoml.predict import GaussianProcess

# Connect database generated by a GA search.
db = DataConnection('gadb.db')

# Get all relaxed candidates from the db file.
print('Getting candidates from the database')
all_cand = db.get_all_relaxed_candidates(use_extinct=False)

# Setup the test and training datasets.
testset = get_unique(atoms=all_cand, size=50, key='raw_score')
trainset = get_train(atoms=all_cand, size=50, taken=testset['taken'],
                     key='raw_score')

# Get the list of fingerprint vectors and normalize them.
print('Getting the fingerprint vectors')
par = ParticleFingerprintGenerator(get_nl=False, max_bonds=13)
std = StandardFingerprintGenerator()
test_features = return_fpv(testset['atoms'], [par.nearestneighbour_fpv,
                                              par.bond_count_fpv,
                                              par.distribution_fpv,
                                              par.rdf_fpv,
                                              std.mass_fpv,
                                              std.eigenspectrum_fpv,
                                              std.distance_fpv])
train_features = return_fpv(trainset['atoms'], [par.nearestneighbour_fpv,
                                                par.bond_count_fpv,
                                                par.distribution_fpv,
                                                par.rdf_fpv,
                                                std.mass_fpv,
                                                std.eigenspectrum_fpv,
                                                std.distance_fpv])


def do_pred(train, test):
    """Function to make prediction."""
    norm = normalize(train_matrix=train, test_matrix=test)

    # Do the predictions.
    pred = gp.get_predictions(train_fp=norm['train'],
                              test_fp=norm['test'],
                              train_target=trainset['target'],
                              test_target=testset['target'],
                              get_validation_error=True,
                              get_training_error=True,
                              optimize_hyperparameters=False)

    # Print the error associated with the predictions.
    print('Training error:', pred['training_rmse']['average'])
    print('Model error:', pred['validation_rmse']['average'])


# Get base predictions.
print('\nBase Predictions\n')
# Set up the prediction routine.
kdict = {'k1': {'type': 'gaussian', 'width': 0.5}}
gp = GaussianProcess(kernel_dict=kdict, regularization=0.001)
do_pred(train=train_features, test=test_features)

# Get descriptor correlation
corr = ['pearson', 'spearman', 'kendall']
for c in corr:
    print('\nPredictions based on %s correlation\n' % c)
    # Set up the prediction routine.
    kdict = {'k1': {'type': 'gaussian', 'width': 0.5}}
    gp = GaussianProcess(kernel_dict=kdict, regularization=0.001)

    screen = FeatureScreening(correlation=c, iterative=False)
    features = screen.eliminate_features(target=trainset['target'],
                                         train_features=train_features,
                                         test_features=test_features, size=50,
                                         step=None, order=None)

    reduced_train = features[0]
    reduced_test = features[1]
    do_pred(train=reduced_train, test=reduced_test)

    screen = FeatureScreening(correlation='pearson', iterative=True,
                              regression='ridge')
    features = screen.eliminate_features(target=trainset['target'],
                                         train_features=train_features,
                                         test_features=test_features, size=50,
                                         step=None, order=None)

    reduced_train = features[0]
    reduced_test = features[1]
    do_pred(train=reduced_train, test=reduced_test)
