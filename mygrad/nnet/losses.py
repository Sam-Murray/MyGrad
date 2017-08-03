from ..operations.operation_base import Operation
from ..tensor_base import Tensor
import numpy as np

__all__ = ["multiclass_hinge"]


class MulticlassHinge(Operation):
    def __call__(self, a, y, hinge=1.):
        """ Parameters
            ----------
            a : mygrad.Tensor, shape=(N, C)
                The C class scores for each of the N pieces of data.

            y : numpy.ndarray, shape=(N,)
                The correct class-index, in [0, C), for each datum.

            Returns
            -------
            The average multiclass hinge loss"""
        self.a = a
        scores = a.data
        correct_labels = (range(len(y)), y)
        correct_class_scores = scores[correct_labels]  # Nx1

        M = scores - correct_class_scores[:, np.newaxis] + hinge  # NxC margins
        not_thresh = np.where(M <= 0)
        Lij = M
        Lij[not_thresh] = 0
        Lij[correct_labels] = 0

        TMP = np.ones(M.shape, dtype=float)
        TMP[not_thresh] = 0
        TMP[correct_labels] = 0  # NxC; 1 where margin > 0
        TMP[correct_labels] = -1 * TMP.sum(axis=-1)
        self.back = TMP
        self.back /= scores.shape[0]
        return np.sum(Lij) / scores.shape[0]

    def backward_a(self, grad):
        self.a.backward(grad * self.back)


def multiclass_hinge(x, y_true, hinge=1.):
    """ Parameters
        ----------
        x : mygrad.Tensor, shape=(N, K)
            The K class scores for each of the N pieces of data.

        y : Sequence[int]
            The correct class-indices, in [0, K), for each datum.

        Returns
        -------
        The average multiclass hinge loss"""
    return Tensor._op(MulticlassHinge, x, op_args=(y_true, hinge))


class SoftmaxCrossEntropy(Operation):
    """ Given the classification scores of C classes for N pieces of data,
        computes the NxC softmax classification probabilities. The
        cross entropy is then computed by using the true classifications."""
    def __call__(self, a, y):
        """ Parameters
            ----------
            a : mygrad.Tensor, shape=(N, C)
                The C class scores for each of the N pieces of data.

            y : Sequence[int]
                The correct class-indices, in [0, C), for each datum.
            Returns
            -------
            The average softmax loss"""
        self.a = a
        scores = np.copy(a.data)
        max_scores = np.max(scores, axis=1, keepdims=True)
        np.exp(scores - max_scores, out=scores)
        scores /= np.sum(scores, axis=1, keepdims=True)
        label_locs = (range(len(scores)), y)

        loss = -np.sum(np.log(scores[label_locs])) / scores.shape[0]

        self.back = scores
        self.back[label_locs] -= 1.
        self.back /= scores.shape[0]
        return loss

    def backward_a(self, grad):
        self.a.backward(grad * self.back)


def softmax_crossentropy(x, y_true):
    """ Parameters
        ----------
        x : pygrad.Tensor, shape=(N, C)
            The C class scores for each of the N pieces of data.
        y_true : Sequence[int]
            The correct class-indices, in [0, C), for each datum.
        Returns
        -------
        The average softmax loss"""
    return Tensor._op(SoftmaxCrossEntropy, x, y_true)

class MeanSquaredError(Operation):
    """Given a predicted output value and true value,
        Will return the mean squared error of the two"""
    def __call__(self, x, y_true):
        """ Params
            ------
            x: pygrad.tensor shape: (N,), the predicted values of a sequence
            y: np.array() shape:(N,), the truth values of the sequence
            Returns
            -------
            Mean squared error"""
  
        self.a = x
        self.error=np.copy(x.data)-y_true.data
        
        self.length=len(self.error)
        print(self.length)
        print(self.error)
        loss=np.sum((self.error**2)/self.length)
        return loss
    def backward_a(self,grad):
            print(grad)
            self.a.backward((grad*self.error*2)/self.length)
            
            
def mean_squared_error(x,y_true):
    """ Params
        ------
        x: pygrad.tensor shape: (N,), the predicted values of a sequence
        y: np.array() shape:(N,), the truth values of the sequence
        Returns
        -------
        Mean squared error"""
    return Tensor._op(MeanSquaredError,x,y_true)
    
            
